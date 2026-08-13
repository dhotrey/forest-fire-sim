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

set -euo pipefail

PROJECT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
cd "$PROJECT_DIR"

make clean
make o3timised

# Arguments: grid size, timesteps, tree growth probability, fire probability.
GRID_SIZE="${1:-100}"
TIMESTEPS="${2:-500}"
P="${3:-0.01}"
F="${4:-0.001}"

time ./bin/fire-o3timised "$GRID_SIZE" "$TIMESTEPS" "$P" "$F"
