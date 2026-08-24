#!/bin/bash
#SBATCH --job-name=cache-test
#SBATCH --partition=a100
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1
#SBATCH --time=00:05:00
#SBATCH --output=cache-test-%j.out

set -euo pipefail

if (( $# == 0 || $# % 5 != 0 )); then
    echo "Usage: sbatch $0 <build> <grid> <timesteps> <p> <f> [<build> <grid> <timesteps> <p> <f> ...]" >&2
    exit 1
fi

if ! command -v valgrind >/dev/null 2>&1; then
    echo "ERROR: valgrind is not available on this node" >&2
    exit 1
fi

ARGS=("$@")
RUNS=$(( ${#ARGS[@]} / 5 ))

for (( i = 0; i < ${#ARGS[@]}; i += 5 )); do
    build="${ARGS[i]}"
    if [[ ! -x "$build" ]]; then
        echo "ERROR: missing or non-executable build: $build" >&2
        exit 1
    fi
done

echo "hostname: $(hostname)"
echo "job id:   ${SLURM_JOB_ID:-n/a}"
echo "runs:     $RUNS"

for (( i = 0; i < ${#ARGS[@]}; i += 5 )); do
    build="${ARGS[i]}"
    echo "=== cachegrind start: $build ==="
    valgrind --tool=cachegrind --cache-sim=yes \
        "$build" "${ARGS[i + 1]}" "${ARGS[i + 2]}" \
        "${ARGS[i + 3]}" "${ARGS[i + 4]}" 2>&1
    echo "=== cachegrind end: $build ==="
done
