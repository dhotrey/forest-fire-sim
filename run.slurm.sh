#!/bin/bash
#SBATCH --job-name=forest-fire
#SBATCH --partition=cpu
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1
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
WARMUP_REPS=2
REPS=5
P=0.01
F=0.001

mkdir -p "${DATA}/benchmarking" "${DATA}/gprofng"

echo "=== execution environment ==="
echo "opt flag: ${OPT}"
echo "job id:   ${SLURM_JOB_ID:-n/a}"
echo "job node: ${SLURM_JOB_NODELIST:-n/a}"
echo "hostname: $(hostname)"
echo "kernel:   $(uname -r)"
echo "date:     $(date -Iseconds)"
lscpu | grep -E '^(Model name|Architecture|CPU\(s\)|Thread|Core|Socket|CPU max MHz|CPU min MHz|NUMA|Virtualization)' || true
grep -m1 'model name' /proc/cpuinfo || true
echo "cpufreq governor: $(cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_governor 2>/dev/null || echo 'n/a')"
echo "binary:   $(ls -la "$BIN" 2>/dev/null || echo "MISSING: $BIN")"
echo "md5:      $(md5sum "$BIN" 2>/dev/null | cut -d' ' -f1)"
CORE=$(taskset -pc $$ 2>/dev/null | awk -F': ' '{print $2}' | cut -d',' -f1)
if [[ -z "$CORE" ]]; then
    echo "WARNING: could not resolve pinned core; running unpinned"
    PIN=""
else
    PIN="taskset -c $CORE"
fi
echo "pinned core: ${CORE:-none} (allowed cpus: $(taskset -pc $$ 2>/dev/null | awk -F': ' '{print $2}' || echo unknown))"
if [[ -x "$BIN" ]]; then
    "$BIN" 1 1 "$P" "$F" 2>&1 | grep -v '^$'
fi
echo "============================="

if [[ ! -f "$CSV" ]]; then
    echo "run_number,grid_size,user_s,system_s,cpu_pct,total_s" > "$CSV"
fi

run_timed() {
    local grid="$1"
    local time_file
    time_file=$(mktemp)

    $PIN /usr/bin/time -f "%U,%S,%P,%e" -o "$time_file" \
        "$BIN" "$grid" "$TIMESTEPS" "$P" "$F" >/dev/null

    local USER SYS CPU TOTAL
    IFS=',' read USER SYS CPU TOTAL < "$time_file"
    rm "$time_file"

    CPU=${CPU%\%}
    echo "$1,$USER,$SYS,$CPU,$TOTAL"
}

for GRID in "${GRIDS[@]}"; do
    # Warm-up runs (untimed): populate caches/branch predictors so timed
    # runs are comparable between binaries.
    for _ in $(seq 1 "$WARMUP_REPS"); do
        $PIN "$BIN" "$GRID" "$TIMESTEPS" "$P" "$F" >/dev/null
    done

    for REP in $(seq 1 "$REPS"); do
        RUN_NUMBER=$(
            awk -F',' -v grid="$GRID" '
                $2 == grid { n++ }
                END { print n + 1 }
            ' "$CSV"
        )

        IFS=',' read -r _ USER SYS CPU TOTAL <<< "$(run_timed "$GRID")"

        [[ -z "$TOTAL" ]] && echo "ERROR: empty timing for grid=$GRID rep=$REP" >&2

        echo "run=$RUN_NUMBER grid=$GRID rep=$REP user=${USER}s sys=${SYS}s cpu=${CPU}% total=${TOTAL}s [${OPT}]"
        echo "$RUN_NUMBER,$GRID,$USER,$SYS,$CPU,$TOTAL" >> "$CSV"
    done
done

"$GPROFNG_BIN" collect app \
    -o "$GPROFNG" \
    "$BIN" 1000 "$TIMESTEPS" "$P" "$F" \
    >/dev/null || echo "WARNING: gprofng collection failed (exit $?)"