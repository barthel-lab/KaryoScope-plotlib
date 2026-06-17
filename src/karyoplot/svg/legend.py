"""SVG legend builders.

Consolidates three legend-construction patterns previously scattered
across KaryoScope scripts:

1. **Hexamer legend** — fixed 5-row legend for telomeric motifs
   (from ``karyoscope_utils.drawing``).
2. **Multi-track grouped legend** — drawn alongside a plot, organised
   by track type with section headers (column or vertical layout).
3. **Standalone legend drawing** — a full-page legend from a colors
   file with auto-layout, merging, grouping (from
   ``KaryoScope_draw_legend.py``).

All builders default to the dark theme (black background, white text,
``sans-serif`` font) matching ``fiberseq_all.cluster_plot_black.svg``.
"""

from __future__ import annotations

import math
from collections import OrderedDict

import drawsvg as draw

from ..core.fonts import DEFAULT_FONT_FAMILY
from ..core.theme import DEFAULT_THEME, Theme

# --------------------------------------------------------------------
# Hexamer legend (called from per-read / hexamer track plots)
# --------------------------------------------------------------------

HEXAMER_LEGEND_ITEMS: list[tuple[str, str]] = [
    ("TTAGGG", "#F07167"),  # Coral
    ("CCCTAA", "#60A5FA"),  # Blue
    ("TCAGGG/CCCTGA", "#40D392"),  # Green
    ("TGAGGG/CCCTCA", "#C4A9E8"),  # Lavender
    ("TTGGGG/CCCCAA", "#FBBF24"),  # Yellow
]


def draw_hexamer_legend(
    d,
    x_pos: float,
    y_pos: float,
    text_color: str,
    *,
    vertical: bool = True,
    font_family: str = DEFAULT_FONT_FAMILY,
) -> float:
    """Draw a small legend describing the canonical telomeric hexamers.

    Args:
        d: drawsvg Drawing to append to.
        x_pos: X position of the legend.
        y_pos: Y position of the legend top.
        text_color: Text color.
        vertical: ``True`` (default) for a stacked vertical layout,
            ``False`` for a single-row horizontal layout.
        font_family: Font family for labels.

    Returns:
        Final Y position after the last legend row (only meaningful
        for ``vertical=True``; same as ``y_pos`` otherwise).
    """
    if vertical:
        return _draw_hexamer_legend_vertical(d, x_pos, y_pos, text_color, font_family)
    _draw_hexamer_legend_horizontal(d, x_pos, y_pos, text_color, font_family)
    return y_pos


def _draw_hexamer_legend_vertical(d, x_pos, y_pos, text_color, font_family):
    row_height = 14
    box_size = 10
    current_y = y_pos

    d.append(
        draw.Text(
            "Hexamers",
            font_size=9,
            x=x_pos,
            y=current_y,
            fill=text_color,
            font_family=font_family,
            font_weight="bold",
        )
    )
    current_y += row_height

    for label, color in HEXAMER_LEGEND_ITEMS:
        d.append(
            draw.Rectangle(
                x_pos + 10,
                current_y - box_size + 2,
                box_size,
                box_size,
                fill=color,
                stroke="none",
            )
        )
        d.append(
            draw.Text(
                label,
                font_size=9,
                x=x_pos + 24,
                y=current_y,
                fill=text_color,
                font_family=font_family,
            )
        )
        current_y += row_height
    return current_y


def _draw_hexamer_legend_horizontal(d, x_pos, y_pos, text_color, font_family):
    d.append(
        draw.Text(
            "Direct Sequence Calls:",
            font_size=9,
            x=x_pos,
            y=y_pos,
            fill=text_color,
            font_family=font_family,
            font_weight="bold",
        )
    )
    current_x = x_pos
    y_pos += 15
    for label, color in HEXAMER_LEGEND_ITEMS:
        d.append(
            draw.Rectangle(
                current_x,
                y_pos - 8,
                10,
                10,
                fill=color,
                stroke="none",
            )
        )
        d.append(
            draw.Text(
                label,
                font_size=8,
                x=current_x + 14,
                y=y_pos,
                fill=text_color,
                font_family=font_family,
            )
        )
        current_x += len(label) * 6 + 30


# --------------------------------------------------------------------
# Multi-track grouped legend (drawn alongside a plot)
# --------------------------------------------------------------------


def clean_label(name: str) -> str:
    """Clean a feature name into a legend label (underscores -> spaces)."""
    return name.replace("_", " ")


