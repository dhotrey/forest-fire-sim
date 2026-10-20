#!/bin/bash
#SBATCH --job-name=forest-fire
#SBATCH --partition=a100
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1
#SBATCH --time=00:15:00

set -euo pipefail

VERSION="${2:-v0.0}"
CONFIGS="${1:-o3}"

DATA="data/${VERSION}"

GRIDS=(5000)
TIMESTEPS=500
REPS=3
P=0.02
F=0.01

mkdir -p "${DATA}/benchmarking"

if [[ "$CONFIGS" == "all" ]]; then
    CONFIGS="o1,o2,o3"
fi
IFS=',' read -r -a OPTS <<< "$CONFIGS"
if (( ${#OPTS[@]} == 0 )); then
    echo "ERROR: no optimisation configurations supplied" >&2
    exit 1
fi

for OPT in "${OPTS[@]}"; do
    if [[ ! "$OPT" =~ ^o[123]$ ]]; then
        echo "ERROR: unsupported optimisation configuration: $OPT" >&2
        exit 1
    fi

    BIN="bin/fire-${VERSION}-${OPT}"
    if [[ ! -x "$BIN" ]]; then
        echo "ERROR: missing or non-executable binary: $BIN" >&2
        exit 1
    fi
done

CONFIG_LABEL=$(IFS=-; echo "${OPTS[*]}")
CSV="${DATA}/benchmarking/benchmarks-${CONFIG_LABEL}.csv"
echo "version,opt_flag,run_number,grid_size,user_s,system_s,cpu_pct,total_s,max_rss_kb,involuntary_ctx_switches,voluntary_ctx_switches,major_page_faults,minor_page_faults" > "$CSV"

AFFINITY=$(taskset -pc $$ 2>/dev/null | awk -F': ' '{print $2}' || true)
CORE=${AFFINITY%%,*}
if [[ -z "$CORE" ]]; then
    echo "WARNING: could not resolve pinned core; running unpinned"
    PIN=()
else
    PIN=(taskset -c "$CORE")
fi
FIRST_CORE=${CORE%%-*}

echo "=== execution environment ==="
echo "opt flags: ${OPTS[*]}"
echo "job id:   ${SLURM_JOB_ID:-n/a}"
echo "job node: ${SLURM_JOB_NODELIST:-n/a}"
echo "hostname: $(hostname)"
echo "kernel:   $(uname -r)"
echo "date:     $(date -Iseconds)"
echo "working directory: $(pwd)"
echo "command: $0 $CONFIGS $VERSION"
echo "parameters: grids=${GRIDS[*]} timesteps=$TIMESTEPS warmups=0 reps=$REPS p=$P f=$F"
echo "slurm allocation: job_cpus_per_node=${SLURM_JOB_CPUS_PER_NODE:-n/a} cpus_per_task=${SLURM_CPUS_PER_TASK:-n/a} ntasks=${SLURM_NTASKS:-n/a}"
echo "process affinity: ${AFFINITY:-unknown}"
echo "load average: $(cat /proc/loadavg 2>/dev/null || echo n/a)"
echo "uptime: $(uptime 2>/dev/null || echo n/a)"
lscpu | grep -E '^(Model name|Architecture|CPU\(s\)|Thread|Core|Socket|CPU max MHz|CPU min MHz|NUMA|Virtualization)' || true
grep -m1 'model name' /proc/cpuinfo || true
echo "pinned core: ${CORE:-none}"
echo "cpufreq governor: $(cat "/sys/devices/system/cpu/cpu${FIRST_CORE}/cpufreq/scaling_governor" 2>/dev/null || echo n/a)"
echo "cpufreq current kHz: $(cat "/sys/devices/system/cpu/cpu${FIRST_CORE}/cpufreq/scaling_cur_freq" 2>/dev/null || echo n/a)"
echo "compiler command: $(command -v g++ 2>/dev/null || echo n/a)"
g++ --version 2>/dev/null | sed -n '1p' || true
echo "time command: $(/usr/bin/time --version 2>/dev/null | sed -n '1p' || echo n/a)"
if command -v scontrol >/dev/null 2>&1 && [[ -n "${SLURM_JOB_ID:-}" ]]; then
    scontrol show job "$SLURM_JOB_ID" || true
fi

for OPT in "${OPTS[@]}"; do
    BIN="bin/fire-${VERSION}-${OPT}"
    echo "--- binary $OPT ---"
    ls -la "$BIN"
    file "$BIN" 2>/dev/null || true
    size "$BIN" 2>/dev/null || true
    ldd "$BIN" 2>/dev/null || true
    echo "md5:    $(md5sum "$BIN" | cut -d' ' -f1)"
    echo "sha256: $(sha256sum "$BIN" | cut -d' ' -f1)"
done
echo "============================="

print_run_context() {
    echo "date: $(date -Iseconds)"
    echo "load average: $(cat /proc/loadavg 2>/dev/null || echo n/a)"
    echo "cpu current kHz: $(cat "/sys/devices/system/cpu/cpu${FIRST_CORE}/cpufreq/scaling_cur_freq" 2>/dev/null || echo n/a)"
}

run_timed() {
    local opt="$1"
    local grid="$2"
    local rep="$3"
    local bin="bin/fire-${VERSION}-${opt}"
    local time_file
    time_file=$(mktemp)

    echo "=== timed run start: opt=$opt grid=$grid rep=$rep ==="
    print_run_context

    local status=0
    "${PIN[@]}" /usr/bin/time -f "%U,%S,%P,%e,%M,%c,%w,%F,%R" -o "$time_file" \
        "$bin" "$grid" "$TIMESTEPS" "$P" "$F" || status=$?

    if (( status != 0 )); then
        echo "ERROR: binary failed: opt=$opt grid=$grid rep=$rep status=$status" >&2
        rm -f "$time_file"
        return "$status"
    fi

    IFS=',' read -r TIME_USER TIME_SYS TIME_CPU TIME_TOTAL TIME_MAX_RSS \
        TIME_INVOL_CTX TIME_VOL_CTX TIME_MAJOR_FAULTS TIME_MINOR_FAULTS < "$time_file"
    rm "$time_file"

    TIME_CPU=${TIME_CPU%\%}
    if [[ -z "$TIME_TOTAL" ]]; then
        echo "ERROR: empty timing: opt=$opt grid=$grid rep=$rep" >&2
        return 1
    fi

    print_run_context
    echo "run=$rep grid=$grid user=${TIME_USER}s sys=${TIME_SYS}s cpu=${TIME_CPU}% total=${TIME_TOTAL}s max_rss=${TIME_MAX_RSS}KiB invol_ctx=$TIME_INVOL_CTX vol_ctx=$TIME_VOL_CTX major_faults=$TIME_MAJOR_FAULTS minor_faults=$TIME_MINOR_FAULTS [$opt]"
    echo "=== timed run end: opt=$opt grid=$grid rep=$rep ==="
}

for GRID in "${GRIDS[@]}"; do
    for REP in $(seq 1 "$REPS"); do
        # Reverse the order every repetition to balance temperature, boost
        # frequency, and other time-dependent effects between configurations.
        if (( REP % 2 == 1 )); then
            RUN_ORDER=("${OPTS[@]}")
        else
            RUN_ORDER=()
            for (( INDEX=${#OPTS[@]} - 1; INDEX >= 0; --INDEX )); do
                RUN_ORDER+=("${OPTS[INDEX]}")
            done
        fi

        for OPT in "${RUN_ORDER[@]}"; do
            run_timed "$OPT" "$GRID" "$REP"
            echo "$VERSION,$OPT,$REP,$GRID,$TIME_USER,$TIME_SYS,$TIME_CPU,$TIME_TOTAL,$TIME_MAX_RSS,$TIME_INVOL_CTX,$TIME_VOL_CTX,$TIME_MAJOR_FAULTS,$TIME_MINOR_FAULTS" >> "$CSV"
        done
    done
done

echo "benchmark CSV: $CSV"
