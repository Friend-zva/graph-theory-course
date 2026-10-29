#!/usr/bin/env python3

import argparse
import csv
import re
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
ROOT = SCRIPT_DIR.parent


def main() -> None:
    parser = argparse.ArgumentParser(description="Plot parsed Galois benchmarks")
    parser.add_argument(
        "input",
        nargs="?",
        type=Path,
        default=ROOT / "benchmarks" / "recent" / "parsed",
    )
    parser.add_argument("--metric", default="median_ms", help="CSV column to plot")
    parser.add_argument("--algo", help="Algorithm, for example bfs or sssp")
    parser.add_argument("--dataset", help="Dataset name, for example coPapersDBLP")
    parser.add_argument("--threads", type=int, help="Thread count (-t)")
    parser.add_argument(
        "--nodes",
        nargs="+",
        type=int,
        help="MPI process counts (-n) to include",
    )
    parser.add_argument("--output", type=Path, help="Output directory")
    args = parser.parse_args()

    try:
        import matplotlib.pyplot as plt
    except ImportError as error:
        parser.error("plot_bench.py requires matplotlib")

    input_dir = args.input.resolve()
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
        if args.algo and match["algo"] != args.algo:
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
        groups.setdefault((match["algo"], match["dataset"], match["t"]), []).append(
            (int(match["n"]), float(row[args.metric]))
        )

    for (algorithm, dataset, threads), points in groups.items():
        points.sort()
        nodes = [node for node, _ in points]
        values = [value for _, value in points]
        plt.figure()
        plt.plot(nodes, values, marker="o")
        plt.xticks(nodes)
        plt.xlabel("MPI processes (-n)")
        plt.ylabel(args.metric)
        plt.title(f"{algorithm} / {dataset} / t={threads}")
        plt.tight_layout()
        plt.savefig(output_dir / f"{algorithm}_{dataset}_t{threads}_{args.metric}.png")
        plt.close()


if __name__ == "__main__":
    main()
