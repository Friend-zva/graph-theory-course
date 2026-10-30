#!/usr/bin/env python3

import argparse
import csv
import math
import statistics
import sys
from pathlib import Path
import re
from typing import Dict, Iterable, List, Optional, Tuple

SCRIPT_DIR = Path(__file__).resolve().parent
ROOT = SCRIPT_DIR.parent
BENCHMARKS = ROOT / "benchmarks"
RUN_DIRECTORY_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2}_\d+$")


def latest_benchmark_directory() -> Path:
    directories = [
        path
        for path in BENCHMARKS.iterdir()
        if path.is_dir() and RUN_DIRECTORY_PATTERN.match(path.name)
    ]
    if not directories:
        raise FileNotFoundError(f"no benchmark runs found in {BENCHMARKS}")
    return max(directories, key=lambda path: path.name)


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
    algorithm_region = next(
        (
            region
            for (region, category) in stats
            if category == "TimerTotal"
        ),
        algorithm.upper(),
    )
    timers = {
        int(category[6:]): value
        for (region, category), value in stats.items()
        if category.startswith("Timer_") and category[6:].isdigit()
    }
    runs = int(float(params.get(("DistBench", "Runs"), len(timers))))
    if not timers and runs <= 0:
        raise ValueError(f"{path}: no Timer_N values found")

    if skip_first and runs <= 1:
        raise ValueError(f"{path}: --skip-first-iteration requires runs > 1")
    if skip_first:
        # Galois omits zero-valued STAT rows, so an absent Timer_N is a
        # completed iteration with a measured time of zero.
        values = [timers.get(index, 0.0) for index in range(1, runs)]
    else:
        values = [timers.get(index, 0.0) for index in range(runs)]

    timer_values = [timers.get(index, 0.0) for index in range(runs)]
    algo_values = [
        stats.get((algorithm_region, f"Time_{index}"), 0.0)
        if (algorithm_region, f"Time_{index}") in stats
        else stats.get((f"{algorithm_region}_{index}", "Time"), 0.0)
        for index in range(runs)
    ]
    sync_values = [
        stats.get(("Gluon", f"Sync_{algorithm_region}_{index}"), 0.0)
        for index in range(runs)
    ]
    values = timer_values[1:] if skip_first else timer_values
    algo_stat_values = algo_values[1:] if skip_first else algo_values
    total_time = stats.get((algorithm_region, "TimerTotal"), 0.0)
    row: Dict[str, object] = {
        "dataset": dataset_name(params, path),
        "nodes": params.get(("DistBench", "Hosts"), ""),
        "threads": params.get(("DistBench", "Threads"), ""),
        "runs": runs,
    }
    for index in range(runs):
        row[f"Sync_{algorithm_region}_{index}"] = sync_values[index]
        row[f"{algorithm_region}_{index}"] = algo_values[index]
        row[f"Timer_{index}"] = timer_values[index]
        row[f"NumIterations_{index}"] = stats.get(
            (algorithm_region, f"NumIterations_{index}"), 0.0
        )
        row[f"NumWorkItems_{index}"] = stats.get(
            (algorithm_region, f"NumWorkItems_{index}"), 0.0
        )
    row["TimerTotal"] = total_time
    row["ReplicationFactor"] = stats.get(("Gluon", "ReplicationFactor"), 0.0)
    row["warm_up"] = timer_values[0]
    row[f"avg_{algorithm}"] = statistics.mean(algo_stat_values)
    row[f"median_{algorithm}"] = statistics.median(algo_stat_values)
    row["avg_timer"] = statistics.mean(values)
    row["median_timer"] = statistics.median(values)
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
    parser.add_argument(
        "input",
        nargs="?",
        type=Path,
        help="Raw stat file or directory (default: latest benchmark run)",
    )
    parser.add_argument(
        "--skip-first-iteration",
        action="store_true",
        help="Exclude Timer_0 from avg/median and require runs > 1",
    )
    args = parser.parse_args(argv)
    if args.input is None:
        try:
            input_path = latest_benchmark_directory() / "raw"
        except FileNotFoundError as error:
            parser.error(str(error))
    else:
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
        output_path = output_dir / path.name
        write_csv(output_path, [row])
        print(f"Parsed 1 file: {output_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
