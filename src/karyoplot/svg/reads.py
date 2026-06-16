"""Per-read feature rasterization primitives.

Two strategies for converting a list of bp-resolution colored features
into pixel-resolution SVG rectangles:

- :func:`smooth_features_to_pixels` — windowed majority-vote downsampling.
  Each pixel is whichever color has the most bp coverage in its window;
  contiguous same-color pixels are run-length encoded into single rects.
  Optional ``oversample`` factor lets sub-pixel features survive the vote
  by rasterizing internally at higher resolution.

- :func:`features_to_pixels_direct` — direct scaling with min-width
  enforcement. Every feature transition is preserved; small features get
  at least ``min_width`` pixels by absorbing space proportionally from
  their neighbors.

The :func:`rasterize_features` dispatcher picks one based on
``feature_mode``.

These functions were ported from inline copies in
``KaryoScope_cluster_plot.py`` and ``KaryoScope_plot_reads.py``; the
implementations are functionally identical (only docstrings differed),
so the move is a pure deduplication.
"""

from __future__ import annotations


def smooth_features_to_pixels(colored_features, bar_length, ratio, oversample: int = 1):
    """Downsample bp-level features to pixel-level via windowed majority vote.

    Each pixel represents a window of ~1/ratio base pairs. For each window,
    the color with the most bp coverage wins. Contiguous same-color pixels
    are run-length encoded into single rectangles.

    When ``oversample > 1``, rasterization happens at oversamplex resolution
    internally, then coordinates are divided by oversample before output.
    This lets features smaller than 1/ratio bp survive the majority vote
    and appear as fractional-pixel SVG rects.

    Args:
        colored_features: list of ``(bp_start, bp_stop, color, fill_opacity)``;
            coordinates are relative to the same origin as ``bar_length``.
        bar_length: total number of pixels for this read's bar.
        ratio: pixels per base pair.
        oversample: internal oversampling factor (default 1).

    Returns:
        list of ``{scaled_start, scaled_stop, color, fill_opacity}`` dicts,
        one per contiguous same-color pixel run.
    """
    if not colored_features or bar_length <= 0:
        return []

    effective_ratio = ratio * oversample
    effective_bar_length = bar_length * oversample

    sorted_feats = sorted(colored_features)
    n_feats = len(sorted_feats)
    feat_idx = 0  # monotonically advancing pointer

    result = []
    current_color = None
    current_opacity = 1.0
    run_start = 0

    for px in range(effective_bar_length):
        # bp window for this sub-pixel
        win_start = px / effective_ratio
        win_end = (px + 1) / effective_ratio

        # Advance pointer past features that end before this window
        while feat_idx < n_feats and sorted_feats[feat_idx][1] <= win_start:
            feat_idx += 1

        # Tally bp coverage per color within this sub-pixel's window
        color_coverage = {}
        color_opacity = {}
        for i in range(feat_idx, n_feats):
            f_start, f_stop, f_color, f_opacity = sorted_feats[i][:4]
            if f_start >= win_end:
                break
            overlap = min(f_stop, win_end) - max(f_start, win_start)
            if overlap > 0:
                color_coverage[f_color] = color_coverage.get(f_color, 0) + overlap
                color_opacity[f_color] = f_opacity

        # Plurality winner
        if color_coverage:
            px_color = max(color_coverage, key=color_coverage.get)
            px_opacity = color_opacity[px_color]
        else:
            px_color = None
            px_opacity = 1.0

        # Run-length encoding
        if px_color != current_color:
            if current_color is not None:
                result.append(
                    {
                        "scaled_start": run_start / oversample,
                        "scaled_stop": px / oversample,
                        "color": current_color,
                        "fill_opacity": current_opacity,
                    }
                )
            current_color = px_color
            current_opacity = px_opacity
            run_start = px

    # Flush last run
    if current_color is not None:
        result.append(
            {
                "scaled_start": run_start / oversample,
                "scaled_stop": bar_length,
                "color": current_color,
                "fill_opacity": current_opacity,
            }
        )

    return result


