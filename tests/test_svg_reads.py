"""Unit tests for karyoplot.svg.reads (rasterization primitives)."""

from karyoplot.svg.reads import (
    features_to_pixels_direct,
    rasterize_features,
    smooth_features_to_pixels,
)

# ----- smooth_features_to_pixels -----


def test_smooth_empty_returns_empty():
    assert smooth_features_to_pixels([], 100, 0.01) == []
    assert smooth_features_to_pixels([(0, 100, "#FF0000", 1.0)], 0, 0.01) == []


def test_smooth_single_feature_full_bar():
    feats = [(0, 1000, "#FF0000", 1.0)]
    out = smooth_features_to_pixels(feats, 10, 0.01)
    assert len(out) == 1
    assert out[0]["color"] == "#FF0000"
    assert out[0]["scaled_start"] == 0
    assert out[0]["scaled_stop"] == 10


def test_smooth_run_length_encodes_adjacent_same_color():
    feats = [(0, 500, "#FF0000", 1.0), (500, 1000, "#FF0000", 1.0)]
    out = smooth_features_to_pixels(feats, 10, 0.01)
    assert len(out) == 1  # collapsed into one run
    assert out[0]["scaled_stop"] == 10


def test_smooth_two_color_split():
    feats = [(0, 500, "#FF0000", 1.0), (500, 1000, "#00FF00", 1.0)]
    out = smooth_features_to_pixels(feats, 10, 0.01)
    colors = [r["color"] for r in out]
    assert colors == ["#FF0000", "#00FF00"]


def test_smooth_oversample_lets_subpixel_features_survive():
    # 10bp red feature inside a 1000bp bar @ ratio=0.01 (10px) — 0.1px naturally.
    # In a 100-bp window (one full pixel), red covers 10/100 vs green 90/100 → green wins.
    feats = [(0, 10, "#FF0000", 1.0), (10, 1000, "#00FF00", 1.0)]
    no_os = smooth_features_to_pixels(feats, 10, 0.01, oversample=1)
    with_os = smooth_features_to_pixels(feats, 10, 0.01, oversample=20)
    no_os_colors = {r["color"] for r in no_os}
    with_os_colors = {r["color"] for r in with_os}
    assert "#FF0000" not in no_os_colors  # outvoted at native resolution
    assert "#FF0000" in with_os_colors  # survives with oversampling


# ----- features_to_pixels_direct -----


def test_direct_empty_returns_empty():
    assert features_to_pixels_direct([], 100, 0.01) == []
    assert features_to_pixels_direct([(0, 100, "#FF0000", 1.0)], 0, 0.01) == []


def test_direct_two_color_simple():
    feats = [(0, 500, "#FF0000", 1.0), (500, 1000, "#00FF00", 1.0)]
    out = features_to_pixels_direct(feats, 10, 0.01)
    colors = [r["color"] for r in out]
    assert colors == ["#FF0000", "#00FF00"]


def test_direct_min_width_floor_for_tiny_features():
    # Feature is 0.1px naturally; min_width=0.5 should expand it
    feats = [(0, 10, "#FF0000", 1.0), (10, 1000, "#00FF00", 1.0)]
    out = features_to_pixels_direct(feats, 10, 0.01, min_width=0.5)
    red = next(r for r in out if r["color"] == "#FF0000")
    assert (red["scaled_stop"] - red["scaled_start"]) >= 0.5


def test_direct_skip_min_flag_suppresses_floor():
    # 5th element True = skip_min — feature stays at natural width even if
    # smaller than min_width.
    feats = [
        (0, 10, "#FF0000", 1.0, True),  # natural 0.1px, no floor
        (10, 1000, "#00FF00", 1.0, False),
    ]
    out = features_to_pixels_direct(feats, 10, 0.01, min_width=0.5)
    red = next(r for r in out if r["color"] == "#FF0000")
    width = red["scaled_stop"] - red["scaled_start"]
    assert width < 0.2  # close to natural 0.1, not floored to 0.5


def test_direct_run_length_encoding():
    feats = [(0, 500, "#FF0000", 1.0), (500, 1000, "#FF0000", 1.0)]
    out = features_to_pixels_direct(feats, 10, 0.01)
    assert len(out) == 1


def test_direct_total_does_not_exceed_bar_length():
    feats = [(i * 100, (i + 1) * 100, f"#{i:06X}", 1.0) for i in range(10)]
    out = features_to_pixels_direct(feats, 5, 0.01, min_width=1.0)
    last_stop = max(r["scaled_stop"] for r in out)
    assert last_stop <= 5 + 1e-9


# ----- rasterize_features dispatcher -----


def test_rasterize_dispatcher_transition_mode():
    feats = [(0, 1000, "#FF0000", 1.0)]
    out_direct = features_to_pixels_direct(feats, 10, 0.01)
    out_dispatcher = rasterize_features(feats, 10, 0.01, feature_mode="transition")
    assert out_direct == out_dispatcher


def test_rasterize_dispatcher_smooth_mode():
    feats = [(0, 1000, "#FF0000", 1.0)]
    out_smooth = smooth_features_to_pixels(feats, 10, 0.01)
    out_dispatcher = rasterize_features(feats, 10, 0.01, feature_mode="smooth")
    assert out_smooth == out_dispatcher


def test_rasterize_dispatcher_raw_mode_returns_none():
    feats = [(0, 1000, "#FF0000", 1.0)]
    assert rasterize_features(feats, 10, 0.01, feature_mode="raw") is None
