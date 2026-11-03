# graph-theory-course

This repository contains a report on experiments for the Graph Theory course.

## Datasets

| Name              | Vertices |  Edges | Avg Deg | Sd Deg | Max Deg |                                                                                  Link |
| :---------------- | -------: | -----: | ------: | -----: | ------: | ------------------------------------------------------------------------------------: |
| coPapersDBLP      |   540.5K |  30.5M |    56.4 |   66.2 |  3299.0 |  [link](https://www.cise.ufl.edu/research/sparse/matrices/DIMACS10/coPapersDBLP.html) |
| belgium_osm       |     1.4M |   3.1M |     2.2 |    0.5 |    10.0 |   [link](https://www.cise.ufl.edu/research/sparse/matrices/DIMACS10/belgium_osm.html) |
| hollywood-2009    |     1.1M | 112.8M |    98.9 |  271.9 | 11467.0 |     [link](https://www.cise.ufl.edu/research/sparse/matrices/LAW/hollywood-2009.html) |
| rgg_n_2_22_s0     |     4.2M |  60.7M |    14.5 |    3.8 |    36.0 | [link](https://www.cise.ufl.edu/research/sparse/matrices/DIMACS10/rgg_n_2_22_s0.html) |
| soc-LiveJournal1* |     4.8M |  85.7M |    17.7 |   52.0 | 20333.0 |  [link](https://www.cise.ufl.edu/research/sparse/matrices/SNAP/soc-LiveJournal1.html) |
| road_central      |    14.1M |  33.9M |     2.4 |    0.9 |     8.0 |  [link](https://www.cise.ufl.edu/research/sparse/matrices/DIMACS10/road_central.html) |

`*`: symmetric and clear with `Galois` `graph-convert` (`mtx2gr`, `gr2cgr`)

## Module 1: Linear Algebra

Objective: compare the performance of different solutions based on linear algebra.
Implementation for experiments: `SuiteSparse:GraphBLAS` & `LAGraph` and `Spla`.

### How to reproduce

> NOTE: If you cloned the repository using `git clone --recurse-submodules`, you can skip the `git clone` steps and proceed directly to building the libraries.

Build and install `GraphBLAS`:

```sh
git clone https://github.com/DrTimothyAldenDavis/GraphBLAS.git --depth 1
cd GraphBLAS
mkdir build && cd build
cmake -DCMAKE_EXPORT_COMPILE_COMMANDS=ON -DOpenMP_C_INCLUDE_DIR="/opt/homebrew/opt/libomp/include" ..
make -j
```

Build and install `LAGraph`:

```sh
git clone https://github.com/GraphBLAS/LAGraph.git --depth 1
cd LAGraph
mkdir build && cd build
cmake -DCMAKE_EXPORT_COMPILE_COMMANDS=ON -DOpenMP_C_INCLUDE_DIR="/opt/homebrew/opt/libomp/include" ..
make -j
```

> NOTE: You may need to make the following modifications to `LAGraph`. See [pathes](patches/LAGraph).

Build and install `Spla`:

```sh
git clone https://github.com/SparseLinearAlgebra/spla.git --depth 1
cd Spla
python3 build.py
```

> NOTE: You may need to make the following modifications to `Spla`. See [pathes](patches/spla).

### Benchmark

`spla-bench/` contains scripts that run the `spla` & `lagraph` algorithms. Clone and see [`README.md`](https://github.com/Friend-zva/spla-bench).

### Profile

```sh
./spla/build/pr --mtxpath=./spla-bench/dataset/hollywood-09.mtx --run-cpu=false --run-ref=false // 1
sample -wait pr 30 1 -file ./spla_pr_sample.txt // 2
./FlameGraph/stackcollapse-sample.awk spla_pr_sample.txt > spla_pr.txt
./FlameGraph/flamegraph.pl spla_pr.txt > spla_pr.svg
```

## Module 2: Distributed graph processing

Objective: to evaluate scalability as a function of the number of nodes.
Implementation for experiments: `Galois`.

### How to reproduce

Build and install `Galois`:

```sh
git clone https://github.com/IntelligentSoftwareSystems/Galois.git --depth 1
cd Galois
mkdir build && cd build
cmake -DCMAKE_EXPORT_COMPILE_COMMANDS=ON -DGALOIS_COMM_STATS=ON -DGALOIS_ENABLE_DIST=1 ..
cd lonestar/analytics/distributed
make -j
```

> NOTE: You may need to make the following modifications to `Galois`. See [pathes](patches/Galois).

### Benchmark

`galois-bench/` contains scripts that run the distributed algorithms for
several `-n` / `-t` values, parse the Galois `-statFile` output and plot the
results. See [`galois-bench/README.md`](galois-bench/README.md).
