"""Unit tests for karyoplot.core.colors palette loaders.

These cover the two new functions :func:`load_palette_file` and
:func:`load_featureset_palettes` that subsume the 5 legacy color-loading
variants. Each test mirrors a specific legacy behaviour the unified
function must preserve.
"""

from pathlib import Path

import pytest

from karyoplot.core.colors import (
    load_featureset_palettes,
    load_palette_file,
)


# Sample colors file content used by both single-file and multi-file tests.
SAMPLE = """\
feature\tcolor
chr13_specific\t#FF0000
chr14_specific\t#00FF00
DJ_specific\t#0000FF
"""

SAMPLE_WITH_SECTIONS = """\
# Chromosomes
chr13_specific\t#FF0000
chr14_specific\t#00FF00
# Features
DJ_specific\t#0000FF
PJ_specific\t#FFFF00
"""


# ── single-file: load_palette_file ──────────────────────────────────────────

def test_load_palette_file_basic_hex(tmp_path: Path):
    f = tmp_path / "x.colors.txt"
    f.write_text(SAMPLE)
    palette = load_palette_file(f)
    # Header skipped; _specific reverse mapping added; bare hex format
    assert palette == {
        "chr13_specific": "#FF0000",
        "chr13": "#FF0000",
        "chr14_specific": "#00FF00",
        "chr14": "#00FF00",
        "DJ_specific": "#0000FF",
        "DJ": "#0000FF",
    }


def test_load_palette_file_tuple_format(tmp_path: Path):
    f = tmp_path / "x.colors.txt"
    f.write_text(SAMPLE)
    palette = load_palette_file(f, value_format="tuple")
    assert palette["chr13_specific"] == ("#FF0000", 1.0)
    assert palette["chr13"] == ("#FF0000", 1.0)


def test_load_palette_file_missing_returns_empty(tmp_path: Path):
    palette = load_palette_file(tmp_path / "no-such-file.txt")
    assert palette == {}


def test_load_palette_file_missing_with_initial(tmp_path: Path):
    initial = {"novel": "#FFFFFF"}
    palette = load_palette_file(tmp_path / "no-such-file.txt", initial=initial)
    # Missing file → only the initial dict is returned
    assert palette == {"novel": "#FFFFFF"}


def test_load_palette_file_initial_seed(tmp_path: Path):
    f = tmp_path / "x.colors.txt"
    f.write_text(SAMPLE)
    palette = load_palette_file(f, initial={"novel": "#FFFFFF"})
    assert palette["novel"] == "#FFFFFF"
    assert palette["chr13_specific"] == "#FF0000"


def test_load_palette_file_suffix_both_ways(tmp_path: Path):
    f = tmp_path / "x.colors.txt"
    f.write_text("plainfeat\t#ABCDEF\n")
    palette = load_palette_file(f, suffix_both_ways=True)
    # suffix_both_ways=True adds bare → _specific direction too
    assert palette == {
        "plainfeat": "#ABCDEF",
        "plainfeat_specific": "#ABCDEF",
    }


def test_load_palette_file_multigroup1_not_doubled(tmp_path: Path):
    """_multigroup1 names must NOT receive a forward _specific mapping."""
    f = tmp_path / "x.colors.txt"
    f.write_text("autosome_multigroup1\t#888888\n")
    palette = load_palette_file(f, suffix_both_ways=True)
    assert "autosome_multigroup1_specific" not in palette


def test_load_palette_file_with_sections(tmp_path: Path):
    f = tmp_path / "x.colors.txt"
    f.write_text(SAMPLE_WITH_SECTIONS)
    palette, sections = load_palette_file(f, parse_sections=True)
    assert palette["chr13_specific"] == "#FF0000"
    assert sections == [
        ("Chromosomes", ["chr13_specific", "chr14_specific"]),
        ("Features", ["DJ_specific", "PJ_specific"]),
    ]