def features_to_pixels_direct(colored_features, bar_length, ratio, min_width: float = 0.5):
    """Direct-scale bp features to pixel coordinates, preserving every transition.

    Uses contiguous redistribution so that small interspersed features are
    guaranteed at least ``min_width`` pixels of visibility. Features are
    placed end-to-end (no overlaps, no gaps) and large features absorb the
    cost proportionally when the total exceeds ``bar_length``.

    A 5th tuple element on a feature is interpreted as a ``skip_min`` flag —
    those features bypass the ``min_width`` floor (used to draw very thin
    background fills without inflating them).

    Args:
        colored_features: list of ``(bp_start, bp_stop, color, fill_opacity)``
            (optionally a 5th ``skip_min`` flag).
        bar_length: total pixel length for the bar.
        ratio: pixels per base pair.
        min_width: minimum pixel width per feature (default 0.5).

    Returns:
        list of ``{scaled_start, scaled_stop, color, fill_opacity}`` dicts,
        one per contiguous same-color run.
    """
    if not colored_features or bar_length <= 0:
        return []

    sorted_feats = sorted(colored_features, key=lambda f: (f[0], f[1]))

    # Step 1: Scale to pixels, enforce min_width (respecting per-feature skip flag)
    segments = []
    for feat in sorted_feats:
        bp_start, bp_stop, color, opacity = feat[:4]
        skip_min = feat[4] if len(feat) > 4 else False
        effective_min = 0 if skip_min else min_width
        natural_width = (bp_stop - bp_start) * ratio
        width = max(natural_width, effective_min)
        segments.append((width, natural_width, color, opacity, effective_min))

    # Step 1.5: If min-width floors alone exceed bar_length, fall back to
    # natural widths so large features aren't squeezed out by many tiny ones.
    floor_total = sum(em for _, _, _, _, em in segments)
    if floor_total > bar_length:
        segments = [(nw, nw, c, o, 0) for _, nw, c, o, _ in segments]

    # Step 2: If total exceeds bar_length, shrink proportionally above each
    # feature's floor.
    total = sum(w for w, _, _, _, _ in segments)
    if total > bar_length:
        excess = total - bar_length
        shrinkable = sum(max(0, w - em) for w, _, _, _, em in segments)
        if shrinkable > 0:
            factor = max(0, 1 - excess / shrinkable)
            segments = [
                (em + (w - em) * factor if w > em else w, nw, c, o, em)
                for w, nw, c, o, em in segments
            ]

    # Step 3: Place contiguously
    scaled = []
    pos = 0.0
    for width, _, color, opacity, _ in segments:
        end = min(pos + width, bar_length)
        if end > pos:
            scaled.append((pos, end, color, opacity))
        pos = end

    if not scaled:
        return []

    # Step 4: Run-length encode adjacent same-color features
    result = []
    run_start, run_stop, run_color, run_opacity = scaled[0]

    for px_start, px_stop, color, opacity in scaled[1:]:
        if color == run_color and opacity == run_opacity and abs(px_start - run_stop) < 0.01:
            run_stop = px_stop
        else:
            result.append(
                {
                    "scaled_start": run_start,
                    "scaled_stop": run_stop,
                    "color": run_color,
                    "fill_opacity": run_opacity,
                }
            )
            run_start, run_stop, run_color, run_opacity = px_start, px_stop, color, opacity

    # Flush last run
    result.append(
        {
            "scaled_start": run_start,
            "scaled_stop": run_stop,
            "color": run_color,
            "fill_opacity": run_opacity,
        }
    )

    return result


def rasterize_features(
    colored_features,
    bar_length,
    ratio,
    feature_mode: str = "transition",
    oversample: int = 1,
    min_feature_width: float = 0.5,
):
    """Dispatch feature rasterization based on ``feature_mode``.

    Args:
        colored_features: list of ``(bp_start, bp_stop, color, fill_opacity)``.
        bar_length: total pixel length for the bar.
        ratio: pixels per base pair.
        feature_mode: ``"transition"`` for :func:`features_to_pixels_direct`,
            ``"raw"`` returns ``None`` (sentinel for legacy bypass paths in
            ``KaryoScope_plot_reads.py``), any other value falls back to
            :func:`smooth_features_to_pixels`.
        oversample: oversampling factor (smooth mode only).
        min_feature_width: minimum pixel width (transition mode only).

    Returns:
        list of ``{scaled_start, scaled_stop, color, fill_opacity}`` dicts,
        or ``None`` for ``feature_mode="raw"``.
    """
    if feature_mode == "raw":
        return None
    if feature_mode == "transition":
        return features_to_pixels_direct(
            colored_features, bar_length, ratio, min_width=min_feature_width
        )
    return smooth_features_to_pixels(colored_features, bar_length, ratio, oversample=oversample)
