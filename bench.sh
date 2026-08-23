#!/bin/bash

set -euo pipefail

CONFIGS="${1:-o1,o2}"
VERSION="${2:-v0.1}"

if [[ "$CONFIGS" == "all" ]]; then
    CONFIGS="o1,o2,o3"
fi

IFS=',' read -r -a CONFIG_LIST <<< "$CONFIGS"
if (( ${#CONFIG_LIST[@]} == 0 )); then
    echo "Usage: $0 <o1,o2|all> [version]" >&2
    exit 1
fi

for OPT in "${CONFIG_LIST[@]}"; do
    if [[ ! "$OPT" =~ ^o[123]$ ]]; then
        echo "Unsupported optimisation configuration: $OPT" >&2
        exit 1
    fi
done

CONFIG_LABEL=$(IFS=-; echo "${CONFIG_LIST[*]}")
LOG_DIR="data/${VERSION}/slurm-logs"
LOG_FILE="${LOG_DIR}/slurm-${CONFIG_LABEL}.out"

mkdir -p "$LOG_DIR"

sbatch \
    --job-name="ff_${CONFIG_LABEL}" \
    --output="$LOG_FILE" \
    run.slurm.sh "$CONFIGS" "$VERSION"