def test_load_palette_file_no_sections_wraps_in_none_header(tmp_path: Path):
    f = tmp_path / "x.colors.txt"
    f.write_text(SAMPLE)  # no '# Header' lines
    palette, sections = load_palette_file(f, parse_sections=True)
    # When there are no section markers, the entire palette is wrapped in
    # one (None, [...]) section
    assert len(sections) == 1
    assert sections[0][0] is None


def test_load_palette_file_track_order(tmp_path: Path):
    f = tmp_path / "x.colors.txt"
    f.write_text(SAMPLE)
    palette, order = load_palette_file(f, track_order=True)
    assert order == ["chr13_specific", "chr14_specific", "DJ_specific"]
    assert "chr13_specific" in palette


def test_load_palette_file_invalid_value_format_raises(tmp_path: Path):
    with pytest.raises(ValueError):
        load_palette_file(tmp_path / "x.txt", value_format="bogus")


# ── multi-file: load_featureset_palettes ────────────────────────────────────

def _setup_dir(tmp_path: Path, database: str = "KS_test"):
    (tmp_path / f"{database}.repeat.colors.txt").write_text(
        "feature\tcolor\nLINE_specific\t#AAA\nSINE_specific\t#BBB\n"
    )
    (tmp_path / f"{database}.region.colors.txt").write_text(
        "feature\tcolor\ncentromeric\t#CCC\n"
    )
    return database


def test_load_featureset_palettes_basic(tmp_path: Path):
    db = _setup_dir(tmp_path)
    out = load_featureset_palettes(tmp_path, db, ["repeat", "region"])
    assert "repeat" in out and "region" in out
    # Default value_format is 'tuple' (legacy multi-file shape)
    assert out["repeat"]["LINE_specific"] == ("#AAA", 1.0)
    assert out["region"]["centromeric"] == ("#CCC", 1.0)


def test_load_featureset_palettes_hex_format(tmp_path: Path):
    db = _setup_dir(tmp_path)
    out = load_featureset_palettes(tmp_path, db, ["repeat"], value_format="hex")
    assert out["repeat"]["LINE_specific"] == "#AAA"


def test_load_featureset_palettes_with_background_seeds_novel_unknown(tmp_path: Path):
    db = _setup_dir(tmp_path)
    # Legacy convention (assembly_contig_zoom): novel matches background.
    out = load_featureset_palettes(tmp_path, db, ["repeat"], background="black")
    assert out["repeat"]["novel"] == ("#000000", 1.0)
    assert out["repeat"]["unknown"] == ("#808080", 1.0)
    out_white = load_featureset_palettes(tmp_path, db, ["repeat"], background="white")
    assert out_white["repeat"]["novel"] == ("#ffffff", 1.0)


def test_load_featureset_palettes_missing_warn(tmp_path: Path, capsys):
    db = _setup_dir(tmp_path)
    out = load_featureset_palettes(
        tmp_path, db, ["repeat", "nonexistent"], on_missing="warn",
    )
    captured = capsys.readouterr().out
    assert "Warning" in captured
    assert out["repeat"]                    # loaded
    assert out["nonexistent"] == {}         # empty without seed


def test_load_featureset_palettes_missing_silent(tmp_path: Path, capsys):
    db = _setup_dir(tmp_path)
    out = load_featureset_palettes(
        tmp_path, db, ["nonexistent"], on_missing="silent",
    )
    captured = capsys.readouterr().out
    assert "Warning" not in captured
    assert out["nonexistent"] == {}


def test_load_featureset_palettes_missing_error_exits(tmp_path: Path):
    db = _setup_dir(tmp_path)
    with pytest.raises(SystemExit):
        load_featureset_palettes(
            tmp_path, db, ["nonexistent"], on_missing="error",
        )


def test_load_featureset_palettes_track_order(tmp_path: Path):
    db = _setup_dir(tmp_path)
    out, orders = load_featureset_palettes(
        tmp_path, db, ["repeat"], track_order=True,
    )
    assert orders["repeat"] == ["LINE_specific", "SINE_specific"]
