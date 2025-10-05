#!/usr/bin/env python3
"""Plot multi-track well logs from an Excel workbook.

This script is designed to reproduce a composite well-log similar to the
reference image by reading curves from an Excel file and arranging them into
parallel tracks.  Tracks and curves are configured through a JSON file (see
``configs/default_well_log.json`` for an example) so that the script can be
adapted to different datasets without editing the code.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, Iterable, Optional

import matplotlib.pyplot as plt
import pandas as pd

# The repository ships with a default configuration that mirrors the layout of
# the example figure.  Users can override it by supplying ``--config``.
DEFAULT_CONFIG_PATH = Path(__file__).with_name("configs").joinpath("default_well_log.json")


def load_config(path: Optional[Path]) -> Dict[str, Any]:
    """Load a configuration from JSON.

    Parameters
    ----------
    path:
        Path to the configuration file.  If ``None`` the bundled default is
        loaded.
    """

    if path is None:
        path = DEFAULT_CONFIG_PATH

    with Path(path).expanduser().resolve().open("r", encoding="utf-8") as handle:
        config: Dict[str, Any] = json.load(handle)
    return config


def read_excel_table(source: Path, sheet: Optional[str | int] = None) -> pd.DataFrame:
    """Read an Excel worksheet into a DataFrame and normalise column names."""

    df = pd.read_excel(source, sheet_name=sheet)
    # Normalise column names so that configuration keys do not have to worry
    # about trailing spaces or case differences.
    df.columns = [str(col).strip() for col in df.columns]
    return df


def _resolve_depth_series(df: pd.DataFrame, depth_column: str) -> pd.Series:
    if depth_column not in df.columns:
        raise KeyError(
            f"Depth column '{depth_column}' was not found in the Excel sheet. "
            "Check the configuration or specify --depth-column."
        )
    depth = df[depth_column]
    if not pd.api.types.is_numeric_dtype(depth):
        raise TypeError(
            f"Depth column '{depth_column}' must be numeric, got {depth.dtype}."
        )
    return depth


def _coerce_numeric(series: pd.Series, column: str) -> pd.Series:
    """Ensure the series is numeric, raising a helpful error otherwise."""

    if not pd.api.types.is_numeric_dtype(series):
        try:
            numeric = pd.to_numeric(series, errors="raise")
        except Exception as exc:  # pylint: disable=broad-except
            raise TypeError(
                f"Column '{column}' must contain numeric data to be plotted."
            ) from exc
        return numeric
    return series


def _plot_fill_between(
    ax: plt.Axes,
    depth: pd.Series,
    df: pd.DataFrame,
    track: Dict[str, Any],
) -> None:
    for fill in track.get("fill_between", []):
        left_col = fill["left"]
        right_col = fill["right"]
        left = _coerce_numeric(df[left_col], left_col)
        right = _coerce_numeric(df[right_col], right_col)
        mask: Optional[Iterable[bool]]
        condition = fill.get("where")
        if condition == "left>right":
            mask = left > right
        elif condition == "right>left":
            mask = right > left
        elif condition in (None, "all"):
            mask = None
        else:
            raise ValueError(
                f"Unsupported fill_between condition '{condition}'. "
                "Use 'left>right', 'right>left', or 'all'."
            )
        ax.fill_betweenx(
            depth,
            left,
            right,
            where=mask,
            color=fill.get("color", "#d3d3d3"),
            alpha=fill.get("alpha", 0.3),
            linewidth=0.0,
            interpolate=True,
            label=fill.get("label"),
        )


def _apply_track_options(ax: plt.Axes, track: Dict[str, Any]) -> None:
    ax.set_title(track.get("title", ""), fontsize=10)
    ax.set_xlabel(track.get("xlabel", track.get("title", "")))
    if "xlim" in track and track["xlim"]:
        ax.set_xlim(track["xlim"])
    if track.get("invert_x"):
        ax.invert_xaxis()
    scale = track.get("scale", "linear")
    ax.set_xscale(scale)
    facecolor = track.get("facecolor")
    if facecolor:
        ax.set_facecolor(facecolor)

    grid = track.get("grid", False)
    if isinstance(grid, bool):
        ax.grid(grid, linestyle="--", linewidth=0.5, alpha=0.6)
    elif isinstance(grid, dict):
        ax.grid(True, **grid)

    for line in track.get("reference_lines", []):
        ax.axvline(
            line.get("value"),
            color=line.get("color", "k"),
            linewidth=line.get("linewidth", 0.8),
            linestyle=line.get("linestyle", "--"),
            alpha=line.get("alpha", 0.8),
        )

    tick_params = track.get("tick_params")
    if tick_params:
        ax.tick_params(**tick_params)


def _plot_track(
    ax: plt.Axes,
    df: pd.DataFrame,
    depth: pd.Series,
    track: Dict[str, Any],
) -> None:
    _apply_track_options(ax, track)

    for curve in track.get("curves", []):
        column = curve["column"]
        if column not in df.columns:
            raise KeyError(
                f"Column '{column}' defined in track '{track.get('title')}' was not found."
            )
        series = _coerce_numeric(df[column], column)
        line, = ax.plot(
            series,
            depth,
            color=curve.get("color", "C0"),
            linewidth=curve.get("linewidth", 1.0),
            linestyle=curve.get("linestyle", "-"),
            label=curve.get("label", column),
            alpha=curve.get("alpha", 1.0),
        )

    _plot_fill_between(ax, depth, df, track)

    if track.get("show_legend", len(track.get("curves", [])) > 1):
        ax.legend(loc=track.get("legend_loc", "upper right"), fontsize=8)

    if track.get("twiny"):
        twin = ax.twiny()
        twin.set_xlim(ax.get_xlim())
        twin.set_xlabel(track["twiny"].get("xlabel", ""))


def plot_well_log(
    df: pd.DataFrame,
    config: Dict[str, Any],
    *,
    title: Optional[str] = None,
    output: Optional[Path] = None,
) -> Path:
    depth_column = config["depth_column"]
    depth = _resolve_depth_series(df, depth_column)

    track_defs = config.get("tracks", [])
    if not track_defs:
        raise ValueError("The configuration must define at least one track.")

    fig, axes = plt.subplots(
        nrows=1,
        ncols=len(track_defs),
        figsize=(3.2 * len(track_defs), 12),
        sharey=True,
        constrained_layout=False,
    )

    if len(track_defs) == 1:
        axes = [axes]  # type: ignore[assignment]

    for ax, track in zip(axes, track_defs):
        _plot_track(ax, df, depth, track)

    axes[0].set_ylabel(config.get("depth_label", depth_column))
    if config.get("invert_depth", True):
        axes[0].invert_yaxis()

    limits = config.get("depth_limits")
    if limits:
        axes[0].set_ylim(limits)

    for ax in axes[1:]:
        plt.setp(ax.get_yticklabels(), visible=False)
        ax.yaxis.set_ticks_position('none')

    for ax in axes:
        ax.tick_params(labelsize=8)

    fig.suptitle(title or config.get("title", "Well Log"), fontsize=14, y=0.95)
    fig.subplots_adjust(top=0.9, wspace=0.05)

    output_path = output or Path("well_log.png")
    fig.savefig(output_path, dpi=300, bbox_inches="tight")
    return output_path


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create a multi-track well log from an Excel file.",
    )
    parser.add_argument(
        "excel",
        type=Path,
        help="Path to the Excel workbook containing the log curves.",
    )
    parser.add_argument(
        "--sheet",
        type=str,
        default=None,
        help="Worksheet name or index to read (defaults to the first sheet).",
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=None,
        help="Path to a JSON configuration file describing the tracks.",
    )
    parser.add_argument(
        "--depth-column",
        type=str,
        default=None,
        help="Override the depth column defined in the configuration.",
    )
    parser.add_argument(
        "--title",
        type=str,
        default=None,
        help="Figure title to use instead of the configuration title.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Destination file for the plot (png, pdf, etc.).",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_arguments()

    config = load_config(args.config)
    if args.depth_column:
        config["depth_column"] = args.depth_column

    df = read_excel_table(args.excel, sheet=args.sheet)

    output_path = plot_well_log(df, config, title=args.title, output=args.output)
    print(f"Saved well log to {output_path}")


if __name__ == "__main__":
    main()
