#!/bin/bash

CONFIGS="$1"
VERSION="${2:-v0.0}"

mkdir -p "data/${VERSION}/slurm-logs"

if [[ "$CONFIGS" == "all" ]]; then
    CONFIGS="o1,o2,o3"
fi

IFS=',' read -ra CONFIGS <<< "$CONFIGS"

for OPT in "${CONFIGS[@]}"; do
    sbatch \
        --job-name="ff_${OPT}" \
        --output="data/${VERSION}/slurm-logs/slurm-${OPT}.out" \
        run.slurm.sh "$OPT" "$VERSION"
done