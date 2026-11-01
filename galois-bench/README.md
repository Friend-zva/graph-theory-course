# galois-bench

These scripts run distributed Galois benchmarks, parse raw statistics, and generate plots. Run the commands from the `galois-bench` directory.

## Standard workflow

```bash
cd /Users/vladimir/Projects/python/graph-theory-course/galois-bench

python3 ./scripts/benchmark.py \
  -n 1 1 1 2 3 4 \
  -t 1 3 7 3 2 1 \
  -i 22

python3 ./scripts/parse_stats.py -s benchmarks/main/raw

python3 ./scripts/plot_bench_grid.py benchmarks/main/parsed \
  -n 1 1 1 2 3 4 \
  -t 1 3 7 3 2 1
```

`-n` specifies the number of MPI processes, and `-t` specifies the number of threads per process. Values are paired by position:

```text
-n 1 1 1 2 3 4
-t 1 3 7 3 2 1
```

This produces the configurations `(n=1,t=1)`, `(1,3)`, `(1,7)`, `(2,3)`, `(3,2)`, and `(4,1)`. The number of values in `-n` and `-t` must match. `-i 22` runs each configuration 22 times; the first run is used as a warm-up.

## Results

After `benchmark.py` finishes, a run directory is created in `benchmarks/` with a `raw/` subdirectory. The `benchmarks/recent` symlink points to the latest run. In the current setup, the results used for further processing are stored in `benchmarks/main/raw`.

`parse_stats.py -s` excludes `Timer_0` from mean and median values and writes the processed CSV files to the `parsed/` directory. Without `-s`, the first run is also included in the statistics.

`plot_bench_grid.py` creates PNG files in `plots/`. For PageRank, the plot shows `compute`, `delta`, and `overhead` separately; for other algorithms, it shows `compute` and `overhead`.

## Useful options

Run only selected algorithms:

```bash
python3 ./scripts/benchmark.py --algo pr --algo tc -n 1 -t 4 -i 10
```

Select specific graphs:

```bash
python3 ./scripts/benchmark.py \
  --datasets datasets/coPapersDBLP.gr \
  -n 1 -t 4 -i 10
```

Create a regular plot instead of a grid:

```bash
python3 ./scripts/plot_bench.py benchmarks/main/parsed \
  --algo pr --dataset coPapersDBLP
```

Running the benchmarks requires built Galois binaries and `mpirun`. Plotting requires the Python package `matplotlib`.
