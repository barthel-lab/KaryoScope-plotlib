"""Unit tests for karyoplot.core modules."""

import gzip
from pathlib import Path

import pytest

# ----- chromosomes -----


def test_chrom_sort_key_orders_canonical():
    from karyoplot.core.chromosomes import chrom_sort_key

    chroms = ["chrY", "chr10", "chr1", "chrX", "chr2", "chrM"]
    assert sorted(chroms, key=chrom_sort_key) == [
        "chr1",
        "chr2",
        "chr10",
        "chrX",
        "chrY",
        "chrM",
    ]


def test_chrom_sort_key_handles_no_chr_prefix():
    from karyoplot.core.chromosomes import chrom_sort_key

    assert chrom_sort_key("1") == (1, "")
    assert chrom_sort_key("X") == (23, "")


def test_acrocentric_membership():
    from karyoplot.core.chromosomes import ACROCENTRIC

    assert "chr13" in ACROCENTRIC
    assert "chr1" not in ACROCENTRIC


def test_telomeric_motifs_have_canonical():
    from karyoplot.core.chromosomes import TELOMERIC_MOTIFS

    assert TELOMERIC_MOTIFS["TTAGGG"]["color"] == "#F07167"
    assert TELOMERIC_MOTIFS["CCCTAA"]["type"] == "canonical_rc"


def test_reference_lookup_chm13():
    from karyoplot.core.chromosomes import reference

    chm13 = reference("CHM13_v2")
    assert chm13.lengths["chr13"] == 113_566_656
    assert chm13.q_arm_starts["chr14"] == 17_708_240


# ----- colors -----


def test_load_palette_basic(tmp_path: Path):
    from karyoplot.core.colors import load_palette

    p = tmp_path / "palette.txt"
    p.write_text("feature\tcolor\nrepeat_a\t#FF0000\nrepeat_b\t#00FF00\n")
    pal = load_palette(p)
    assert pal == {"repeat_a": "#FF0000", "repeat_b": "#00FF00"}


def test_load_palette_missing_file_returns_empty(tmp_path: Path):
    from karyoplot.core.colors import load_palette

    assert load_palette(tmp_path / "nope.txt") == {}


def test_hex_rgb_roundtrip():
    from karyoplot.core.colors import hex_to_rgb, rgb_to_hex

    assert hex_to_rgb("#F07167") == (240, 113, 103)
    assert rgb_to_hex(240, 113, 103) == "#F07167"


def test_hex_to_rgba_alpha():
    from karyoplot.core.colors import hex_to_rgba

    assert hex_to_rgba("#F07167", alpha=128) == (240, 113, 103, 128)


def test_get_color_default_fallback():
    from karyoplot.core.colors import DEFAULT_COLOR, get_color

    assert get_color("missing", {"a": "#111111"}) == DEFAULT_COLOR
    assert get_color("a", {"a": "#111111"}) == "#111111"


def test_barthel_palette_keys():
    from karyoplot.core.colors import BARTHEL

    for key in ("black", "white", "coral", "lavender", "green", "blue"):
        assert key in BARTHEL


def test_tab10_tab20_canonical():
    from karyoplot.core.colors import TAB10, TAB20

    assert len(TAB10) == 10
    assert len(TAB20) == 20
    assert TAB10[0] == "#1f77b4"
    assert TAB20[0] == "#1f77b4"
    assert TAB20[1] == "#aec7e8"  # tab20 has paired light/dark


def test_qualitative_palette_cycles():
    from karyoplot.core.colors import TAB10, qualitative_palette

    assert qualitative_palette(3, TAB10) == list(TAB10[:3])
    assert qualitative_palette(12, TAB10) == list(TAB10) + list(TAB10[:2])


# ----- coords -----


def test_pixel_scale_full_mode():
    from karyoplot.core.coords import PixelScale

    s = PixelScale(mode="full", origin=10)
    assert s.pos_to_pixel(0) == 10
    assert s.pos_to_pixel(1_000_000) == 14  # 4 px per Mb + origin


