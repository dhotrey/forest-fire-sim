# COSC3500 - Forest fire sim

## Running

Build and run the model by supplying the grid size, number of time steps, and
the `p` and `f` probabilities:

```sh
make
./bin/fire 100 500 0.01 0.001
```

On startup, the program prints the model configuration and the build metadata:
compile date/time, compiler and version, C++ standard, compiler target,
executable target, build profile, and optimisation settings.

Normal runs do not write simulation frames to disk. Add `--visualise` when a
save file and a frame-by-frame console dump are wanted:

```sh
./bin/fire 100 500 0.01 0.001 --visualise
python3 visualise.py fire.bin 10
```

The flag takes no argument. It writes every completed timestep to `fire.bin`.
The second argument to `visualise.py` is optional and displays every Nth saved
frame; `10` therefore displays frames 0, 10, 20, and so on.

## Binary save-file format

`fire.bin` is self-describing and does not require the Python script to be told
the grid size or number of timesteps. All integer fields are fixed-width and
little-endian. The header is 23 bytes:

```text
offset  size  field
0       4     magic bytes: "FFCA"
4       2     format version: uint16, currently 1
6       4     square grid size: uint32
10      8     number of saved frames: uint64
18      4     frame interval: uint32, currently 1
22      1     cell size in bytes: uint8, currently 1
```

The header is followed by `number of saved frames` flattened grids. Each grid
contains `grid_size * grid_size` one-byte cell states in display order: all x
values for y = 0, then all x values for y = 1, and so on. The current states
are `0 = Empty`, `1 = Tree`, and `2 = Burning`. Frame 0 is the grid after the
first completed update, so a run with `timesteps = N` contains exactly N
frames.

Use `make optimized` (or `make optimised`) for the `-O3` build, and `make debug`
for the debug build. The selected profile and optimisation flags are included
in the startup banner.

# Random

- `module avail` : to see what modules are available on cluster for linking

# Slurm cheatsheet

- `sinfo` : to see different nodes available on the cluster
- `sinfo -p cosc3500 -N -l` : to see status of machines in the cosc3500 cluster. We get priority access on this partition. 
- `squeue` : to see who is running jobs on the cluster at the moment
- `sbatch <slurm_file.sh>` : to run the job on the cluster using the configuration in the <slurm_file.sh>
