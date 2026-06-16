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
from collections.abc import Iterable
from pathlib import Path

DEFAULT_COLOR = "#CCCCCC"


# matplotlib's tab10 / tab20 qualitative palettes, baked in as hex tuples
# so callers can avoid a matplotlib import for simple categorical coloring.
TAB10: tuple[str, ...] = (
    "#1f77b4",
    "#ff7f0e",
    "#2ca02c",
    "#d62728",
    "#9467bd",
    "#8c564b",
    "#e377c2",
    "#7f7f7f",
    "#bcbd22",
    "#17becf",
)
TAB20: tuple[str, ...] = (
    "#1f77b4",
    "#aec7e8",
    "#ff7f0e",
    "#ffbb78",
    "#2ca02c",
    "#98df8a",
    "#d62728",
    "#ff9896",
    "#9467bd",
    "#c5b0d5",
    "#8c564b",
    "#c49c94",
    "#e377c2",
    "#f7b6d2",
    "#7f7f7f",
    "#c7c7c7",
    "#bcbd22",
    "#dbdb8d",
    "#17becf",
    "#9edae5",
)


def qualitative_palette(n: int, palette: tuple[str, ...] = TAB20) -> list[str]:
    """Return ``n`` colors cycled from a qualitative palette (default :data:`TAB20`)."""
    if not palette:
        raise ValueError("palette must be non-empty")
    return [palette[i % len(palette)] for i in range(n)]


# ----------------------------------------------------------------------------
# KaryoScope featureset palette loader
# ----------------------------------------------------------------------------

# A "section" is a tuple ``(header_or_None, [feature_names])`` for legend grouping.
# Sections are introduced by ``# Header`` comment lines in the colors file.
PaletteSection = tuple[str | None, list[str]]


def load_palette_file(
    file_path: str | os.PathLike,
    *,
    parse_sections: bool = False,
    suffix_both_ways: bool = False,
    initial: dict | None = None,
    value_format: str = "hex",
    track_order: bool = False,
):
    """Load a single ``{database}.{featureset}.colors.txt`` file.

    Subsumes the per-file parsing logic that was previously duplicated across
    ``KaryoScope_cluster_plot.py``, ``plot_reads.py``, ``telogator_reads_viz.py``,
    ``visualize_translocation_reads.py``, and
    ``KaryoScope_assembly_contig_zoom_plot.py``.

    Args:
        file_path: Path to the TSV (whitespace-separated, two columns:
            ``feature``, ``hex_color``). Lines starting with ``#`` are
            treated as comments; their text after the ``#`` becomes a section
            header when ``parse_sections=True``. The ``feature`` literal
            header line is auto-skipped.
        parse_sections: If ``True``, parse ``# Header`` comment lines as
            section headers and return ``(palette, sections)`` where
            ``sections`` is a list of ``(header_or_None, [features])`` tuples
            for legend grouping. If no sections are found, the entire palette
            is wrapped in a single ``(None, [...])`` section. Default ``False``.
        suffix_both_ways: If ``True``, add bidirectional ``_specific`` mapping —
            ``foo_specific`` and bare ``foo`` both point at the same color.
            If ``False``, only the bare-from-suffix direction is added (matches
            the legacy multi-file loaders). Default ``False``.
        initial: Optional dict to initialize the palette with (for "novel" /
            "unknown" sentinels). Keys may be plain hex strings or
            ``(color, opacity)`` tuples — must match ``value_format``.
        value_format: ``"hex"`` returns bare hex strings (``"#RRGGBB"``);
            ``"tuple"`` returns ``(color, 1.0)`` tuples (legacy multi-file
            shape). Default ``"hex"``.
        track_order: If ``True``, also returns the list of features in file
            order (excluding the ``feature`` header). Default ``False``.

    Returns:
        Depending on flags, one of:

        * ``palette`` — dict of feature → hex (or tuple).
        * ``(palette, sections)`` — when ``parse_sections=True``.
        * ``(palette, order)`` — when ``track_order=True``.
        * ``(palette, sections, order)`` — when both flags are set.

        If the file does not exist, returns an empty palette (or empty plus
        ``initial`` if provided), no sections, no order. No exception raised.
    """
    if value_format not in ("hex", "tuple"):
        raise ValueError(f"value_format must be 'hex' or 'tuple', got {value_format!r}")

    palette: dict = dict(initial) if initial else {}
    sections: list[PaletteSection] = []
    order: list[str] = []

    if not Path(file_path).exists():
        return _palette_return(palette, sections, order, parse_sections, track_order)

    current_header: str | None = None
    current_features: list[str] = []
    has_section_marker = False
    import re as _re

    def _wrap(color: str):
        return (color, 1.0) if value_format == "tuple" else color

    with Path(file_path).open() as f:
        for line in f:
            stripped = line.strip()
            if parse_sections:
                m = _re.match(r"^#\s+(.+)", stripped)
                if m:
                    if current_features:
                        sections.append((current_header, current_features))
                    current_header = m.group(1).strip()
                    current_features = []
                    has_section_marker = True
                    continue
            elif stripped.startswith("#"):
                continue  # plain comment — skip without recording

            parts = stripped.split()
            if len(parts) < 2:
                continue
            if parts[0].lower() == "feature":
                continue

            feature, color = parts[0], parts[1]
            palette[feature] = _wrap(color)
            order.append(feature)
            if parse_sections:
                current_features.append(feature)

            # Reverse mapping: feature_specific → bare feature
            if feature.endswith("_specific"):
                palette[feature[: -len("_specific")]] = _wrap(color)
            # Forward mapping (only when caller asks for both directions)
            if suffix_both_ways and not (
                feature.endswith("_specific") or feature.endswith("_multigroup1")
            ):
                palette[feature + "_specific"] = _wrap(color)

    if parse_sections:
        if current_features:
            sections.append((current_header, current_features))
        if not has_section_marker and palette:
            # No section markers found — wrap everything in a single None-header section
            sections = [(None, list(palette.keys()))]

    return _palette_return(palette, sections, order, parse_sections, track_order)


