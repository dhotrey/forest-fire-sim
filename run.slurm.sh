#!/bin/bash
#SBATCH --job-name=forest-fire
#SBATCH --partition=cpu
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=2
#SBATCH --time=00:07:00

VERSION="${2:-v0.0}"
OPT="$1"

BIN="bin/fire-${VERSION}-${OPT}"
DATA="data/${VERSION}"

CSV="${DATA}/benchmarking/benchmarks-${OPT}.csv"
if [[ ! -f "$CSV" ]]; then
    echo "run_number,grid_size,user_s,system_s,cpu_pct,total_s" > "$CSV"
fi
GPROFNG="${DATA}/gprofng/gprofng-${OPT}.er"

GRIDS=(100 500 1000)
TIMESTEPS=500
REPS=5
P=0.01
F=0.001

for GRID in "${GRIDS[@]}"; do
    SUM=0

    for REP in $(seq 1 "$REPS"); do
        RUN_NUMBER=$(
            awk -F',' -v grid="$GRID" '
                $2 == grid { n++ }
                END { print n + 1 }
            ' "$CSV"
        )

        TIME=$(
            /usr/bin/time -f "%U,%S,%P,%e" \
                "$BIN" "$GRID" "$TIMESTEPS" "$P" "$F" \
                2>&1 >/dev/null
        )

        IFS=',' read USER SYS CPU TOTAL <<< "$TIME"
        CPU=${CPU%\%}

        echo "$RUN_NUMBER,$GRID,$USER,$SYS,$CPU,$TOTAL" >> "$CSV"

        SUM=$(awk -v a="$SUM" -v b="$TOTAL" 'BEGIN { print a + b }')
    done

    MEAN=$(awk -v sum="$SUM" -v reps="$REPS" 'BEGIN { print sum / reps }')
    echo "${GRID}x${GRID}: mean = ${MEAN}s"
done

gprofng collect app \
    -o "$GPROFNG" \
    "$BIN" 1000 "$TIMESTEPS" "$P" "$F" \
    >/dev/null
