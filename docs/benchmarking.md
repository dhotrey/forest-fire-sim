# Run and plot benchmarks

Run commands from the repository root. The benchmark launcher requires Slurm
and GNU `/usr/bin/time`; the plotting tool uses the Python environment in
`tools/animation/` through uv.

## Submit a benchmark

Build each selected optimisation configuration before submitting:

```sh
make o3
bash bench.sh o3 v1.4
```

Supply the version explicitly. Make uses `1.4`, while `bench.sh` expects `v1.4`.
The launcher does not compile binaries. Use `o2,o3` to benchmark those builds
sequentially in one job, or `all` for `o1,o2,o3`.

`bench.sh` submits `run.slurm.sh`, which requests one node, one task, and eight
CPUs on the `a100` partition, with a 15-minute time limit. The script sets
`OMP_NUM_THREADS` from the allocated CPU count, disables dynamic teams, and
binds threads to cores with `OMP_PLACES=cores` and `OMP_PROC_BIND=close`.

The current workload is an 8320 × 8320 interior grid for 500 timesteps with
`p=0.02` and `f=0.01`. Each build runs five times without warm-ups. All
measurements are saved, and build order reverses on alternate repetitions.
These settings live in `run.slurm.sh`. The script benchmarks one thread count
per submission; it does not sweep thread counts automatically.

The time limit covers all repetitions of every selected build. Select fewer
builds if their combined runtime would exceed the limit.

## Interpret the output

GNU `/usr/bin/time` measures the whole process, including startup and allocation.
The CSV records elapsed wall time in `total_s`, user and system CPU time, CPU
utilisation, peak memory, context switches, and page faults. Use `total_s` for
speedup comparisons. User CPU time adds the CPU time spent by all threads.

Each run starts with empty grids. The current parallel implementation seeds
each thread with `80085 + thread_id`. Frame recording is disabled for the
benchmark binaries. The script stops if a binary exits with an error, but does
not compare simulation output or hashes automatically.

For `o3 v1.4`, results go to `data/v1.4/benchmarking/benchmarks-o3.csv`.
Machine details, binary checksums, and run output go to
`data/v1.4/slurm-logs/slurm-o3.out`. Repeating the same version and configuration
overwrites these outputs, so preserve any results you need before rerunning.

Earlier measurements include 100², 500², 1000², 5000², and 5120² grids. The 100²
runs were too short for useful comparisons at the timer's 0.01-second precision.

## Plot saved measurements

Supply any number of benchmark CSV files:

```sh
uv run --project tools/animation python tools/plot_benchmarks.py \
	data/v1.0/benchmarking/benchmarks-o3.csv \
	data/v1.1/benchmarking/benchmarks-o3.csv \
	data/v1.3/8-threads/benchmarking/benchmarks-o3.csv \
	--output-dir plots/benchmarks
```

The script writes one two-panel chart per grid size, such as
`plots/benchmarks/benchmark-8320x8320.png`. The first panel shows minimum elapsed
wall time, with the minimum-to-maximum range shaded. The second shows percentage
runtime changes between adjacent versions; negative values mean faster runs.

The README's `benchmark-final-comparison-8-threads.png` uses the three datasets
above. Their minimum times are 117.77 s for serial `v1.0`, 32.42 s for SIMD
`v1.1`, and 4.02 s for eight-thread `v1.3`. All three datasets contain five runs
on an AMD EPYC 7542 with the same grid, timestep count, and probabilities. The
overall speedup is `117.77 / 4.02 = 29.3×`. These are recorded milestone results;
they are not new measurements of the current `v1.4` build.
