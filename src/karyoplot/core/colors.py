"""Color palette loading + hex/RGB conversion.

The Barthel brand palette is exposed as named constants for use in
themed plots. Color file loaders handle the standard KaryoScope
``{database}.{featureset}.colors.txt`` tab-separated format with an
optional header row.

Examples:
    >>> from karyoplot.core import colors
    >>> palette = colors.load_palette("KS_human_CHM13.repeat.colors.txt")
    >>> colors.hex_to_rgb("#F07167")
    (240, 113, 103)
    >>> colors.BARTHEL["coral"]
    '#F07167'
"""

from __future__ import annotations

import os
from typing import Iterable

DEFAULT_COLOR = "#CCCCCC"


# matplotlib's tab10 / tab20 qualitative palettes, baked in as hex tuples
# so callers can avoid a matplotlib import for simple categorical coloring.
TAB10: tuple[str, ...] = (
    "#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd",
    "#8c564b", "#e377c2", "#7f7f7f", "#bcbd22", "#17becf",
)
TAB20: tuple[str, ...] = (
    "#1f77b4", "#aec7e8", "#ff7f0e", "#ffbb78", "#2ca02c",
    "#98df8a", "#d62728", "#ff9896", "#9467bd", "#c5b0d5",
    "#8c564b", "#c49c94", "#e377c2", "#f7b6d2", "#7f7f7f",
    "#c7c7c7", "#bcbd22", "#dbdb8d", "#17becf", "#9edae5",
)


def qualitative_palette(n: int, palette: tuple[str, ...] = TAB20) -> list[str]:
    """Return ``n`` colors cycled from a qualitative palette (default :data:`TAB20`)."""
    if not palette:
        raise ValueError("palette must be non-empty")
    return [palette[i % len(palette)] for i in range(n)]


# Barthel brand palette (per global CLAUDE.md)
BARTHEL: dict[str, str] = {
    "black": "#000000",
    "white": "#FFFFFF",
    "gray": "#545454",
    "lavender": "#C4A9E8",
    "green": "#40D392",
    "blue": "#60A5FA",
    "coral": "#F07167",
    "yellow": "#FBBF24",
    "emerald": "#10B981",
    "royal_blue": "#3B82F6",
}


def load_palette(filepath: str | os.PathLike) -> dict[str, str]:
    """Load a single color file (tab-separated: feature, hex).

    Skips a header row if the first column is literally ``feature``.
    Returns an empty dict if the file does not exist (matching the
    behaviour of the legacy ``karyoscope_utils.colors.load_color_file``).
    """
    palette: dict[str, str] = {}
    if not os.path.exists(filepath):
        return palette
    with open(filepath, "r") as f:
        for i, line in enumerate(f):
            parts = line.strip().split("\t")
            if len(parts) >= 2:
                feature, color = parts[0], parts[1]
                if i == 0 and feature.lower() == "feature":
                    continue
                palette[feature] = color
    return palette


def load_palettes(
    colors_dir: str | os.PathLike,
    database: str,
    featuresets: Iterable[str],
) -> dict[str, dict[str, str]]:
    """Load multiple color files keyed by featureset.

    Looks up files of the form ``{database}.{featureset}.colors.txt``
    inside ``colors_dir``.
    """
    out: dict[str, dict[str, str]] = {}
    for fs in featuresets:
        path = os.path.join(colors_dir, f"{database}.{fs}.colors.txt")
        out[fs] = load_palette(path)
    return out


def get_color(
    feature: str,
    palette: dict[str, str],
    default: str = DEFAULT_COLOR,
) -> str:
    """Look up ``feature`` in ``palette``; return ``default`` if missing."""
    return palette.get(feature, default)


def hex_to_rgb(hex_str: str) -> tuple[int, int, int]:
    """Convert ``#RRGGBB`` (or ``RRGGBB``) to an (r, g, b) tuple."""
    s = hex_str.lstrip("#")
    if len(s) != 6:
        raise ValueError(f"expected #RRGGBB, got {hex_str!r}")
    return (int(s[0:2], 16), int(s[2:4], 16), int(s[4:6], 16))


def hex_to_rgba(hex_str: str, alpha: int = 255) -> tuple[int, int, int, int]:
    """Convert ``#RRGGBB`` to an (r, g, b, a) tuple with ``alpha`` (0–255)."""
    r, g, b = hex_to_rgb(hex_str)
    return (r, g, b, alpha)


def rgb_to_hex(r: int, g: int, b: int) -> str:
    """Convert an (r, g, b) tuple to ``#RRGGBB``."""
    return f"#{r:02X}{g:02X}{b:02X}"
