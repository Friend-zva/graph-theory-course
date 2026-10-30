#!/usr/bin/env python3

import argparse
import csv
import re
import sys
from pathlib import Path

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
    parser.add_argument("--dataset", help="Dataset name, for example coPapersDBLP")
    parser.add_argument("-t", "--threads", type=int, help="Thread count")
    parser.add_argument(
        "-n",
        "--nodes",
        nargs="+",
        type=int,
        help="MPI process counts (-n) to include",
    )
    parser.add_argument("--output", type=Path, help="Output directory")
    args = parser.parse_args(argv)

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
        if args.threads is not None and int(match["t"]) != args.threads:
            continue
        if args.nodes and int(match["n"]) not in args.nodes:
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
        groups.setdefault((match["algo"], match["dataset"]), []).append(
            (int(match["n"]), int(match["t"]), value / 1000, algo_time / 1000)
        )

    for (algorithm, dataset), points in groups.items():
        points.sort(key=lambda point: (point[0], point[1]))
        labels = [f"({node}, {threads})" for node, threads, _, _ in points]
        values = [value for _, _, value, _ in points]
        algo_values = [value for _, _, _, value in points]
        overhead_values = [value - algo for value, algo in zip(values, algo_values)]
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
        axis.set_xticks(positions, labels)
        axis.set_xlabel("(MPI processes, threads)")
        axis.set_ylabel("Time, s")
        axis.set_title(f"{algorithm} / {dataset}")
        axis.set_axisbelow(False)
        axis.set_ylim(0, max(values) * 1.11 if values else 1)
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
