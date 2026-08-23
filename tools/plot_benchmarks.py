#!/usr/bin/env python3
"""Plot benchmark CSV files.

Each input CSV must contain the columns ``version``, ``opt_flag``,
``grid_size``, and ``total_s``. Repeated benchmark runs are averaged before
plotting. One two-panel performance chart is written for every grid size
present in the input files. The first panel shows absolute runtimes and the
second highlights the percentage change from each preceding version.

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
from matplotlib.axes import Axes
from matplotlib.ticker import AutoMinorLocator, FuncFormatter, MaxNLocator


REQUIRED_COLUMNS = {"version", "opt_flag", "grid_size", "total_s"}
VERSION_PATTERN = re.compile(r"^v?(\d+(?:\.\d+)*)$")
SERIES_COLOURS = ("#2563EB", "#F97316", "#16A34A", "#9333EA")
BACKGROUND_COLOUR = "#F8FAFC"
GRID_COLOUR = "#CBD5E1"
TEXT_COLOUR = "#0F172A"
MUTED_TEXT_COLOUR = "#64748B"

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
    """Create and save the runtime and version-change chart for one grid size."""
    optimisations = sorted(
        {
            opt_flag
            for version in versions
            for opt_flag in optimisation_runs[version]
        }
    )
    x_positions = list(range(len(versions)))
    mean_series = {
        opt_flag: [
            (
                fmean(optimisation_runs[version][opt_flag])
                if opt_flag in optimisation_runs[version]
                else math.nan
            )
            for version in versions
        ]
        for opt_flag in optimisations
    }
    maximum_runtime = max(
        runtime
        for runtimes in mean_series.values()
        for runtime in runtimes
        if math.isfinite(runtime)
    )
    runtime_precision = 3 if maximum_runtime < 1 else 2

    figure, (runtime_axes, change_axes) = plt.subplots(
        1,
        2,
        figsize=(13, 6.8),
        gridspec_kw={"width_ratios": (1.45, 1)},
    )
    figure.patch.set_facecolor(BACKGROUND_COLOUR)

    for series_index, opt_flag in enumerate(optimisations):
        colour = SERIES_COLOURS[series_index % len(SERIES_COLOURS)]
        runtimes = mean_series[opt_flag]
        lower_bounds = [
            (
                min(optimisation_runs[version][opt_flag])
                if opt_flag in optimisation_runs[version]
                else math.nan
            )
            for version in versions
        ]
        upper_bounds = [
            (
                max(optimisation_runs[version][opt_flag])
                if opt_flag in optimisation_runs[version]
                else math.nan
            )
            for version in versions
        ]

        runtime_axes.fill_between(
            x_positions,
            lower_bounds,
            upper_bounds,
            color=colour,
            alpha=0.12,
            linewidth=0,
        )
        runtime_axes.plot(
            x_positions,
            runtimes,
            color=colour,
            label=opt_flag,
            linewidth=2.5,
            marker="o",
            markersize=7,
            markeredgecolor="white",
            markeredgewidth=1.5,
            zorder=3,
        )
        label_offset = 10 if series_index % 2 == 0 else -16
        for x_position, runtime in zip(x_positions, runtimes):
            if math.isfinite(runtime):
                runtime_axes.annotate(
                    f"{runtime:.{runtime_precision}f}s",
                    (x_position, runtime),
                    xytext=(0, label_offset),
                    textcoords="offset points",
                    ha="center",
                    va="bottom" if label_offset > 0 else "top",
                    color=colour,
                    fontsize=8,
                    fontweight="bold",
                )

    _style_axes(runtime_axes)
    runtime_axes.set_xticks(x_positions, versions)
    runtime_axes.set_xlabel("Program version")
    runtime_axes.set_ylabel("Mean runtime (seconds)")
    runtime_axes.set_title("Absolute runtime", loc="left", fontweight="bold")
    runtime_axes.set_ylim(bottom=0)
    runtime_axes.yaxis.set_major_locator(MaxNLocator(nbins=10, min_n_ticks=6))
    runtime_axes.yaxis.set_minor_locator(AutoMinorLocator(2))
    runtime_axes.yaxis.set_major_formatter(
        FuncFormatter(lambda value, _: f"{value:.{runtime_precision}f}")
    )
    runtime_axes.grid(axis="y", which="minor", color=GRID_COLOUR, alpha=0.2)
    runtime_axes.legend(
        title="Optimisation",
        frameon=False,
        ncols=min(len(optimisations), 4),
        loc="upper right",
    )

    transition_labels = [
        f"{previous} → {current}"
        for previous, current in zip(versions, versions[1:])
    ]
    transition_positions = list(range(len(transition_labels)))
    bar_width = 0.72 / max(len(optimisations), 1)
    all_changes: list[float] = []
    for series_index, opt_flag in enumerate(optimisations):
        colour = SERIES_COLOURS[series_index % len(SERIES_COLOURS)]
        offset = (series_index - (len(optimisations) - 1) / 2) * bar_width
        bar_positions = [position + offset for position in transition_positions]
        changes = []
        for previous, current in zip(
            mean_series[opt_flag], mean_series[opt_flag][1:]
        ):
            if math.isfinite(previous) and math.isfinite(current) and previous > 0:
                changes.append((current / previous - 1) * 100)
            else:
                changes.append(math.nan)
        all_changes.extend(change for change in changes if math.isfinite(change))

        bars = change_axes.bar(
            bar_positions,
            changes,
            width=bar_width * 0.88,
            color=colour,
            alpha=0.9,
            label=opt_flag,
            zorder=3,
        )
        change_axes.bar_label(
            bars,
            labels=[
                f"{change:+.1f}%" if math.isfinite(change) else ""
                for change in changes
            ],
            padding=3,
            fontsize=8,
            color=TEXT_COLOUR,
            fontweight="bold",
        )

    _style_axes(change_axes)
    change_axes.axhline(0, color=TEXT_COLOUR, linewidth=1.1, zorder=2)
    change_axes.set_xticks(transition_positions, transition_labels, rotation=12)
    change_axes.set_xlabel("Version transition")
    change_axes.set_ylabel("Runtime change (%)")
    change_axes.set_title(
        "Change from previous version", loc="left", fontweight="bold"
    )
    change_axes.yaxis.set_major_locator(MaxNLocator(nbins=10, min_n_ticks=6))
    change_axes.yaxis.set_minor_locator(AutoMinorLocator(2))
    change_axes.yaxis.set_major_formatter(
        FuncFormatter(lambda value, _: f"{value:.1f}%")
    )
    change_axes.grid(axis="y", which="minor", color=GRID_COLOUR, alpha=0.2)
    if all_changes:
        change_span = max(max(all_changes) - min(all_changes), 10)
        change_axes.set_ylim(
            min(min(all_changes) - change_span * 0.12, -5),
            max(max(all_changes) + change_span * 0.18, 5),
        )
    change_axes.text(
        0.02,
        0.98,
        "↑ slower",
        transform=change_axes.transAxes,
        va="top",
        color=MUTED_TEXT_COLOUR,
        fontsize=9,
    )
    change_axes.text(
        0.02,
        0.02,
        "↓ faster",
        transform=change_axes.transAxes,
        va="bottom",
        color=MUTED_TEXT_COLOUR,
        fontsize=9,
    )

    figure.suptitle(
        f"{grid_size} × {grid_size} grid performance",
        x=0.06,
        y=0.98,
        ha="left",
        color=TEXT_COLOUR,
        fontsize=18,
        fontweight="bold",
    )
    figure.text(
        0.06,
        0.93,
        "Lower is better · shaded bands show the range across repeated runs",
        ha="left",
        color=MUTED_TEXT_COLOUR,
        fontsize=10,
    )
    figure.tight_layout(rect=(0.03, 0.02, 0.98, 0.91))

    output_path = output_dir / f"benchmark-{grid_size}x{grid_size}.png"
    figure.savefig(
        output_path,
        dpi=200,
        facecolor=figure.get_facecolor(),
        bbox_inches="tight",
    )
    plt.close(figure)
    return output_path


def _style_axes(axes: Axes) -> None:
    """Apply shared styling to a benchmark chart panel."""
    axes.set_facecolor("white")
    axes.set_axisbelow(True)
    axes.grid(axis="y", color=GRID_COLOUR, alpha=0.55, linewidth=0.8)
    axes.tick_params(colors=MUTED_TEXT_COLOUR, labelsize=9)
    axes.xaxis.label.set_color(MUTED_TEXT_COLOUR)
    axes.yaxis.label.set_color(MUTED_TEXT_COLOUR)
    axes.title.set_color(TEXT_COLOUR)
    axes.spines["top"].set_visible(False)
    axes.spines["right"].set_visible(False)
    axes.spines["left"].set_color(GRID_COLOUR)
    axes.spines["bottom"].set_color(GRID_COLOUR)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Create one performance chart per benchmark grid size."
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
