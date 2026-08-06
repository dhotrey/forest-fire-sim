# COSC3500 - Forest fire sim

# Random

- `module avail` : to see what modules are available on cluster for linking

# Slurm cheatsheet

- `sinfo` : to see different nodes available on the cluster
- `sinfo -p cosc3500 -N -l` : to see status of machines in the cosc3500 cluster. We get priority access on this partition. 
- `squeue` : to see who is running jobs on the cluster at the moment
- `sbatch <slurm_file.sh>` : to run the job on the cluster using the configuration in the <slurm_file.sh>

