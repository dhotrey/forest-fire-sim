#!/bin/bash
#SBATCH --job-name=cache-test
#SBATCH --partition=cpu
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1
#SBATCH --time=00:30:00
#SBATCH --output=cache-test-%j.out

set -euo pipefail

if (( $# == 0 )); then
    echo "Usage: sbatch $0 <build> [build ...]" >&2
    exit 1
fi

if ! command -v valgrind >/dev/null 2>&1; then
    echo "ERROR: valgrind is not available on this node" >&2
    exit 1
fi

for build in "$@"; do
    if [[ ! -x "$build" ]]; then
        echo "ERROR: missing or non-executable build: $build" >&2
        exit 1
    fi
done

echo "hostname: $(hostname)"
echo "job id:   ${SLURM_JOB_ID:-n/a}"
echo "builds:   $#"

for build in "$@"; do
    echo "=== cachegrind start: $build ==="
    valgrind --tool=cachegrind --cache-sim=yes \
        "$build" 1000 500 0.02 0.01 2>&1
    echo "=== cachegrind end: $build ==="
done