def draw_grouped_legend(
    d,
    x_pos: float,
    y_pos: float,
    text_color: str,
    used_colors: dict,
    track_labels: dict,
    tracks: list,
    *,
    layout: str = "column",
    column_width: float = 120,
    font_family: str = DEFAULT_FONT_FAMILY,
    sort_key=None,
) -> float:
    """Draw a legend organised by track type with section headers.

    Args:
        d: drawsvg Drawing to append to.
        x_pos: X position for legend start.
        y_pos: Y position for legend top.
        text_color: Text color.
        used_colors: ``{track_type: {feature: color}}``.
        track_labels: ``{track_type: display_label}``.
        tracks: Track types to include, in order.
        layout: ``"column"`` (each track type its own column) or
            ``"vertical"`` (single column, sections stacked).
        column_width: Column width when ``layout="column"``.
        font_family: Font family for labels.
        sort_key: Optional ``feature -> sortable`` callable for ordering features within each
            track. Defaults to alphabetical (``None``). Pass a DB-aware key for KaryoScope-style
            ordering (the renderer stays DB-agnostic — it just receives the callable).

    Returns:
        Final Y position after the legend.
    """
    if layout == "column":
        return _draw_column_legend(
            d,
            x_pos,
            y_pos,
            text_color,
            used_colors,
            track_labels,
            tracks,
            column_width,
            font_family,
            sort_key,
        )
    if layout == "vertical":
        return _draw_vertical_legend(
            d,
            x_pos,
            y_pos,
            text_color,
            used_colors,
            track_labels,
            tracks,
            font_family,
            sort_key,
        )
    raise ValueError(f"unknown layout {layout!r}; use 'column' or 'vertical'")


def _sorted_items(type_colors: dict, sort_key):
    """Feature/color items ordered by ``sort_key`` (on the feature name), else alphabetically."""
    if sort_key is None:
        return sorted(type_colors.items())
    return sorted(type_colors.items(), key=lambda kv: sort_key(kv[0]))


def _draw_column_legend(
    d,
    x_pos,
    y_pos,
    text_color,
    used_colors,
    track_labels,
    tracks,
    column_width,
    font_family,
    sort_key=None,
):
    row_height = 14
    box_size = 10
    current_x = x_pos
    max_y = y_pos

    for annot_type in tracks:
        type_colors = used_colors.get(annot_type)
        if not type_colors:
            continue

        current_y = y_pos
        d.append(
            draw.Text(
                track_labels.get(annot_type, annot_type),
                font_size=9,
                x=current_x,
                y=current_y,
                fill=text_color,
                font_family=font_family,
                font_weight="bold",
            )
        )
        current_y += row_height

        for feature, color in _sorted_items(type_colors, sort_key):
            d.append(
                draw.Rectangle(
                    current_x + 10,
                    current_y - box_size + 2,
                    box_size,
                    box_size,
                    fill=color,
                    stroke="none",
                )
            )
            d.append(
                draw.Text(
                    clean_label(feature),
                    font_size=9,
                    x=current_x + 24,
                    y=current_y,
                    fill=text_color,
                    font_family=font_family,
                )
            )
            current_y += row_height

        max_y = max(max_y, current_y)
        current_x += column_width

    return max_y


def _draw_vertical_legend(
    d, x_pos, y_pos, text_color, used_colors, track_labels, tracks, font_family, sort_key=None
):
    current_y = y_pos
    row_height = 14
    box_size = 10

    for annot_type in tracks:
        type_colors = used_colors.get(annot_type)
        if not type_colors:
            continue

        d.append(
            draw.Text(
                track_labels.get(annot_type, annot_type) + ":",
                font_size=8,
                x=x_pos,
                y=current_y,
                fill=text_color,
                font_family=font_family,
                font_weight="bold",
            )
        )
        current_y += row_height

        for feature, color in _sorted_items(type_colors, sort_key):
            d.append(
                draw.Rectangle(
                    x_pos + 10,
                    current_y - box_size + 2,
                    box_size,
                    box_size,
                    fill=color,
                    stroke="none",
                )
            )
            d.append(
                draw.Text(
                    clean_label(feature),
                    font_size=7,
                    x=x_pos + 24,
                    y=current_y,
                    fill=text_color,
                    font_family=font_family,
                )
            )
            current_y += row_height
        current_y += 4  # extra spacing between sections

    return current_y


# --------------------------------------------------------------------
# Standalone legend drawing (replaces KaryoScope_draw_legend.py main)
# --------------------------------------------------------------------


