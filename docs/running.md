# Build and run the simulation

Use an AVX2-capable CPU, GCC with C++17 and OpenMP support, and Make. Run commands
from the repository root.

## Build

```sh
make o3
```

The Makefile defaults to version `1.4`, named `avx+omp-final`. Executables use
the name `bin/fire-v{version}-{dev|o1|o2|o3}`. Override the version metadata with
`make o3 VERSION=1.4 VERSION_NAME=avx+omp-final`.

The default `make` target is `dev`, an `-O0` debug build that prints a final-grid
hash. Use `make o1`, `make o2`, or `make o3` for individual optimisation builds,
or `make all` for all four builds. Every SIMD build includes
`-march=native -mavx2 -fopenmp` and targets the build machine's CPU.

Use `make serial` to build `bin/fire-v1.0-serial-baseline-o3` from `serial.cpp`
with `-O3 -march=native`.

## Run

```sh
OMP_NUM_THREADS=8 ./bin/fire-v1.4-o3 256 500 0.02 0.01
```

Arguments are the interior grid width, number of timesteps, tree-growth
probability `p`, and spontaneous-fire probability `f`. The SIMD implementation
requires a positive interior width divisible by 32. It has no scalar path for
leftover cells and does not validate this restriction at startup.

The program adds an empty border on every side, so an input width of 256 creates
a 258 × 258 stored grid. The startup banner reports the padded size, model
configuration, and build metadata. `OMP_NUM_THREADS` sets the OpenMP team size;
use `1` to run the current SIMD implementation with one thread.

Debug hashes can check repeatability for a fixed build and thread count.
Different implementations and thread counts use different random streams, so
matching hashes across them are not an expected correctness check.

## Record and view frames

Build with frame-recording support:

```sh
make o3 VISUALISE=1
```

This adds `-viz` to the executable name. Record every completed timestep with
`--visualise`:

```sh
OMP_NUM_THREADS=8 ./bin/fire-v1.4-o3-viz 256 500 0.02 0.01 --visualise
```

The program prints the generated path, which has the form
`out/fire-1.4-YYYY-MM-DD-HH-MM-SS-mmm.bin`. Add `--v` or `-v` after
`--visualise` to also write a matching CSV. Normal runs do not record frames.

Use uv to open the newest recording:

```sh
make anim
```

Select a specific recording with
`make anim SAVE_FILE=out/fire-1.4-YYYY-MM-DD-HH-MM-SS-mmm.bin`.
To display every tenth saved frame, call the animation script directly:

```sh
uv run --project tools/animation python tools/animation/visualise.py \
	out/fire-1.4-YYYY-MM-DD-HH-MM-SS-mmm.bin 10
```
