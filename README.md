# COSC3500 - Forest fire simulation

Run all commands below from the repository root.

## Requirements

- A C++17 compiler (`g++` by default) and GNU Make
- [`uv`](https://docs.astral.sh/uv/) for the animation and benchmark plots
- Slurm and GNU `/usr/bin/time` for runtime benchmarking
- Valgrind on the selected compute node for cache benchmarking

## Building with Make

The default target is `dev`, an `-O0` debug build:

```sh
make
# Equivalent to: make dev
```

Build an individual optimised binary, or all four configurations, with:

```sh
make o1
make o2
make o3
make all
```

With the current Makefile defaults (`VERSION=0.5`), these targets produce:

```text
bin/fire-v0.5-dev
bin/fire-v0.5-o1
bin/fire-v0.5-o2
bin/fire-v0.5-o3
```

Override the version, version name, or compiler on the `make` command line:

```sh
make VERSION=0.6 VERSION_NAME=my-change o2
make CXX=clang++ o2
```

All builds omit frame-saving support by default. Set `VISUALISE=1` when
building to include it; this adds `-viz` to the executable name:

```sh
make dev VISUALISE=1
# Produces bin/fire-v0.5-dev-viz
```

Use `make help` to list the main targets. `make clean` removes both `bin/` and
`out/`, including generated simulation save files.

## Running the simulation

Pass the requested grid size, number of timesteps, tree-growth probability
`p`, and lightning probability `f`:

```sh
./bin/fire-v0.5-dev 100 500 0.01 0.001
```

Optimised binaries use the same arguments:

```sh
./bin/fire-v0.5-o2 100 500 0.01 0.001
```

On startup, the program prints its model configuration and build metadata,
including the compiler, target, version, build profile, and optimisation
flags.

## Saving and animating a simulation

First build a visualisation-enabled binary, then pass `--visualise`:

```sh
make dev VISUALISE=1
./bin/fire-v0.5-dev-viz 100 500 0.01 0.001 --visualise
```

The program prints the generated path. It has the form
`out/fire-{version}-{date}-{time}.bin` (for example,
`out/fire-0.5-2026-08-28-10-00-00-000.bin`). It contains every completed
timestep.

To also write a matching, human-readable CSV, add `--v` or `-v` after
`--visualise`:

```sh
./bin/fire-v0.5-dev-viz 100 500 0.01 0.001 --visualise --v
```

Animate the newest `.bin` file in `out/`:

```sh
make anim
```

Select a particular save file with `SAVE_FILE`:

```sh
make anim SAVE_FILE=out/fire-0.5-YYYY-MM-DD-HH-MM-SS-mmm.bin
```

For more control, invoke the animation script directly. The optional second
argument is a positive frame stride; `10` displays frames 0, 10, 20, and so
on:

```sh
uv run --project tools/animation python tools/animation/visualise.py \
  out/fire-0.5-YYYY-MM-DD-HH-MM-SS-mmm.bin 10
```

The animation opens an interactive Matplotlib window, so it needs a graphical
display.

## Runtime benchmarking on Slurm

The runtime benchmark uses non-visualisation `o1`, `o2`, and/or `o3` binaries.
The version passed to `bench.sh` must include the leading `v` and must match
the version in the binary filenames:

```sh
make o1 o2
bash bench.sh o1,o2 v0.5
```

To benchmark all optimised configurations:

```sh
make o1 o2 o3
bash bench.sh all v0.5
```

For a different program version, pass the numeric value to Make and the
corresponding `v`-prefixed value to the benchmark:

```sh
make VERSION=0.6 o1 o2
bash bench.sh o1,o2 v0.6
```

`bench.sh [configurations] [version]` is the submission wrapper. Its
configuration is either a comma-separated subset of `o1,o2,o3` or `all`; its
defaults are `o1,o2` and `v0.1`. It submits `run.slurm.sh` and writes the Slurm
log to:

```text
data/VERSION/slurm-logs/slurm-CONFIGURATIONS.out
```

The job writes its measurements to:

```text
data/VERSION/benchmarking/benchmarks-CONFIGURATIONS.csv
```

`run.slurm.sh` currently benchmarks grids `100`, `500`, and `1000` for 500
timesteps, with two warm-ups and five measured repetitions at `p=0.02` and
`f=0.01`. Change the constants near the top of that script to use a different
benchmark matrix. Runs are pinned to an allocated CPU when possible, and the
configuration order is reversed on alternating repetitions.

The Slurm script can also be submitted directly, but this does not use the
wrapper's organised log path:

```sh
sbatch run.slurm.sh o1,o2 v0.5
```

## Cache benchmarking on Slurm

`cache_test.slurm.sh` runs Valgrind Cachegrind. Each run is a group of five
arguments: executable, grid size, timesteps, `p`, and `f`.

Run one configuration:

```sh
sbatch cache_test.slurm.sh \
  bin/fire-v0.5-o2 1000 500 0.02 0.01
```

Compare multiple builds in one allocation by appending more five-argument
groups:

```sh
sbatch cache_test.slurm.sh \
  bin/fire-v0.5-o1 1000 500 0.02 0.01 \
  bin/fire-v0.5-o2 1000 500 0.02 0.01
```

The submission directory receives `cache-test-JOB_ID.out` plus one
`cachegrind.out.PROCESS_ID` file per run. The script checks that every binary
is executable and that Valgrind is available on the compute node.

## Plotting benchmark results

`tools/plot_benchmarks.py` accepts one or more runtime benchmark CSV files. It
requires the columns `version`, `opt_flag`, `grid_size`, and `total_s`.
Repeated runs for the same version, optimisation, and grid size are averaged.

Compare results across versions with:

```sh
uv run --project tools/animation python tools/plot_benchmarks.py \
  data/v0.0/benchmarking/benchmarks-o1-o2.csv \
  data/v0.1/benchmarking/benchmarks-o1-o2.csv \
  data/v0.2/benchmarking/benchmarks-o1-o2.csv
```

The default output directory is `plots/benchmarks`. Override it with `-o` or
`--output-dir`:

```sh
uv run --project tools/animation python tools/plot_benchmarks.py \
  data/v0.4/benchmarking/benchmarks-o1-o2.csv \
  data/v0.5/benchmarking/benchmarks-o1-o2.csv \
  --output-dir plots/v0.4-v0.5
```

The script writes one PNG per grid size, such as
`benchmark-100x100.png`. Each image shows mean absolute runtime (with the
repeated-run range shaded) and the percentage runtime change between
successive versions.

## Binary save-file format

`fire-{version}-{date}-{time}.bin` is self-describing; the animation script
does not need a grid size or timestep count. All integer fields are
fixed-width and little-endian:

```text
┌─────────────────────────────────────────────────────────────────────┐
│ Header (23 bytes)                                                   │
├────────┬───────────┬───────────┬────────────┬───────────┬───────────┤
│ "FFCA" │ version   │ grid size │ frame count│ interval  │ cell size │
│ 4 B    │ 2 B       │ 4 B       │ 8 B        │ 4 B       │ 1 B       │
└────────┴───────────┴───────────┴────────────┴───────────┴───────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│ Frame 0: grid_size × grid_size one-byte cell states                 │
├─────────────────────────────────────────────────────────────────────┤
│ Frame 1: grid_size × grid_size one-byte cell states                 │
├─────────────────────────────────────────────────────────────────────┤
│ ...                                                                 │
├─────────────────────────────────────────────────────────────────────┤
│ Frame frame_count - 1: grid_size × grid_size one-byte cell states   │
└─────────────────────────────────────────────────────────────────────┘
```

The header contains the magic bytes `FFCA`; format version `uint16`
(currently `1`); stored grid size `uint32`; saved-frame count `uint64`; frame
interval `uint32` (currently `1`); and cell size `uint8` (currently `1`). The
stored grid includes the simulation's one-cell boundary padding, so its width
is two cells larger than the grid size supplied on the command line.

Each frame contains `grid_size * grid_size` cells in display order: all x
values for y = 0, then all x values for y = 1, and so on. Cell states are
`0 = Empty`, `1 = Tree`, and `2 = Burning`. Frame 0 is the grid after the first
completed update, so a run with `timesteps = N` contains exactly N frames.

## Useful Slurm commands

- `module avail` lists modules available on the cluster.
- `sinfo` lists available partitions and nodes.
- `sinfo -p cosc3500 -N -l` shows detailed node status for the `cosc3500`
  partition.
- `squeue` lists queued and running jobs.
- `sbatch SCRIPT [ARGUMENTS...]` submits a Slurm job.
