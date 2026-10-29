#!/usr/bin/env python3

import argparse
import csv
import math
import statistics
import sys
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

SCRIPT_DIR = Path(__file__).resolve().parent
ROOT = SCRIPT_DIR.parent
BENCHMARKS = ROOT / "benchmarks"


def read_stats(
    path: Path,
) -> Tuple[Dict[Tuple[str, str], float], Dict[Tuple[str, str], str]]:
    stats: Dict[Tuple[str, str], float] = {}
    params: Dict[Tuple[str, str], str] = {}
    with path.open(newline="", encoding="utf-8", errors="replace") as source:
        for row in csv.reader(source, skipinitialspace=True):
            if len(row) < 6 or row[0] not in {"STAT", "PARAM"}:
                continue
            region, category = row[2].strip(), row[3].strip()
            value = ",".join(row[5:]).strip()
            if row[0] == "PARAM":
                params[(region, category)] = value
            else:
                try:
                    number = float(value)
                except ValueError:
                    continue
                if math.isfinite(number):
                    stats[(region, category)] = number
    return stats, params


def algorithm_name(path: Path, stats: Dict[Tuple[str, str], float]) -> str:
    regions = {region.upper() for region, category in stats if category == "TimerTotal"}
    if "BFS" in regions:
        return "bfs"
    if "SSSP" in regions:
        return "sssp"
    if "PAGERANK" in regions:
        return "pr"
    if "TC" in regions or "TRIANGLECOUNTING" in regions:
        return "tc"
    return path.stem.split("_", 1)[0]


def dataset_name(params: Dict[Tuple[str, str], str], path: Path) -> str:
    value = params.get(("DistBench", "Input"))
    return Path(value).stem if value else path.stem.split("_", 1)[-1]


def parse_file(path: Path, skip_first: bool) -> Tuple[str, str, Dict[str, object]]:
    stats, params = read_stats(path)
    algorithm = algorithm_name(path, stats)
    timers = {
        int(category[6:]): value
        for (region, category), value in stats.items()
        if category.startswith("Timer_") and category[6:].isdigit()
    }
    if not timers:
        raise ValueError(f"{path}: no Timer_N values found")

    runs = int(float(params.get(("DistBench", "Runs"), len(timers))))
    if skip_first and runs <= 1:
        raise ValueError(f"{path}: --skip-first-iteration requires runs > 1")
    if skip_first:
        # Galois omits zero-valued STAT rows, so an absent Timer_N is a
        # completed iteration with a measured time of zero.
        values = [timers.get(index, 0.0) for index in range(1, runs)]
    else:
        values = [timers.get(index, 0.0) for index in range(runs)]

    row: Dict[str, object] = {
        "dataset": dataset_name(params, path),
        "algorithm": algorithm,
        "nodes": params.get(("DistBench", "Hosts"), ""),
        "threads": params.get(("DistBench", "Threads"), ""),
        "runs": runs,
        "warm_up_ms": timers.get(0, ""),
        "avg_ms": statistics.mean(values),
        "median_ms": statistics.median(values),
        "rf_cnt": stats.get(("Gluon", "ReplicationFactor"), ""),
    }
    for (region, category), value in stats.items():
        if category.startswith("Timer_") or category.startswith("Sync_"):
            row[category] = value
    return str(row["dataset"]), algorithm, row


def write_csv(path: Path, rows: Iterable[Dict[str, object]]) -> None:
    rows = list(rows)
    fields = ["dataset"]
    for row in rows:
        for field in row:
            if field not in fields:
                fields.append(field)
    with path.open("w", newline="", encoding="utf-8") as output:
        writer = csv.DictWriter(output, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Parse Galois benchmark CSV stat files"
    )
    parser.add_argument("input", nargs="?", type=Path, default=BENCHMARKS / "recent")
    parser.add_argument(
        "--skip-first-iteration",
        action="store_true",
        help="Exclude Timer_0 from avg/median and require runs > 1",
    )
    args = parser.parse_args(argv)
    input_path = args.input.resolve()
    input_dir = input_path.parent if input_path.is_file() else input_path
    run_dir = input_dir.parent if input_dir.name == "raw" else input_dir
    files = [input_path] if input_path.is_file() else sorted(input_dir.rglob("*.csv"))
    files = [
        path
        for path in files
        if path.name != "summary.csv"
        and path.read_text(encoding="utf-8", errors="replace").startswith("STAT_TYPE")
    ]
    if not files:
        parser.error(f"no CSV stat files found in {input_dir}")

    parsed = [(path, *parse_file(path, args.skip_first_iteration)) for path in files]
    output_dir = run_dir / "parsed"
    output_dir.mkdir(parents=True, exist_ok=True)
    for path, _, _, row in parsed:
        row.pop("algorithm", None)
        output_path = output_dir / path.name
        write_csv(output_path, [row])
        print(f"Parsed 1 file: {output_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
