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