def _estimate_text_width(text: str, font_size: int) -> float:
    return len(text) * font_size * 0.6


def _calculate_layout(n_items: int, rows: int | None, cols: int | None) -> tuple[int, int]:
    if n_items == 0:
        return (0, 0)
    if rows and cols:
        return (rows, cols)
    if cols:
        return (math.ceil(n_items / cols), cols)
    if rows:
        return (rows, math.ceil(n_items / rows))
    cols = max(1, math.ceil(math.sqrt(n_items * 1.5)))
    rows = math.ceil(n_items / cols)
    return (rows, cols)


def merge_by_color(
    items: list[tuple[str, str]],
    label_overrides: dict[str, str] | None = None,
) -> list[tuple[str, str]]:
    """Collapse ``(feature, color)`` items sharing the same color into one entry.

    The kept label is the override (if provided) or the shortest cleaned label.
    """
    overrides = label_overrides or {}
    color_groups: OrderedDict[str, list[str]] = OrderedDict()
    for feature, color in items:
        color_groups.setdefault(color.upper(), []).append(feature)

    merged: list[tuple[str, str]] = []
    for color, features in color_groups.items():
        label = next((overrides[f] for f in features if f in overrides), None)
        if label is None:
            cleaned = sorted(((clean_label(f), f) for f in features), key=lambda x: len(x[0]))
            label = cleaned[0][0]
        merged.append((label, color))
    return merged


def featureset_legend_items(
    colors_by_set: dict[str, dict[str, str]],
    *,
    feature_sets: list[str] | None = None,
    set_labels: dict[str, str] | None = None,
    include: set[str] | None = None,
    exclude: set[str] | None = None,
    clean_labels: bool = True,
    sort_key=None,
) -> list[tuple[str, str, bool]]:
    """Flatten a ``{feature_set: {feature: color}}`` DB palette into legend rows.

    Produces the ``(label, color, is_header)`` items consumed by
    :func:`make_legend_drawing`: one bold header row per feature set (the set's
    display label, empty color, ``is_header=True``) followed by its feature rows.
    This is the DB-driven replacement for the legacy ``KaryoScope_draw_legend.py``
    helpers (``load_colors_file`` / ``parse_groups`` / ``group_items``): grouping
    comes from the ``feature_set`` column of ``colors.tsv`` rather than a manual
    ``Header:feat1,feat2`` string. Kept DB-agnostic — it takes plain dicts (e.g.
    from ``karyoscope.core.io.colors.parse_colors``), not engine objects.

    Feature rows preserve the order of ``colors_by_set`` (i.e. the curated
    ``colors.tsv`` row order). Ordering logic is intentionally **not** duplicated
    here from the engine's ``karyoscope.core.karyotype._legend_sort_key``; if
    byte-identical hierarchy-aware ordering is ever needed, sort the per-set dicts
    upstream (and consider promoting that engine helper to public API).

    Args:
        colors_by_set: Nested ``{feature_set: {feature: hex}}`` mapping.
        feature_sets: Feature sets to include, in this order. Sets absent from
            ``colors_by_set`` are skipped. Defaults to all sets, in dict order.
        set_labels: Optional ``{feature_set: header_label}`` overrides; a set with
            no override uses its own name as the header.
        include: If given, keep only these feature names.
        exclude: If given, drop these feature names (applied after ``include``).
        clean_labels: If ``True`` (default), feature labels are passed through
            :func:`clean_label` (underscores -> spaces); if ``False``, shown verbatim.
        sort_key: Optional ``feature -> sortable`` callable to order features within each set;
            defaults to the ``colors_by_set`` order. (DB-agnostic — just a callable.)

    Returns:
        Flat list of ``(label, color, is_header)`` rows. Feature sets that end up
        empty after filtering contribute no header.
    """
    order = feature_sets if feature_sets is not None else list(colors_by_set)
    labels = set_labels or {}
    items: list[tuple[str, str, bool]] = []
    for fs in order:
        fs_colors = colors_by_set.get(fs)
        if not fs_colors:
            continue
        feats = list(fs_colors.items())
        if sort_key is not None:
            feats.sort(key=lambda fc: sort_key(fc[0]))
        rows: list[tuple[str, str, bool]] = []
        for feature, color in feats:
            if include is not None and feature not in include:
                continue
            if exclude is not None and feature in exclude:
                continue
            label = clean_label(feature) if clean_labels else feature
            rows.append((label, color, False))
        if rows:
            items.append((labels.get(fs, fs), "", True))
            items.extend(rows)
    return items


