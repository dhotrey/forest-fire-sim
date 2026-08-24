#!/bin/bash
#SBATCH --job-name=forest-fire-all
#SBATCH --partition=cpu
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1
#SBATCH --time=00:10:00

set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

CONFIGS="${1:-o1,o2}"
VERSIONS="${2:-v0.0}"

if [[ "$CONFIGS" == "all" ]]; then
    CONFIGS="o1,o2,o3"
fi

IFS=',' read -r -a OPTS <<< "$CONFIGS"
IFS=',' read -r -a VERSION_LIST <<< "$VERSIONS"

if [[ -z "$CONFIGS" || -z "$VERSIONS" || ${#OPTS[@]} -eq 0 || ${#VERSION_LIST[@]} -eq 0 ]]; then
    echo "Usage: $0 <o1,o2,o3|all> <v0.1,v0.2,...>" >&2
    exit 1
fi

for OPT in "${OPTS[@]}"; do
    if [[ ! "$OPT" =~ ^o[123]$ ]]; then
        echo "ERROR: unsupported optimisation configuration: $OPT" >&2
        exit 1
    fi
done

for VERSION in "${VERSION_LIST[@]}"; do
    if [[ ! "$VERSION" =~ ^v[0-9]+(\.[0-9]+)*$ ]]; then
        echo "ERROR: unsupported version: $VERSION" >&2
        exit 1
    fi

    for OPT in "${OPTS[@]}"; do
        BIN="builds/${VERSION}/fire-${VERSION}-${OPT}"
        if [[ ! -x "$BIN" ]]; then
            echo "ERROR: missing or non-executable binary: $BIN" >&2
            exit 1
        fi
    done
done

CONFIG_LABEL=$(IFS=-; echo "${OPTS[*]}")
VERSION_LABEL=$(IFS=-; echo "${VERSION_LIST[*]}")

# Submit one job so all versions share the same compute allocation.
if [[ -z "${SLURM_JOB_ID:-}" ]]; then
    LOG_DIR="data/benchall"
    DATE_LABEL=$(date -u +%Y%m%d-%H%M%S)
    LOG_FILE="${SCRIPT_DIR}/${LOG_DIR}/slurm-out-${VERSION_LABEL}-${DATE_LABEL}.out"

    mkdir -p "$LOG_DIR"
    echo "Submitting consolidated benchmark job"
    echo "SLURM log: $LOG_FILE"
    sbatch \
        --job-name="ff_${VERSION_LABEL}_${CONFIG_LABEL}" \
        --partition=cpu \
        --time=00:10:00 \
        --output="$LOG_FILE" \
        --chdir="$SCRIPT_DIR" \
        "$SCRIPT_DIR/benchall.sh" "$CONFIGS" "$VERSIONS"
    exit 0
fi

GRIDS=(100 500 1000)
TIMESTEPS=500
WARMUP_REPS=2
REPS=5
P=0.02
F=0.01

for VERSION in "${VERSION_LIST[@]}"; do
    mkdir -p "data/${VERSION}/benchmarking"
    CSV="data/${VERSION}/benchmarking/benchmarks-${CONFIG_LABEL}.csv"
    echo "version,opt_flag,run_number,grid_size,user_s,system_s,cpu_pct,total_s,max_rss_kb,involuntary_ctx_switches,voluntary_ctx_switches,major_page_faults,minor_page_faults" > "$CSV"
done

AFFINITY=$(taskset -pc $$ 2>/dev/null | awk -F': ' '{print $2}' || true)
CORE=${AFFINITY%%,*}
if [[ -z "$CORE" ]]; then
    echo "WARNING: could not resolve pinned core; running unpinned"
    PIN=()
else
    PIN=(taskset -c "$CORE")
fi
FIRST_CORE=${CORE%%-*}

echo "=== consolidated benchmark environment ==="
echo "opt flags: ${OPTS[*]}"
echo "versions: ${VERSION_LIST[*]}"
echo "job id:   ${SLURM_JOB_ID:-n/a}"
echo "job node: ${SLURM_JOB_NODELIST:-n/a}"
echo "hostname: $(hostname)"
echo "kernel:   $(uname -r)"
echo "date:     $(date -Iseconds)"
echo "working directory: $(pwd)"
echo "parameters: grids=${GRIDS[*]} timesteps=$TIMESTEPS warmups=$WARMUP_REPS reps=$REPS p=$P f=$F"
echo "slurm allocation: job_cpus_per_node=${SLURM_JOB_CPUS_PER_NODE:-n/a} cpus_per_task=${SLURM_CPUS_PER_TASK:-n/a} ntasks=${SLURM_NTASKS:-n/a}"
echo "process affinity: ${AFFINITY:-unknown}"
echo "load average: $(cat /proc/loadavg 2>/dev/null || echo n/a)"
echo "uptime: $(uptime 2>/dev/null || echo n/a)"
lscpu | grep -E '^(Model name|Architecture|CPU\(s\)|Thread|Core|Socket|CPU max MHz|CPU min MHz|NUMA|Virtualization)' || true
grep -m1 'model name' /proc/cpuinfo || true
echo "pinned core: ${CORE:-none}"
echo "cpufreq governor: $(cat "/sys/devices/system/cpu/cpu${FIRST_CORE}/cpufreq/scaling_governor" 2>/dev/null || echo n/a)"
echo "cpufreq current kHz: $(cat "/sys/devices/system/cpu/cpu${FIRST_CORE}/cpufreq/scaling_cur_freq" 2>/dev/null || echo n/a)"
echo "time command: $(/usr/bin/time --version 2>/dev/null | sed -n '1p' || echo n/a)"

for VERSION in "${VERSION_LIST[@]}"; do
    for OPT in "${OPTS[@]}"; do
        BIN="builds/${VERSION}/fire-${VERSION}-${OPT}"
        echo "--- binary $VERSION/$OPT ---"
        ls -la "$BIN"
        file "$BIN" 2>/dev/null || true
        size "$BIN" 2>/dev/null || true
        ldd "$BIN" 2>/dev/null || true
        echo "md5:    $(md5sum "$BIN" | cut -d' ' -f1)"
        echo "sha256: $(sha256sum "$BIN" | cut -d' ' -f1)"
    done
done
echo "========================================"

print_run_context() {
    echo "date: $(date -Iseconds)"
    echo "load average: $(cat /proc/loadavg 2>/dev/null || echo n/a)"
    echo "cpu current kHz: $(cat "/sys/devices/system/cpu/cpu${FIRST_CORE}/cpufreq/scaling_cur_freq" 2>/dev/null || echo n/a)"
}

run_timed() {
    local version="$1"
    local opt="$2"
    local grid="$3"
    local rep="$4"
    local bin="builds/${version}/fire-${version}-${opt}"
    local time_file
    time_file=$(mktemp)

    echo "=== timed run start: version=$version opt=$opt grid=$grid rep=$rep ==="
    print_run_context

    local status=0
    "${PIN[@]}" /usr/bin/time -f "%U,%S,%P,%e,%M,%c,%w,%F,%R" -o "$time_file" \
        "$bin" "$grid" "$TIMESTEPS" "$P" "$F" || status=$?

    if (( status != 0 )); then
        echo "ERROR: binary failed: version=$version opt=$opt grid=$grid rep=$rep status=$status" >&2
        rm -f "$time_file"
        return "$status"
    fi

    IFS=',' read -r TIME_USER TIME_SYS TIME_CPU TIME_TOTAL TIME_MAX_RSS \
        TIME_INVOL_CTX TIME_VOL_CTX TIME_MAJOR_FAULTS TIME_MINOR_FAULTS < "$time_file"
    rm "$time_file"

    TIME_CPU=${TIME_CPU%\%}
    if [[ -z "$TIME_TOTAL" ]]; then
        echo "ERROR: empty timing: version=$version opt=$opt grid=$grid rep=$rep" >&2
        return 1
    fi

    print_run_context
    echo "version=$version run=$rep grid=$grid user=${TIME_USER}s sys=${TIME_SYS}s cpu=${TIME_CPU}% total=${TIME_TOTAL}s max_rss=${TIME_MAX_RSS}KiB invol_ctx=$TIME_INVOL_CTX vol_ctx=$TIME_VOL_CTX major_faults=$TIME_MAJOR_FAULTS minor_faults=$TIME_MINOR_FAULTS [$opt]"
    echo "=== timed run end: version=$version opt=$opt grid=$grid rep=$rep ==="
}

for VERSION in "${VERSION_LIST[@]}"; do
    CSV="data/${VERSION}/benchmarking/benchmarks-${CONFIG_LABEL}.csv"

    echo "=== initial size-1 warm-up runs: version=$VERSION ==="
    for OPT in "${OPTS[@]}"; do
        BIN="builds/${VERSION}/fire-${VERSION}-${OPT}"
        echo "=== size-1 warm-up start: version=$VERSION opt=$OPT ==="
        "${PIN[@]}" "$BIN" 1 1 "$P" "$F"
        echo "=== size-1 warm-up end: version=$VERSION opt=$OPT ==="
    done

    for GRID in "${GRIDS[@]}"; do
        # Warm-up runs (untimed) populate caches and branch predictors.
        for WARMUP in $(seq 1 "$WARMUP_REPS"); do
            for OPT in "${OPTS[@]}"; do
                BIN="builds/${VERSION}/fire-${VERSION}-${OPT}"
                echo "=== warm-up start: version=$VERSION opt=$OPT grid=$GRID rep=$WARMUP ==="
                "${PIN[@]}" "$BIN" "$GRID" "$TIMESTEPS" "$P" "$F"
                echo "=== warm-up end: version=$VERSION opt=$OPT grid=$GRID rep=$WARMUP ==="
            done
        done

        for REP in $(seq 1 "$REPS"); do
            # Reverse the order every repetition to balance time-dependent effects.
            if (( REP % 2 == 1 )); then
                RUN_ORDER=("${OPTS[@]}")
            else
                RUN_ORDER=()
                for (( INDEX=${#OPTS[@]} - 1; INDEX >= 0; --INDEX )); do
                    RUN_ORDER+=("${OPTS[INDEX]}")
                done
            fi

            for OPT in "${RUN_ORDER[@]}"; do
                run_timed "$VERSION" "$OPT" "$GRID" "$REP"
                echo "$VERSION,$OPT,$REP,$GRID,$TIME_USER,$TIME_SYS,$TIME_CPU,$TIME_TOTAL,$TIME_MAX_RSS,$TIME_INVOL_CTX,$TIME_VOL_CTX,$TIME_MAJOR_FAULTS,$TIME_MINOR_FAULTS" >> "$CSV"
            done
        done
    done

    echo "benchmark CSV: $CSV"
done