def test_pixel_scale_subtelomere_mode():
    from karyoplot.core.coords import PixelScale

    s = PixelScale(mode="subtelomere")
    assert s.pos_to_pixel(3000) == 10  # 3000 * (1/300)


def test_pixel_scale_custom_factor():
    from karyoplot.core.coords import PixelScale

    s = PixelScale(mode="custom", pixels_per_bp=1.0)
    assert s.pos_to_pixel(42) == 42


def test_pixel_scale_unknown_mode_raises():
    from karyoplot.core.coords import PixelScale

    with pytest.raises(ValueError):
        PixelScale(mode="bogus")


# ----- fonts -----


def test_register_fonts_missing_dir(tmp_path: Path):
    from karyoplot.core.fonts import register_fonts

    assert register_fonts(tmp_path / "no_such_dir") == []


def test_default_font_family_is_sans_serif():
    from karyoplot.core.fonts import DEFAULT_FONT_FAMILY

    assert DEFAULT_FONT_FAMILY == "sans-serif"


def test_resolve_family_falls_back():
    from karyoplot.core.fonts import DEFAULT_FONT_FAMILY, resolve_family

    # Some random unregistered family must fall back to sans-serif
    assert resolve_family("ZZZ_NotARealFont_ZZZ") == DEFAULT_FONT_FAMILY


def test_pil_font_returns_imagefont_for_unknown_family():
    from PIL import ImageFont

    from karyoplot.core.fonts import pil_font

    # Unknown family + non-existent fallback -> always falls back to default
    f = pil_font(12, family="NotAFamily", fallback="DefinitelyNotAFont")
    assert isinstance(f, (ImageFont.ImageFont, ImageFont.FreeTypeFont))


# ----- theme -----


def test_dark_theme_matches_cluster_plot_black():
    from karyoplot.core import theme

    assert theme.DARK.background == "#000000"
    assert theme.DARK.text == "#FFFFFF"
    assert theme.DARK.font_family == "sans-serif"


def test_default_theme_is_dark():
    from karyoplot.core import theme

    assert theme.DEFAULT_THEME is theme.DARK


def test_get_theme_aliases():
    from karyoplot.core import theme

    assert theme.get("black") is theme.DARK
    assert theme.get("white") is theme.LIGHT
    assert theme.get(None) is theme.DEFAULT_THEME


def test_line_color_for_background():
    from karyoplot.core import theme

    assert theme.line_color_for("#000000") == "#FFFFFF"
    assert theme.line_color_for("black") == "#FFFFFF"
    assert theme.line_color_for("#FFFFFF") == "#333333"


# ----- io -----


def test_smart_open_plain(tmp_path: Path):
    from karyoplot.core.io import smart_open

    p = tmp_path / "x.txt"
    p.write_text("hello\n")
    with smart_open(p) as f:
        assert f.read() == "hello\n"


def test_smart_open_gzip(tmp_path: Path):
    from karyoplot.core.io import smart_open

    p = tmp_path / "x.txt.gz"
    with gzip.open(p, "wt") as f:
        f.write("zipped\n")
    with smart_open(p) as f:
        assert f.read() == "zipped\n"


def test_load_bed_basic_and_filter(tmp_path: Path):
    from karyoplot.core.io import load_bed

    p = tmp_path / "test.bed"
    p.write_text("chr1\t100\t200\trepeat\nchr1\t300\t400\tgene\nchr2\t500\t600\trepeat\n")
    df = load_bed(p)
    assert list(df.columns)[:4] == ["chrom", "start", "end", "name"]
    assert len(df) == 3

    df_repeat = load_bed(p, featureset="repeat")
    assert len(df_repeat) == 2
    assert set(df_repeat["chrom"]) == {"chr1", "chr2"}


def test_iter_bed_records_skips_comments(tmp_path: Path):
    from karyoplot.core.io import iter_bed_records

    p = tmp_path / "test.bed.gz"
    with gzip.open(p, "wt") as f:
        f.write("# comment\nchr1\t10\t20\tfoo\nchr2\t30\t40\tbar\n")
    records = list(iter_bed_records(p))
    assert records == [("chr1", 10, 20, "foo"), ("chr2", 30, 40, "bar")]
