#!/usr/bin/env python3

import argparse
import csv
import math
import re
import sys
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

SCRIPT_DIR = Path(__file__).resolve().parent
ROOT = SCRIPT_DIR.parent
FILENAME_PATTERN = re.compile(
    r"^(?P<algo>[^_]+)_(?P<dataset>.+)_n(?P<n>\d+)_t(?P<t>\d+)\.csv$"
)
RUN_DIRECTORY_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2}_\d+$")
ALGORITHMS = ("bfs", "sssp", "pr", "tc")

Pair = Tuple[int, int]
Point = Tuple[int, int, float, float, str, float, float, Optional[float]]


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
) -> Optional[List[Pair]]:
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


def read_points(
    input_dir: Path,
    algo: Optional[str],
    dataset: Optional[str],
    threads: Optional[Sequence[int]],
    nodes: Optional[Sequence[int]],
    pair_order: Optional[Dict[Pair, int]],
) -> Dict[str, List[Point]]:
    groups: Dict[str, List[Point]] = {}
    for path in sorted(input_dir.glob("*.csv")):
        match = FILENAME_PATTERN.match(path.name)
        if not match:
            continue
        if algo and match["algo"] != algo:
            continue
        if dataset and match["dataset"] != Path(dataset).stem:
            continue
        if threads is not None and int(match["t"]) not in threads:
            continue
        if nodes and int(match["n"]) not in nodes:
            continue
        pair = (int(match["n"]), int(match["t"]))
        if pair_order is not None and pair not in pair_order:
            continue
        with path.open(newline="", encoding="utf-8") as source:
            row = next(csv.DictReader(source), None)
        if not row:
            continue
        try:
            total = float(row["median_timer"])
            algo_time = float(row.get(f"median_{match['algo']}", 0) or 0)
        except (KeyError, TypeError, ValueError):
            continue
        minimum, maximum, warm_up = timer_range(row, total)
        replication = format_replication_factor(row.get("ReplicationFactor", ""))
        groups.setdefault(match["dataset"], []).append(
            (
                int(match["n"]),
                int(match["t"]),
                total / 1000,
                algo_time / 1000,
                replication,
                minimum,
                maximum,
                warm_up,
            )
        )
    return groups


def plot_grid(
    groups: Dict[str, Iterable[Point]],
    output: Path,
    *,
    algorithm: str,
    pair_order: Optional[Dict[Pair, int]] = None,
) -> None:
    import matplotlib.pyplot as plt

    if not groups:
        raise ValueError("no benchmark points to plot")
    columns = min(2, len(groups))
    rows = math.ceil(len(groups) / columns)
    figure, axes = plt.subplots(
        rows, columns, figsize=(7 * columns, 5 * rows), squeeze=False
    )
    axes_flat = list(axes.flat)
    entries = sorted(groups.items())
    for axis, (dataset, raw_points) in zip(axes_flat, entries):
        if pair_order is None:
            points = sorted(raw_points, key=lambda point: (point[0], point[1]))
        else:
            points = sorted(
                raw_points, key=lambda point: pair_order[(point[0], point[1])]
            )
        labels = [
            f"({node},{thread}):{node * (thread + 1)}\nrf:{replication}"
            for node, thread, _, _, replication, _, _, _ in points
        ]
        total = [value for _, _, value, _, _, _, _, _ in points]
        algo_time = [value for _, _, _, value, _, _, _, _ in points]
        overhead = [value - algo for value, algo in zip(total, algo_time)]
        minimums = [minimum for _, _, _, _, _, minimum, _, _ in points]
        maximums = [maximum for _, _, _, _, _, _, maximum, _ in points]
        warm_ups = [warm_up for _, _, _, _, _, _, _, warm_up in points]
        positions = list(range(len(labels)))
        axis.bar(
            positions,
            algo_time,
            color="tab:blue",
            label="algorithm",
        )
        axis.bar(
            positions,
            overhead,
            bottom=algo_time,
            color="tab:orange",
            label="overhead",
        )
        axis.errorbar(
            positions,
            total,
            yerr=[
                [value - minimum for value, minimum in zip(total, minimums)],
                [maximum - value for value, maximum in zip(total, maximums)],
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
        axis.set_title(dataset)
        axis.set_xticks(positions, labels)
        if axis in axes_flat[::2]:
            axis.set_ylabel("Time, s")
        axis.set_axisbelow(False)
        axis.set_ylim(0, max(total + maximums) * 1.11 if total else 1)
        axis.margins(x=0.12)
        axis.grid(axis="y", alpha=0.25)

    for index, axis in enumerate(axes_flat[: len(entries)]):
        if index + columns > len(entries) - 1:
            axis.set_xlabel(
                "(MPI processes, threads): total threads, rf: replication factor"
            )
    for axis in axes_flat[len(groups) :]:
        axis.set_visible(False)
    index = min(1, len(groups) - 1)
    handles, labels = axes_flat[index].get_legend_handles_labels()
    order = [labels.index("overhead"), labels.index("algorithm")]
    axes_flat[index].legend(
        [handles[index] for index in order],
        [labels[index] for index in order],
    )
    figure.tight_layout()
    figure.savefig(output, dpi=160)
    plt.close(figure)


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
    parser = argparse.ArgumentParser(description="Plot benchmark charts in a grid")
    parser.add_argument(
        "input",
        nargs="?",
        type=Path,
        default=None,
    )
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
        help="MPI process counts",
    )
    parser.add_argument("--output", type=Path, help="Output PNG path")
    args = parser.parse_args(argv)

    pairs = build_pairs(parser, args.nodes, args.threads)
    pair_order = (
        {pair: index for index, pair in enumerate(pairs)} if pairs is not None else None
    )

    try:
        import matplotlib
    except ImportError:
        parser.error("plot_bench_grid.py requires matplotlib")

    try:
        input_dir = args.input.resolve() if args.input else latest_parsed_directory()
    except FileNotFoundError as error:
        parser.error(str(error))
    available_algorithms = sorted(
        {
            match["algo"]
            for path in input_dir.glob("*.csv")
            if (match := FILENAME_PATTERN.match(path.name))
        }
    )
    algorithms = (
        available_algorithms if args.algo is None else list(dict.fromkeys(args.algo))
    )
    for algorithm in algorithms:
        groups = read_points(
            input_dir,
            algorithm,
            args.dataset,
            args.threads,
            args.nodes,
            pair_order,
        )
        if not groups:
            parser.error(f"no parsed files match the requested filters for {algorithm}")
        if args.output and len(algorithms) > 1:
            output = args.output.with_name(
                f"{args.output.stem}_{algorithm}{args.output.suffix}"
            )
        else:
            if pairs is not None:
                label = "_".join(f"n{node}t{thread}" for node, thread in pairs)
            elif args.nodes:
                label = "_".join(f"n{node}" for node in args.nodes)
            elif args.threads:
                label = "_".join(f"t{thread}" for thread in args.threads)
            else:
                combinations = sorted(
                    {
                        (node, thread)
                        for points in groups.values()
                        for node, thread, _, _, _, _, _, _ in points
                    }
                )
                label = "_".join(
                    f"n{node}t{thread}" for node, thread in combinations
                )
            output = args.output or input_dir.parent / "plots" / (
                f"{algorithm}_grid_{label}.png"
            )
        output.parent.mkdir(parents=True, exist_ok=True)
        plot_grid(groups, output, algorithm=algorithm, pair_order=pair_order)


if __name__ == "__main__":
    main()
