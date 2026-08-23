#!/usr/bin/env python3
"""Plot benchmark CSV files.

Each input CSV must contain the columns ``version``, ``opt_flag``,
``grid_size``, and ``total_s``. Repeated benchmark runs are averaged before
plotting. One stacked line chart is written for every grid size present in the
input files.

Example:

    uv run --project tools/animation python tools/plot_benchmarks.py \
        data/v0.0/benchmarking/benchmarks-o1-o2.csv \
        data/v0.1/benchmarking/benchmarks-o1-o2.csv \
        --output-dir plots/benchmarks
"""

from __future__ import annotations

import argparse
import csv
import math
import re
from collections import defaultdict
from pathlib import Path
from statistics import fmean
from typing import DefaultDict

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt


REQUIRED_COLUMNS = {"version", "opt_flag", "grid_size", "total_s"}
VERSION_PATTERN = re.compile(r"^v?(\d+(?:\.\d+)*)$")

# Runtime data is stored as:
# grid size -> version -> optimisation -> individual run times
BenchmarkData = DefaultDict[
    int, DefaultDict[str, DefaultDict[str, list[float]]]
]


def version_sort_key(version: str) -> tuple[int, tuple[int, ...] | str]:
    """Sort semantic-looking versions numerically and other labels naturally."""
    match = VERSION_PATTERN.fullmatch(version)
    if match:
        return (0, tuple(int(part) for part in match.group(1).split(".")))
    return (1, version.casefold())


def read_benchmarks(csv_paths: list[Path]) -> BenchmarkData:
    """Read and combine benchmark rows from all supplied CSV files."""
    benchmarks: BenchmarkData = defaultdict(
        lambda: defaultdict(lambda: defaultdict(list))
    )

    for csv_path in csv_paths:
        if not csv_path.is_file():
            raise ValueError(f"CSV file does not exist: {csv_path}")

        with csv_path.open(newline="", encoding="utf-8") as csv_file:
            reader = csv.DictReader(csv_file)
            columns = set(reader.fieldnames or [])
            missing = REQUIRED_COLUMNS - columns
            if missing:
                missing_columns = ", ".join(sorted(missing))
                raise ValueError(
                    f"{csv_path} is missing required column(s): {missing_columns}"
                )

            for row_number, row in enumerate(reader, start=2):
                version = (row["version"] or "").strip()
                opt_flag = (row["opt_flag"] or "").strip()
                if not version or not opt_flag:
                    raise ValueError(
                        f"{csv_path}:{row_number} has an empty version or opt_flag"
                    )

                try:
                    grid_size = int(row["grid_size"])
                    runtime = float(row["total_s"])
                except (TypeError, ValueError) as error:
                    raise ValueError(
                        f"{csv_path}:{row_number} has an invalid grid_size or total_s"
                    ) from error

                if grid_size <= 0 or not math.isfinite(runtime) or runtime < 0:
                    raise ValueError(
                        f"{csv_path}:{row_number} has an invalid grid size or runtime"
                    )

                benchmarks[grid_size][version][opt_flag].append(runtime)

    if not benchmarks:
        raise ValueError("No benchmark rows were found")
    return benchmarks


def plot_grid(
    grid_size: int,
    versions: list[str],
    optimisation_runs: dict[str, dict[str, list[float]]],
    output_dir: Path,
) -> Path:
    """Create and save the stacked runtime chart for one grid size."""
    optimisations = sorted(
        {
            opt_flag
            for version in versions
            for opt_flag in optimisation_runs[version]
        }
    )
    x_positions = list(range(len(versions)))
    series: list[list[float]] = []

    for opt_flag in optimisations:
        series.append(
            [
                fmean(optimisation_runs[version].get(opt_flag, [0.0]))
                for version in versions
            ]
        )

    figure, axes = plt.subplots(figsize=(10, 6))
    axes.stackplot(
        x_positions,
        *series,
        labels=optimisations,
        alpha=0.8,
        edgecolor="white",
        linewidth=0.8,
    )

    # Draw the cumulative boundaries explicitly so the stacked series remain
    # legible when printed or viewed without the filled regions.
    cumulative = [0.0] * len(versions)
    for runtime_series in series:
        cumulative = [
            current + runtime for current, runtime in zip(cumulative, runtime_series)
        ]
        axes.plot(x_positions, cumulative, color="#333333", linewidth=1.0)

    axes.set_xticks(x_positions, versions)
    axes.set_xlabel("Program version")
    axes.set_ylabel("Mean runtime (s)")
    axes.set_title(f"Benchmark runtime by version ({grid_size}x{grid_size})")
    axes.grid(axis="y", alpha=0.3)
    axes.legend(title="Optimisation", loc="upper left")
    figure.tight_layout()

    output_path = output_dir / f"benchmark-{grid_size}x{grid_size}.png"
    figure.savefig(output_path, dpi=180)
    plt.close(figure)
    return output_path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Create one stacked runtime chart per benchmark grid size."
    )
    parser.add_argument(
        "csv_files",
        nargs="+",
        type=Path,
        metavar="CSV",
        help="benchmark CSV file(s) to combine",
    )
    parser.add_argument(
        "-o",
        "--output-dir",
        type=Path,
        default=Path("plots/benchmarks"),
        help="directory for generated PNG charts (default: plots/benchmarks)",
    )
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    try:
        benchmarks = read_benchmarks(args.csv_files)
        args.output_dir.mkdir(parents=True, exist_ok=True)
        output_paths = []
        for grid_size in sorted(benchmarks):
            versions = sorted(benchmarks[grid_size], key=version_sort_key)
            output_paths.append(
                plot_grid(
                    grid_size,
                    versions,
                    benchmarks[grid_size],
                    args.output_dir,
                )
            )
    except (OSError, ValueError) as error:
        parser.error(str(error))

    for output_path in output_paths:
        print(output_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
