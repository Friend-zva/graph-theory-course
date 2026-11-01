#!/usr/bin/env python3

import argparse
import csv
import re
import sys
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from pathlib import Path
from typing import List, Optional, Tuple

SCRIPT_DIR = Path(__file__).resolve().parent
ROOT = SCRIPT_DIR.parent
ALGORITHMS = ("bfs", "sssp", "pr", "tc")
RUN_DIRECTORY_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2}_\d+$")


def latest_parsed_directory() -> Path:
    runs = [
        path
        for path in (ROOT / "benchmarks").iterdir()
        if path.is_dir() and RUN_DIRECTORY_PATTERN.match(path.name)
    ]
    if not runs:
        raise FileNotFoundError("no benchmark runs found")
    return max(runs, key=lambda path: path.name) / "parsed"


def format_replication_factor(value: Optional[str]) -> str:
    try:
        number = Decimal(value)
    except (InvalidOperation, TypeError):
        return "0.00"
    return str(number.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def timer_range(row: dict, fallback: float) -> Tuple[float, float, Optional[float]]:
    values = []
    warm_up = None
    for key, value in row.items():
        if not key.startswith("Timer_") or not key[6:].isdigit():
            continue
        try:
            number = float(value)
        except (TypeError, ValueError):
            continue
        if key == "Timer_0":
            warm_up = number / 1000
        else:
            values.append(number)
    if not values:
        values = [fallback * 1000]
    return min(values) / 1000, max(values) / 1000, warm_up


def build_pairs(
    parser: argparse.ArgumentParser,
    nodes: Optional[List[int]],
    threads: Optional[List[int]],
) -> Optional[List[Tuple[int, int]]]:
    """Pair -n and -t values the same way benchmark.py does."""
    if nodes is None or threads is None:
        return None
    if len(nodes) == len(threads):
        return list(zip(nodes, threads))
    if len(threads) == 1:
        return [(node, threads[0]) for node in nodes]
    if len(nodes) == 1:
        return [(nodes[0], thread) for thread in threads]
    parser.error("-n and -t must contain the same number of values")
    raise AssertionError("unreachable")


def main() -> None:
    argv = sys.argv[1:]
    if "--algo" in argv:
        flag_index = argv.index("--algo")
        index = flag_index + 1
        algorithms = []
        while index < len(argv) and argv[index] in ALGORITHMS:
            algorithms.append(argv[index])
            index += 1
        argv[flag_index:index] = [
            item for algorithm in algorithms for item in ("--algo", algorithm)
        ]
    parser = argparse.ArgumentParser(description="Plot parsed Galois benchmarks")
    parser.add_argument(
        "input",
        nargs="?",
        type=Path,
        default=None,
    )
    parser.add_argument("--metric", default="median_timer", help="CSV column to plot")
    parser.add_argument("--algo", action="append", choices=ALGORITHMS, default=None)
    parser.add_argument("--dataset", help="Dataset name")
    parser.add_argument(
        "-t",
        "--threads",
        nargs="+",
        type=int,
        help="Thread counts, one value per -n value",
    )
    parser.add_argument(
        "-n",
        "--nodes",
        nargs="+",
        type=int,
        help="MPI process counts (-n) to include",
    )
    parser.add_argument("--output", type=Path, help="Output directory")
    args = parser.parse_args(argv)

    pairs = build_pairs(parser, args.nodes, args.threads)
    pair_order = (
        {pair: index for index, pair in enumerate(pairs)} if pairs is not None else None
    )

    try:
        import matplotlib.pyplot as plt
    except ImportError as error:
        parser.error("plot_bench.py requires matplotlib")

    try:
        input_dir = args.input.resolve() if args.input else latest_parsed_directory()
    except FileNotFoundError as error:
        parser.error(str(error))
    files = sorted(input_dir.glob("*.csv"))
    if not files:
        parser.error(f"no parsed CSV files found in {input_dir}")

    output_dir = args.output or input_dir.parent / "plots"
    output_dir.mkdir(parents=True, exist_ok=True)
    selected = []
    filename_pattern = re.compile(
        r"^(?P<algo>[^_]+)_(?P<dataset>.+)_n(?P<n>\d+)_t(?P<t>\d+)\.csv$"
    )
    for path in files:
        match = filename_pattern.match(path.name)
        if not match:
            continue
        if args.algo is not None and match["algo"] not in args.algo:
            continue
        if args.dataset and match["dataset"] != Path(args.dataset).stem:
            continue
        if args.threads is not None and int(match["t"]) not in args.threads:
            continue
        if args.nodes and int(match["n"]) not in args.nodes:
            continue
        pair = (int(match["n"]), int(match["t"]))
        if pair_order is not None and pair not in pair_order:
            continue
        selected.append((path, match))
    if not selected:
        parser.error("no parsed files match the requested algorithm/dataset/-t/-n")

    groups = {}
    for path, match in selected:
        with path.open(newline="", encoding="utf-8") as source:
            rows = list(csv.DictReader(source))
        if not rows or args.metric not in rows[0]:
            continue
        row = rows[0]
        try:
            value = float(row[args.metric])
            algo_time = float(row.get(f"median_{match['algo']}", 0) or 0)
        except (TypeError, ValueError, KeyError):
            continue
        minimum, maximum, warm_up = timer_range(row, value)
        replication = format_replication_factor(row.get("ReplicationFactor", ""))
        groups.setdefault((match["algo"], match["dataset"]), []).append(
            (
                int(match["n"]),
                int(match["t"]),
                value / 1000,
                algo_time / 1000,
                replication,
                minimum,
                maximum,
                warm_up,
            )
        )

    for (algorithm, dataset), points in groups.items():
        if pair_order is None:
            points.sort(key=lambda point: (point[0], point[1]))
        else:
            points.sort(key=lambda point: pair_order[(point[0], point[1])])
        labels = [
            f"({node},{thread}):{node * (thread + 1)}\nrf:{replication}"
            for node, thread, _, _, replication, _, _, _ in points
        ]
        values = [value for _, _, value, _, _, _, _, _ in points]
        algo_values = [value for _, _, _, value, _, _, _, _ in points]
        overhead_values = [value - algo for value, algo in zip(values, algo_values)]
        minimums = [minimum for _, _, _, _, _, minimum, _, _ in points]
        maximums = [maximum for _, _, _, _, _, _, maximum, _ in points]
        warm_ups = [warm_up for _, _, _, _, _, _, _, warm_up in points]
        figure, axis = plt.subplots(figsize=(10, 7))
        positions = list(range(len(labels)))
        axis.bar(positions, algo_values, color="tab:blue", label="algorithm")
        if args.metric == "median_timer":
            axis.bar(
                positions,
                overhead_values,
                bottom=algo_values,
                color="tab:orange",
                label="overhead",
            )
        axis.errorbar(
            positions,
            values,
            yerr=[
                [value - minimum for value, minimum in zip(values, minimums)],
                [maximum - value for value, maximum in zip(values, maximums)],
            ],
            fmt="none",
            ecolor="black",
            elinewidth=1.5,
            capsize=4,
            capthick=1.5,
            zorder=3,
        )
        axis.scatter(
            positions,
            warm_ups,
            color="black",
            s=12,
            zorder=4,
        )
        axis.set_xticks(positions, labels)
        axis.set_xlabel(
            "(MPI processes, threads): total threads, rf: replication factor"
        )
        axis.set_ylabel("Time, s")
        axis.set_title(f"{algorithm} / {dataset}")
        axis.set_axisbelow(False)
        axis.set_ylim(0, max(values + maximums) * 1.11 if values else 1)
        axis.margins(x=0.12)
        axis.grid(axis="y", alpha=0.25)
        handles, labels = axis.get_legend_handles_labels()
        order = [labels.index("algorithm")]
        if args.metric == "median_timer":
            order.insert(0, labels.index("overhead"))
        axis.legend(
            [handles[index] for index in order],
            [labels[index] for index in order],
        )
        figure.tight_layout()
        figure.savefig(output_dir / f"{algorithm}_{dataset}.png", dpi=160)
        plt.close(figure)


if __name__ == "__main__":
    main()