def make_legend_drawing(
    items: list[tuple[str, str, bool]],
    *,
    theme: Theme | None = None,
    rows: int | None = None,
    cols: int | None = None,
    swatch_size: int = 8,
    font_size: int = 12,
    row_spacing: int = 14,
    col_spacing: int | None = None,
    padding: int = 15,
    stroke_color: str | None = None,
    font_family: str | None = None,
) -> draw.Drawing:
    """Build a standalone legend Drawing from ``(label, color, is_header)`` items.

    Args:
        items: Sequence of ``(label, color, is_header)``. Header rows
            (``is_header=True``) start a new column with a bold label.
        theme: Visual theme; defaults to :data:`karyoplot.core.theme.DEFAULT_THEME`
            (dark / black background).
        rows: Desired row count (auto if both ``rows`` and ``cols`` are ``None``).
        cols: Desired column count.
        swatch_size: Size of color swatches in px.
        font_size: Label font size in px.
        row_spacing: Vertical spacing between rows.
        col_spacing: Horizontal spacing between columns (default 20).
        padding: Edge padding in px.
        stroke_color: Swatch stroke color (defaults to theme line color).
        font_family: Font family override (defaults to theme font_family).

    Returns:
        ``drawsvg.Drawing`` ready to be saved with ``.save_svg()``.
    """
    t = theme or DEFAULT_THEME
    bg = t.background
    text_color = t.text
    stroke_color = stroke_color or t.line
    font_family = font_family or t.font_family

    has_headers = any(is_header for _, _, is_header in items)
    regular_items: list[tuple[str, str, bool]] = []
    header_at: dict[int, str] = {}
    for label, color, is_header in items:
        if is_header:
            header_at[len(regular_items)] = label
        else:
            regular_items.append((label, color, False))

    rows, cols = _calculate_layout(len(regular_items), rows, cols)
    if cols == 0:
        return draw.Drawing(padding * 2, padding * 2, id_prefix="legend")

    # Distribute regular items into columns (top-to-bottom, then next column)
    columns: list[list[tuple[str, str, bool]]] = [[] for _ in range(cols)]
    col_idx = 0
    row_idx = 0
    col_headers: dict[int, str] = {}
    for i, item in enumerate(regular_items):
        if col_idx >= cols:
            break
        if i in header_at:
            if row_idx > 0:
                col_idx += 1
                row_idx = 0
                if col_idx >= cols:
                    break
            col_headers[col_idx] = header_at[i]
        columns[col_idx].append(item)
        row_idx += 1
        if row_idx >= rows:
            row_idx = 0
            col_idx += 1

    swatch_gap = swatch_size + 3
    col_widths: list[float] = []
    for ci, col in enumerate(columns):
        if not col:
            col_widths.append(0)
            continue
        labels = [label for label, _, _ in col]
        if ci in col_headers:
            labels.append(col_headers[ci])
        col_widths.append(
            swatch_gap + max(_estimate_text_width(label, font_size) for label in labels)
        )

    if col_spacing is None:
        col_spacing = 20

    total_width = round(
        padding * 2 + sum(col_widths) + col_spacing * max(0, len(col_widths) - 1), 1
    )
    max_rows_in_col = max((len(c) for c in columns), default=0)
    header_offset = row_spacing if has_headers else 0
    total_height = round(padding * 2 + max_rows_in_col * row_spacing + header_offset, 1)

    d = draw.Drawing(total_width, total_height, id_prefix="legend")
    d.append(draw.Rectangle(0, 0, total_width, total_height, fill=bg))

    x_offset = padding
    for ci, col in enumerate(columns):
        if ci in col_headers:
            d.append(
                draw.Text(
                    col_headers[ci],
                    font_size,
                    x_offset,
                    padding + swatch_size - 1,
                    fill=text_color,
                    font_family=font_family,
                    font_weight="bold",
                )
            )
        y_offset = padding + header_offset
        for label, color, _ in col:
            d.append(
                draw.Rectangle(
                    x_offset,
                    y_offset,
                    swatch_size,
                    swatch_size,
                    fill=color,
                    stroke=stroke_color,
                    stroke_width=0.5,
                )
            )
            d.append(
                draw.Text(
                    label,
                    font_size,
                    x_offset + swatch_gap,
                    y_offset + swatch_size - 1,
                    fill=text_color,
                    font_family=font_family,
                )
            )
            y_offset += row_spacing
        x_offset += col_widths[ci] + col_spacing

    return d
