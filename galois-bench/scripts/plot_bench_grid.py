#!/usr/bin/env python3

import argparse
import csv
import math
import re
import sys
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

SCRIPT_DIR = Path(__file__).resolve().parent
ROOT = SCRIPT_DIR.parent
FILENAME_PATTERN = re.compile(
    r"^(?P<algo>[^_]+)_(?P<dataset>.+)_n(?P<n>\d+)_t(?P<t>\d+)\.csv$"
)
RUN_DIRECTORY_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2}_\d+$")
ALGORITHMS = ("bfs", "sssp", "pr", "tc")


def latest_parsed_directory() -> Path:
    runs = [
        path
        for path in (ROOT / "benchmarks").iterdir()
        if path.is_dir() and RUN_DIRECTORY_PATTERN.match(path.name)
    ]
    if not runs:
        raise FileNotFoundError("no benchmark runs found")
    return max(runs, key=lambda path: path.name) / "parsed"


def read_points(
    input_dir: Path,
    algo: Optional[str],
    dataset: Optional[str],
    threads: Optional[int],
    nodes: Optional[Sequence[int]],
) -> Dict[str, List[Tuple[int, float, float]]]:
    groups: Dict[str, List[Tuple[int, float, float]]] = {}
    for path in sorted(input_dir.glob("*.csv")):
        match = FILENAME_PATTERN.match(path.name)
        if not match:
            continue
        if algo and match["algo"] != algo:
            continue
        if dataset and match["dataset"] != Path(dataset).stem:
            continue
        if threads is not None and int(match["t"]) != threads:
            continue
        if nodes and int(match["n"]) not in nodes:
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
        groups.setdefault(match["dataset"], []).append(
            (int(match["n"]), int(match["t"]), total / 1000, algo_time / 1000)
        )
    return groups


def plot_grid(
    groups: Dict[str, Iterable[Tuple[int, float, float]]],
    output: Path,
    *,
    algorithm: str,
    threads: Optional[int] = None,
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
    for axis, (dataset, raw_points) in zip(axes_flat, sorted(groups.items())):
        points = sorted(raw_points, key=lambda point: (point[0], point[1]))
        labels = [f"({node}, {threads})" for node, threads, _, _ in points]
        total = [value for _, _, value, _ in points]
        algo_time = [value for _, _, _, value in points]
        overhead = [value - algo for value, algo in zip(total, algo_time)]
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
        axis.set_title(dataset)
        axis.set_xticks(positions, labels)
        axis.set_xlabel("(MPI processes, threads)")
        if axis in axes_flat[::2]:
            axis.set_ylabel("Time, s")
        axis.set_axisbelow(False)
        axis.set_ylim(0, max(total) * 1.11 if total else 1)
        axis.margins(x=0.12)
        axis.grid(axis="y", alpha=0.25)

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
    parser.add_argument("-t", "--threads", type=int, help="Thread count")
    parser.add_argument(
        "-n",
        "--nodes",
        nargs="+",
        type=int,
        help="MPI process counts",
    )
    parser.add_argument("--output", type=Path, help="Output PNG path")
    args = parser.parse_args(argv)

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
        available_algorithms
        if args.algo is None
        else list(dict.fromkeys(args.algo))
    )
    for algorithm in algorithms:
        groups = read_points(
            input_dir, algorithm, args.dataset, args.threads, args.nodes
        )
        if not groups:
            parser.error(
                f"no parsed files match the requested filters for {algorithm}"
            )
        if args.output and len(algorithms) > 1:
            output = args.output.with_name(
                f"{args.output.stem}_{algorithm}{args.output.suffix}"
            )
        else:
            output = args.output or input_dir.parent / "plots" / (
                f"{algorithm}_grid_t{args.threads or 'all'}.png"
            )
        output.parent.mkdir(parents=True, exist_ok=True)
        plot_grid(groups, output, algorithm=algorithm, threads=args.threads)


if __name__ == "__main__":
    main()