def _palette_return(palette, sections, order, parse_sections: bool, track_order: bool):
    if parse_sections and track_order:
        return palette, sections, order
    if parse_sections:
        return palette, sections
    if track_order:
        return palette, order
    return palette


def load_featureset_palettes(
    colors_dir: str | os.PathLike,
    database: str,
    featuresets,
    *,
    on_missing: str = "warn",
    value_format: str = "tuple",
    background: str | None = None,
    track_order: bool = False,
):
    """Multi-file wrapper: load one ``{database}.{fs}.colors.txt`` per featureset.

    Subsumes the multi-file loaders in ``KaryoScope_cluster_plot.py``,
    ``visualize_translocation_reads.py``, and
    ``KaryoScope_assembly_contig_zoom_plot.py``.

    Args:
        colors_dir: Directory containing the per-featureset color files.
        database: Database token (e.g. ``"KS_human_CHM13_v2"``).
        featuresets: Iterable of featureset names.
        on_missing: ``"warn"`` (print warning, fall back to defaults if any),
            ``"error"`` (write to stderr and ``sys.exit(1)`` — matches
            cluster_plot's strict mode), ``"silent"`` (empty dict, no output).
            Default ``"warn"``.
        value_format: ``"hex"`` or ``"tuple"``; passed through to
            :func:`load_palette_file`.
        background: If given (``"black"`` or ``"white"``), each featureset
            dict is pre-seeded with ``"novel"`` and ``"unknown"`` defaults
            matching the assembly_contig_zoom convention: ``novel`` matches
            the background (so novel features render invisibly), ``unknown``
            is grey ``#808080``. If ``None``, no defaults are seeded.
            Default ``None``.
        track_order: If ``True``, also returns ``{fs: [features in file order]}``.

    Returns:
        ``{fs: palette}`` or ``({fs: palette}, {fs: order})`` if track_order.
    """
    import sys

    out: dict = {}
    orders: dict = {}

    if background is not None:
        # Legacy assembly_contig_zoom convention: novel matches the background
        # (so unmapped features blend in invisibly).
        novel_color = "#ffffff" if background == "white" else "#000000"
        if value_format == "tuple":
            seed = {"novel": (novel_color, 1.0), "unknown": ("#808080", 1.0)}
        else:
            seed = {"novel": novel_color, "unknown": "#808080"}
    else:
        seed = None

    for fs in featuresets:
        path = Path(colors_dir) / f"{database}.{fs}.colors.txt"
        if not path.exists():
            if on_missing == "error":
                sys.stderr.write(f"Error: Colors file not found: {path}\n")
                sys.exit(1)
            if on_missing == "warn":
                print(f"  Warning: Colors file not found: {path}")
            out[fs] = dict(seed) if seed else {}
            orders[fs] = []
            continue

        result = load_palette_file(
            path,
            initial=seed,
            value_format=value_format,
            track_order=track_order,
        )
        if track_order:
            palette, order = result
            out[fs] = palette
            orders[fs] = order
        else:
            out[fs] = result
            orders[fs] = []

    if track_order:
        return out, orders
    return out


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
    if not Path(filepath).exists():
        return palette
    with Path(filepath).open() as f:
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
        path = Path(colors_dir) / f"{database}.{fs}.colors.txt"
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
    """Convert ``#RRGGBB`` to an (r, g, b, a) tuple with ``alpha`` (0-255)."""
    r, g, b = hex_to_rgb(hex_str)
    return (r, g, b, alpha)


def rgb_to_hex(r: int, g: int, b: int) -> str:
    """Convert an (r, g, b) tuple to ``#RRGGBB``."""
    return f"#{r:02X}{g:02X}{b:02X}"
