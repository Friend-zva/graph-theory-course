# graph-theory-course

This repository contains a report on experiments for the Graph Theory course.

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

Build and install `spla`:

```sh
git clone https://github.com/SparseLinearAlgebra/spla.git --depth 1
cd spla
python3 build.py
```

> NOTE: You may need to make the following modifications to `build.py`:

```py
  build_config_args = ["cmake", ".", "-B", args.build_dir, "-G", "Ninja", f"-DCMAKE_BUILD_TYPE={args.build_type}",
                         f"-DSPLA_BUILD_TESTS={args.tests}", f"-DSPLA_BUILD_EXAMPLES={args.examples}",
                         f"-DSPLA_BUILD_OPENCL={args.opencl}",
                         "-DCMAKE_EXPORT_COMPILE_COMMANDS=ON"]
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
cmake -DCMAKE_EXPORT_COMPILE_COMMANDS=ON -DGALOIS_ENABLE_DIST=1 ..
cd lonestar/analytics/distributed
make -j
```

> NOTE: You may need to make the following modifications to `libgalois/include/galois/graphs/Details.h`:

```cpp
public:
  EdgeSortIterator() : at(0) {}
  EdgeSortIterator(EdgeIndex x, EdgeDst* dsts, EdgeData* data)
      : at(x), edgeDst(dsts), edgeData(data) {}

  Reference operator[](ptrdiff_t n) const {
    return Reference(at + n, edgeDst, edgeData);
  }

private:
  friend class boost::iterator_core_access;
```
