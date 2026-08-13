#!/bin/bash
#SBATCH --job-name=decay
#SBATCH --partition=cosc3500
#SBATCH --account=cosc3500
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --ntasks-per-node=1
#SBATCH --cpus-per-task=1
##SBATCH --mem-per-cpu=1G # memory (MB)
#SBATCH --time=0-00:01 # time (D-HH:MM)

SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
PROJECT_DIR=$(dirname -- "$SCRIPT_DIR")
cd "$PROJECT_DIR" || exit 1

make clean
make

time ./out/fire 100 500 0.01 0.001
