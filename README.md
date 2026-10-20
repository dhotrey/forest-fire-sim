# COSC3500 - Forest fire sim

![Forest-fire simulation animation](data/gifs/fire-0.7-2026-08-27-11-20-24-089.gif)

## Milestones

### Milestone 1

[![Watch the milestone 1 presentation](https://img.youtube.com/vi/l-9ioKjfn4M/hqdefault.jpg)](https://youtu.be/l-9ioKjfn4M)

[▶ Watch the milestone 1 presentation on YouTube](https://youtu.be/l-9ioKjfn4M).
Click the preview to open the video for playback.

Milestone 2 (parallel implementation) is in progress.

## Running

Build and run the model by supplying the grid size, number of time steps, and
the `p` and `f` probabilities:

```sh
make
./bin/fire-v1.1-dev 100 500 0.01 0.001
```

The default `make` target is `dev`: an `-O0` debug build that prints a final-grid
hash. The optimisation targets are available individually, or together with
the debug build through `all`:

```sh
make o1
make o2
make o3
make all
```

Executables are written to `bin/fire-v{version}-{dev|o1|o2|o3}`. The version and
version name are set in the Makefile; override them with, for example,
`make o3 VERSION=1.1 VERSION_NAME=simd-random`. Only `o3` includes
`-march=native -mavx2`, targeting the build machine's CPU.

All builds omit visualisation support by default. Enable it with `VISUALISE=1`;
this adds `-viz` to the executable name:

```sh
make o3 VISUALISE=1
```

On startup, the program prints the model configuration and the build metadata:
compile date/time, compiler and version, C++ standard, compiler target,
executable target, build profile, and optimisation settings.

Normal runs do not write simulation frames to disk. Add `--visualise` when a
binary save file is wanted:

```sh
./bin/fire-v1.1-o3-viz 100 500 0.01 0.001 --visualise
```

The program prints the generated path, which has the form
`out/fire-{version}-{date}-{time}.bin`.
The `--visualise` flag writes every completed timestep but does not create a
CSV. Add `--v` (or `-v`) after it for verbose visualisation, which also writes
the matching CSV:

```sh
./bin/fire-v1.1-o3-viz 100 500 0.01 0.001 --visualise --v
```

The animation script accepts the generated binary path. Its optional second
argument displays every Nth saved frame; `10` therefore displays frames 0, 10,
20, and so on:

```sh
uv run --project tools/animation python tools/animation/visualise.py \
  out/fire-1.1-YYYY-MM-DD-HH-MM-SS-mmm.bin 10
```

Alternatively, `make anim` opens the newest save file in `out/`. Select a specific
file with `make anim SAVE_FILE=out/fire-1.1-YYYY-MM-DD-HH-MM-SS-mmm.bin`.

## Running benchmarks

Build the required optimisation binaries, then submit the benchmark from the
repository root on the Slurm cluster:

```sh
make o1 o2 o3 VERSION=1.1
bash bench.sh all v1.1
```

Use `bash bench.sh o3 v1.1` for just `-O3`, or `bash bench.sh o2,o3 v1.1` for
`-O2` and `-O3` in the same job, running sequentially. The benchmark script does
not compile binaries. Supply the
version explicitly: Make uses `1.1`, while the benchmark script expects `v1.1`.

`bench.sh` submits `run.slurm.sh`, which currently requests one node, one task,
and one CPU on the `a100` partition. It runs 100², 500², and 1000² grids for 500
timesteps with `p=0.02` and `f=0.01`. Each build gets a tiny initial warm-up,
then two untimed warm-ups and five timed repetitions per grid size. Timed build
order reverses on alternate repetitions. These settings live in `run.slurm.sh`;
thread-count scaling is not implemented yet.

GNU `/usr/bin/time` measures the whole process, including startup and allocation.
Each run starts with empty grids and the fixed RNG seed `80085`. The CSV records
wall time (`total_s`), user/system CPU time, CPU utilisation, peak memory, context
switches, and page faults. Correctness hashes are printed by `dev` builds;
the benchmark does not compare hashes automatically.

For `all v1.1`, results are written to
`data/v1.1/benchmarking/benchmarks-o1-o2-o3.csv`, with machine details, binary
checksums, and run output in `data/v1.1/slurm-logs/slurm-o1-o2-o3.out`.
Repeating the same version/configuration overwrites the CSV. The 100² runs can
be too short for useful comparisons at the timer's 0.01-second output precision.

## Plotting benchmarks

Combine any number of benchmark CSV files and write one two-panel runtime chart
per grid size:

```sh
uv run --project tools/animation python tools/plot_benchmarks.py \
  data/v0.0/benchmarking/benchmarks-o1-o2.csv \
  data/v0.1/benchmarking/benchmarks-o1-o2.csv \
  --output-dir plots/benchmarks
```

The script averages repeated wall times for each version/optimisation/grid
combination and writes files such as `plots/benchmarks/benchmark-100x100.png`.
The first panel shows mean runtime with the minimum-to-maximum range shaded;
the second shows percentage runtime changes between adjacent versions
(negative means faster).

## Binary save-file format

`fire-{version}-{date}-{time}.bin` is self-describing and does not require the
Python script to be told the grid size or number of timesteps. All integer
fields are fixed-width and little-endian. The complete file is laid out like
this:

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

The header fields are, in order: the magic bytes `FFCA`; format version
`uint16` (currently `1`); square grid size `uint32`; saved-frame count
`uint64`; frame interval `uint32` (currently `1`); and cell size `uint8`
(currently `1`). Each frame contains `grid_size * grid_size` cells in display
order: all x values for y = 0, then all x values for y = 1, and so on. Cell
states are `0 = Empty`, `1 = Tree`, and `2 = Burning`. Frame 0 is the grid after
the first completed update, so a run with `timesteps = N` contains exactly N
frames.

The stored grid size includes the one-cell border on every side: an input size
of 100 produces a 102 × 102 stored grid. The startup banner also reports this
padded size.

## Cluster environment

- `module avail` : to see what modules are available on cluster for linking

## Slurm cheatsheet

- `sinfo` : to see different nodes available on the cluster
- `sinfo -p cosc3500 -N -l` : to see status of machines in the cosc3500 cluster. We get priority access on this partition. 
- `squeue` : to see who is running jobs on the cluster at the moment
- `sbatch <slurm_file.sh>` : to run the job on the cluster using the configuration in the <slurm_file.sh>
