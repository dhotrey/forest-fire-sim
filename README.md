# COSC3500 - Forest fire sim

## Running

Build and run the model by supplying the grid size, number of time steps, and
the `p` and `f` probabilities:

```sh
make
./out/fire 100 500 0.01 0.001
```

The default `make` target builds the standard binary and the three
optimisation builds. The optimisation targets are available individually:

```sh
make o1timised
make o2timised
make o3timised
```

The optimisation builds omit visualisation support by default. Enable it when
building one of them with `VISUALISE=1`, for example:

```sh
make o3timised VISUALISE=1
```

On startup, the program prints the model configuration and the build metadata:
compile date/time, compiler and version, C++ standard, compiler target,
executable target, build profile, and optimisation settings.

Normal runs do not write simulation frames to disk. Add `--visualise` when a
binary save file is wanted:

```sh
./out/fire 100 500 0.01 0.001 --visualise
```

The program prints the generated path, which has the form
`out/fire-{version}-{date}-{time}.bin`. The current version is `0.0`.
The `--visualise` flag writes every completed timestep but does not create a
CSV. Add `--v` (or `-v`) after it for verbose visualisation, which also writes
the matching CSV:

```sh
./out/fire 100 500 0.01 0.001 --visualise --v
```

The animation script accepts the generated binary path. Its optional second
argument displays every Nth saved frame; `10` therefore displays frames 0, 10,
20, and so on:

```sh
python3 animation/visualise.py out/fire-0.0-YYYY-MM-DD-HH-MM-SS-mmm.bin 10
```

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

Use `make debug` for a debug build. The selected profile and optimisation flags
are included in the startup banner.

# Random

- `module avail` : to see what modules are available on cluster for linking

# Slurm cheatsheet

- `sinfo` : to see different nodes available on the cluster
- `sinfo -p cosc3500 -N -l` : to see status of machines in the cosc3500 cluster. We get priority access on this partition. 
- `squeue` : to see who is running jobs on the cluster at the moment
- `sbatch <slurm_file.sh>` : to run the job on the cluster using the configuration in the <slurm_file.sh>
