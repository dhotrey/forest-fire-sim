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
GPROFNG_BIN="$HOME/gprofng/binutils-install/bin/gprofng"

DATA="data/${VERSION}"
CSV="${DATA}/benchmarking/benchmarks-${OPT}.csv"
GPROFNG="${DATA}/gprofng/gprofng-${OPT}.er"

GRIDS=(100 500 1000)
TIMESTEPS=500
REPS=5
P=0.01
F=0.001

mkdir -p "${DATA}/benchmarking" "${DATA}/gprofng"

if [[ ! -f "$CSV" ]]; then
    echo "run_number,grid_size,user_s,system_s,cpu_pct,total_s" > "$CSV"
fi

for GRID in "${GRIDS[@]}"; do
    for REP in $(seq 1 "$REPS"); do
        RUN_NUMBER=$(
            awk -F',' -v grid="$GRID" '
                $2 == grid { n++ }
                END { print n + 1 }
            ' "$CSV"
        )

        TIME_FILE=$(mktemp)

        /usr/bin/time -f "%U,%S,%P,%e" -o "$TIME_FILE" \
            "$BIN" "$GRID" "$TIMESTEPS" "$P" "$F"

        IFS=',' read USER SYS CPU TOTAL < "$TIME_FILE"
        rm "$TIME_FILE"

        CPU=${CPU%\%}

        echo "$RUN_NUMBER,$GRID,$USER,$SYS,$CPU,$TOTAL" >> "$CSV"
    done
done

"$GPROFNG_BIN" collect app \
    -o "$GPROFNG" \
    "$BIN" 1000 "$TIMESTEPS" "$P" "$F" \
    >/dev/null