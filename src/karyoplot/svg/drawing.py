"""drawsvg primitive helpers: annotation tracks, hexamer tracks, axes.

Ported from ``karyoscope_utils.drawing`` with two changes:

1. ``font_family`` is now an explicit keyword argument that defaults to
   the generic ``sans-serif`` family (was hardcoded ``'Basic Sans'``).
   Pass ``font_family="Basic Sans"`` (and call
   :func:`karyoplot.core.fonts.register_fonts` first) to opt back in.
2. ``get_color`` / ``color_maps`` are imported from :mod:`karyoplot.core.colors`
   so the same palette dict shape works without the legacy
   ``karyoscope_utils.colors`` import path.

Function signatures are preserved so legacy CHM13 scripts can keep
working through a thin re-export shim.
"""

from __future__ import annotations

import drawsvg as draw

from ..core.colors import DEFAULT_COLOR
from ..core.fonts import DEFAULT_FONT_FAMILY


def _color_lookup(annotation: str, annot_type: str, color_maps: dict) -> str:
    """Look up a color in either a flat or nested palette dict.

    Supports both shapes:
      - flat: ``{feature: hex}`` (when ``annot_type`` is irrelevant)
      - nested: ``{annot_type: {feature: hex}}`` (legacy KaryoScope shape)
    """
    if annot_type and annot_type in color_maps and isinstance(color_maps[annot_type], dict):
        return color_maps[annot_type].get(annotation, DEFAULT_COLOR)
    return color_maps.get(annotation, DEFAULT_COLOR)


def draw_annotation_track(
    d,
    regions,
    y_pos,
    track_height,
    x_scale,
    x_offset,
    annot_type,
    label,
    text_color,
    left_margin,
    color_maps,
    used_colors,
    plot_width,
    view_start,
    view_end,
    *,
    font_family: str = DEFAULT_FONT_FAMILY,
):
    """Draw a single annotation track (rectangles for each region).

    Args:
        d: drawsvg Drawing object to append to.
        regions: Iterable of ``(start, end, annotation)`` tuples.
        y_pos: Y position for the track.
        track_height: Track height in pixels.
        x_scale: Pixels per bp.
        x_offset: X offset in pixels.
        annot_type: Track-type key (e.g. ``"chromosome"``); used for the
            nested palette lookup when ``color_maps`` is nested.
        label: Track label (kept for API compatibility; not drawn here).
        text_color: Text color (kept for API compatibility).
        left_margin: Left margin in pixels (start of plot area).
        color_maps: Either ``{feature: hex}`` or ``{type: {feature: hex}}``.
        used_colors: Mutable dict tracking ``{type: {feature: color}}``;
            updated in place so a later legend call can reuse it.
        plot_width: Width of the plot area in pixels.
        view_start: View start coordinate (bp).
        view_end: View end coordinate (bp).
        font_family: Font family for any text (defaults to ``sans-serif``).
    """
    plot_x_min = left_margin
    plot_x_max = left_margin + plot_width

    for start, end, annotation in regions:
        clipped_start = max(start, view_start)
        clipped_end = min(end, view_end)
        if clipped_start >= clipped_end:
            continue

        x = max(x_offset + clipped_start * x_scale, plot_x_min)
        x_end = min(x_offset + clipped_end * x_scale, plot_x_max)
        width = x_end - x
        if width <= 0:
            continue

        color = _color_lookup(annotation, annot_type, color_maps)

        if annot_type not in used_colors:
            used_colors[annot_type] = {}
        used_colors[annot_type].setdefault(annotation, color)

        d.append(
            draw.Rectangle(
                x,
                y_pos,
                max(width, 1),
                track_height,
                fill=color,
                stroke="none",
            )
        )


def draw_hexamer_track(
    d,
    hits,
    y_pos,
    track_height,
    x_scale,
    x_offset,
    label,
    text_color,
    left_margin,
    plot_width,
    view_start,
    view_end,
    *,
    font_family: str = DEFAULT_FONT_FAMILY,
):
    """Draw direct sequence hexamer hits as colored tick marks.

    ``hits`` is an iterable of dicts with ``position`` (int) and
    ``color`` (hex) keys, matching the output of
    :func:`karyoplot.core.io.fetch_fasta_region` based callers.
    """
    plot_x_min = left_margin
    plot_x_max = left_margin + plot_width

    d.append(
        draw.Line(
            plot_x_min,
            y_pos + track_height / 2,
            plot_x_max,
            y_pos + track_height / 2,
            stroke=text_color,
            stroke_width=0.5,
            stroke_opacity=0.3,
        )
    )

    for hit in hits:
        pos = hit["position"]
        if pos < view_start or pos > view_end:
            continue
        x = x_offset + pos * x_scale
        if x < plot_x_min or x > plot_x_max:
            continue
        d.append(
            draw.Line(
                x,
                y_pos + 2,
                x,
                y_pos + track_height - 2,
                stroke=hit["color"],
                stroke_width=1.5,
            )
        )


def _tick_spacing(coord_range: int) -> int:
    """Pick a sensible tick spacing for a given coordinate range."""
    if coord_range <= 5_000:
        return 1_000
    if coord_range <= 10_000:
        return 2_000
    if coord_range <= 20_000:
        return 5_000
    if coord_range <= 60_000:
        return 10_000
    return 20_000


def draw_axis(
    d,
    view_start,
    view_end,
    y_pos,
    x_scale,
    x_offset,
    text_color,
    left_margin,
    plot_width,
    title,
    *,
    font_family: str = DEFAULT_FONT_FAMILY,
):
    """Draw a horizontal axis with tick marks and a centered title."""
    plot_x_min = left_margin
    plot_x_max = left_margin + plot_width

    d.append(
        draw.Text(
            title,
            font_size=11,
            x=left_margin + plot_width / 2,
            y=y_pos - 5,
            fill=text_color,
            font_family=font_family,
            text_anchor="middle",
            font_weight="bold",
        )
    )

    d.append(
        draw.Line(
            plot_x_min,
            y_pos,
            plot_x_max,
            y_pos,
            stroke=text_color,
            stroke_width=1,
        )
    )

    spacing = _tick_spacing(view_end - view_start)
    first_tick = ((view_start // spacing) + 1) * spacing
    for tick_pos in range(first_tick, view_end + 1, spacing):
        x = x_offset + tick_pos * x_scale
        if x < plot_x_min or x > plot_x_max:
            continue
        d.append(draw.Line(x, y_pos, x, y_pos + 5, stroke=text_color, stroke_width=1))
        label_text = f"{tick_pos / 1000:.0f}kb" if spacing >= 1000 else f"{tick_pos}"
        d.append(
            draw.Text(
                label_text,
                font_size=7,
                x=x,
                y=y_pos + 14,
                fill=text_color,
                font_family=font_family,
                text_anchor="middle",
            )
        )


def draw_centered_track_labels(
    d,
    y_positions,
    center_x,
    text_color,
    track_height: int = 12,
    *,
    font_family: str = DEFAULT_FONT_FAMILY,
):
    """Draw track labels centered between two panels.

    Args:
        d: drawsvg Drawing.
        y_positions: ``{track_name: y_pos}`` mapping.
        center_x: X coordinate for the centered labels.
        text_color: Label color.
        track_height: Track height for vertical centering.
    """
    font_size = 9
    for track_name, y_pos in y_positions.items():
        y_centered = y_pos + track_height / 2 + font_size / 3
        d.append(
            draw.Text(
                track_name,
                font_size=font_size,
                x=center_x,
                y=y_centered,
                fill=text_color,
                font_family=font_family,
                text_anchor="middle",
            )
        )
