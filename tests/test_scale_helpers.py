"""Unit tests for the scale-bar helpers in karyoplot.core.{coords,text}."""

import pytest

from karyoplot.core.coords import DEFAULT_SCALE_OPTIONS, pick_round_scale_bp
from karyoplot.core.text import format_genomic_distance

# ── pick_round_scale_bp ─────────────────────────────────────────────────────


def test_pick_5kb_at_default_ratio():
    # ratio=0.01 px/bp: 5000 bp → 50 px (lower bound of 50-150 window)
    assert pick_round_scale_bp(0.01) == 5000


def test_pick_jumps_to_larger_when_zoomed_out():
    # ratio=0.001 px/bp: 5000 bp → 5 px (too small); 50000 → 50 px ✓
    assert pick_round_scale_bp(0.001) == 50_000


def test_pick_jumps_to_smaller_when_zoomed_in():
    # ratio=0.1 px/bp: smaller options are in the ladder; 500 → 50 px is the first match
    assert pick_round_scale_bp(0.1) == 500


def test_pick_falls_back_when_no_option_fits():
    # ratio=10 px/bp + tight window — nothing fits
    assert (
        pick_round_scale_bp(
            10,
            target_min_px=50,
            target_max_px=150,
            fallback_bp=999,
        )
        == 999
    )


def test_pick_respects_custom_options():
    options = (1, 5, 25)
    assert (
        pick_round_scale_bp(
            20, target_min_px=50, target_max_px=150, options=options, fallback_bp=-1
        )
        == 5
    )


def test_pick_first_match_wins():
    # 1000 → 60 px (in window); 2000 → 120 px (also in window) — first wins
    assert pick_round_scale_bp(0.06, target_min_px=50, target_max_px=150) == 1000


def test_default_options_are_round_numbers():
    # Documented ladder; check 5kb is in there for the cluster_plot bench case
    assert 5000 in DEFAULT_SCALE_OPTIONS
    assert 1_000_000 in DEFAULT_SCALE_OPTIONS


# ── format_genomic_distance ─────────────────────────────────────────────────


def test_kb_short_style_default():
    assert format_genomic_distance(5000) == "5 kb"
    assert format_genomic_distance(500) == "500 bp"
    assert format_genomic_distance(20_000) == "20 kb"


def test_kb_short_uses_integer_division():
    # 1500 bp → "1 kb" not "1.5 kb" in this style (matches cluster_plot legacy)
    assert format_genomic_distance(1500) == "1 kb"


def test_kbp_style_telogator():
    assert format_genomic_distance(10_000, style="kbp") == "10 Kbp"
    assert format_genomic_distance(5000, style="kbp") == "5 Kbp"


def test_auto_style_assembly_contig():
    assert format_genomic_distance(2_000_000, style="auto") == "2 Mb"
    assert format_genomic_distance(1_500_000, style="auto") == "1.5 Mb"
    assert format_genomic_distance(50_000, style="auto") == "50 kb"
    assert format_genomic_distance(75_500, style="auto") == "75.5 kb"
    assert format_genomic_distance(500, style="auto") == "500 bp"


def test_unknown_style_raises():
    with pytest.raises(ValueError):
        format_genomic_distance(1000, style="bogus")
