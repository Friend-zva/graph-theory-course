#!/usr/bin/env python3

import argparse
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

import config

ALGORITHM_ALIASES = {
    "bfs": "bfs",
    "sssp": "sssp",
    "pr": "pr",
    "tc": "tc",
}


def main() -> None:
    argv = sys.argv[1:]
    if "--algo" in argv:
        flag_index = argv.index("--algo")
        index = flag_index + 1
        algorithms = []
        while index < len(argv) and argv[index] in ALGORITHM_ALIASES:
            algorithms.append(argv[index])
            index += 1
        argv[flag_index:index] = [
            item for algorithm in algorithms for item in ("--algo", algorithm)
        ]

    parser = argparse.ArgumentParser(description="Run Galois distributed benchmarks")
    parser.add_argument(
        "--algo",
        action="append",
        choices=ALGORITHM_ALIASES,
        default=None,
        help="Algorithms to run: bfs, sssp, pr, tc",
    )
    parser.add_argument(
        "--datasets",
        nargs="+",
        type=Path,
        default=config.DATASETS,
        help="Graphs to benchmark (default: all datasets from config.py)",
    )
    parser.add_argument(
        "-i",
        "--iterations",
        type=int,
        default=4,
        help="Number of Galois runs (-runs, default: 3)",
    )
    parser.add_argument(
        "-n",
        "--nodes",
        nargs="+",
        type=int,
        default=[1],
        help="MPI process counts (default: 1)",
    )
    parser.add_argument(
        "-t",
        "--threads",
        dest="t",
        nargs="+",
        type=int,
        default=[4],
        help="Threads per process, one value per -n value (default: 4)",
    )
    parser.add_argument(
        "--no-save",
        action="store_true",
        help="Run without creating benchmark files or updating benchmarks/recent",
    )
    args = parser.parse_args(argv)
    if args.algo is None:
        args.algo = list(config.BINARIES)
    algorithms = list(dict.fromkeys(ALGORITHM_ALIASES[name] for name in args.algo))

    graphs = args.datasets
    graphs = [graph.expanduser().resolve() for graph in graphs]
    for graph in graphs:
        if not graph.is_file():
            parser.error(f"graph does not exist: {graph}")
    if any(node <= 0 for node in args.nodes):
        parser.error("node counts must be positive")
    if any(thread <= 0 for thread in args.t):
        parser.error("thread counts must be positive")
    if len(args.nodes) != len(args.t):
        parser.error("-n and -t must contain the same number of values")

    if args.no_save:
        stat_directory = None
    else:
        run_dir = (
            config.ROOT
            / "benchmarks"
            / datetime.now().strftime("%Y-%m-%d_%H-%M-%S_%f")
        )
        run_dir.mkdir(parents=True)
        stat_directory = run_dir / "raw"
        stat_directory.mkdir()

    fixed_options = {
        "bfs": ["-symmetricGraph", "-partition=oec", "-exec=Sync"],
        "sssp": ["-symmetricGraph", "-partition=oec", "-exec=Sync"],
        "pr": ["-symmetricGraph", "-partition=oec", "-exec=Sync", "-tolerance=0.001"],
        "tc": ["-symmetricGraph", "-partition=oec"],
    }

    environment = os.environ.copy()
    environment["GALOIS_DO_NOT_BIND_THREADS"] = "1"
    for graph in graphs:
        dataset_name = graph.stem
        for node_count, thread_count in zip(args.nodes, args.t):
            for algorithm in algorithms:
                binary = config.BINARIES[algorithm]
                if not binary.is_file():
                    parser.error(f"binary does not exist: {binary}")

                stat_file = (
                    Path(os.devnull)
                    if stat_directory is None
                    else stat_directory
                    / f"{algorithm}_{dataset_name}_n{node_count}_t{thread_count}.csv"
                )
                command = [
                    "mpirun",
                    "-n",
                    str(node_count),
                    str(binary),
                    str(graph),
                    f"-t={thread_count}",
                    f"-runs={args.iterations}",
                    f"-statFile={stat_file}",
                    *fixed_options[algorithm],
                ]
                print("$", " ".join(command), flush=True)
                subprocess.run(command, env=environment, check=True)

    if not args.no_save:
        recent = config.ROOT / "benchmarks" / "recent"
        if recent.exists() or recent.is_symlink():
            recent.unlink()
        os.symlink(run_dir.name, recent, target_is_directory=True)


if __name__ == "__main__":
    main()
