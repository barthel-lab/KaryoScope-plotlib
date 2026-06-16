"""Unit tests for karyoplot.svg modules."""

from pathlib import Path

import drawsvg as draw
import pytest

# ----- drawing -----


def test_color_lookup_flat_dict():
    from karyoplot.svg.drawing import _color_lookup

    palette = {"foo": "#FF0000"}
    assert _color_lookup("foo", "anytype", palette) == "#FF0000"


def test_color_lookup_nested_dict():
    from karyoplot.svg.drawing import _color_lookup

    palette = {"chromosome": {"chr1": "#111111"}, "repeat": {"L1": "#222222"}}
    assert _color_lookup("chr1", "chromosome", palette) == "#111111"
    assert _color_lookup("L1", "repeat", palette) == "#222222"


def test_color_lookup_default_on_miss():
    from karyoplot.core.colors import DEFAULT_COLOR
    from karyoplot.svg.drawing import _color_lookup

    assert _color_lookup("missing", "type", {}) == DEFAULT_COLOR


def test_draw_annotation_track_appends_rectangles_and_records_colors():
    from karyoplot.svg.drawing import draw_annotation_track

    d = draw.Drawing(100, 100)
    used: dict = {}
    regions = [(10, 50, "feat_a"), (60, 90, "feat_b")]
    palette = {"chromosome": {"feat_a": "#FF0000", "feat_b": "#00FF00"}}
    draw_annotation_track(
        d,
        regions,
        y_pos=10,
        track_height=8,
        x_scale=1.0,
        x_offset=0,
        annot_type="chromosome",
        label="chr",
        text_color="#FFFFFF",
        left_margin=0,
        color_maps=palette,
        used_colors=used,
        plot_width=100,
        view_start=0,
        view_end=100,
    )
    assert used["chromosome"]["feat_a"] == "#FF0000"
    assert used["chromosome"]["feat_b"] == "#00FF00"
    # Two rectangles should have been added
    assert len(d.elements) == 2


def test_draw_axis_runs_clean():
    from karyoplot.svg.drawing import draw_axis

    d = draw.Drawing(200, 50)
    draw_axis(
        d,
        view_start=0,
        view_end=10_000,
        y_pos=20,
        x_scale=0.02,
        x_offset=10,
        text_color="#FFFFFF",
        left_margin=10,
        plot_width=180,
        title="test axis",
    )
    # Title + axis line + at least one tick group
    assert len(d.elements) >= 3


# ----- legend -----


def test_draw_hexamer_legend_vertical_returns_y():
    from karyoplot.svg.legend import draw_hexamer_legend

    d = draw.Drawing(200, 200)
    final_y = draw_hexamer_legend(d, x_pos=10, y_pos=10, text_color="#FFFFFF")
    assert final_y > 10
    assert len(d.elements) > 0


def test_strip_label_suffixes():
    from karyoplot.svg.legend import _strip_label_suffixes

    assert _strip_label_suffixes("chr13_specific") == "chr13"
    assert _strip_label_suffixes("autosome_multigroup1") == "autosome"
    assert _strip_label_suffixes("plain_name") == "plain name"


def test_draw_grouped_legend_column_layout():
    from karyoplot.svg.legend import draw_grouped_legend

    d = draw.Drawing(400, 200)
    used = {
        "chromosome": {"chr1": "#FF0000"},
        "repeat": {"L1": "#00FF00", "L2": "#0000FF"},
    }
    labels = {"chromosome": "Chromosome", "repeat": "Repeats"}
    final_y = draw_grouped_legend(
        d,
        x_pos=10,
        y_pos=10,
        text_color="#FFFFFF",
        used_colors=used,
        track_labels=labels,
        tracks=["chromosome", "repeat"],
        layout="column",
    )
    assert final_y > 10
    assert len(d.elements) > 0


def test_draw_grouped_legend_unknown_layout_raises():
    from karyoplot.svg.legend import draw_grouped_legend

    d = draw.Drawing(100, 100)
    with pytest.raises(ValueError):
        draw_grouped_legend(
            d,
            x_pos=0,
            y_pos=0,
            text_color="#FFFFFF",
            used_colors={},
            track_labels={},
            tracks=[],
            layout="bogus",
        )


def test_featureset_legend_items_groups_with_headers():
    from karyoplot.svg.legend import featureset_legend_items

    by_set = {
        "chromosome": {"chr1": "#FF0000", "chr2": "#00FF00"},
        "repeat": {"LINE": "#0000FF"},
    }
    items = featureset_legend_items(by_set)
    # One header per set + one row per feature, in input order.
    assert items[0] == ("chromosome", "", True)
    assert ("chr1", "#FF0000", False) in items
    assert items[3] == ("repeat", "", True)
    assert items[-1] == ("LINE", "#0000FF", False)


def test_featureset_legend_items_filters_and_orders():
    from karyoplot.svg.legend import featureset_legend_items

    by_set = {
        "chromosome": {"chr1": "#FF0000", "chr2": "#00FF00"},
        "repeat": {"LINE": "#0000FF"},
    }
    # Restrict sets/features, custom header label; an emptied set yields no header.
    items = featureset_legend_items(
        by_set,
        feature_sets=["repeat", "chromosome"],
        set_labels={"repeat": "Repeats"},
        exclude={"chr1", "chr2"},
    )
    assert items == [("Repeats", "", True), ("LINE", "#0000FF", False)]


def test_merge_by_color_keeps_shortest_label():
    from karyoplot.svg.legend import merge_by_color

    items = [("chr13_specific", "#FF0000"), ("acrocentric_long", "#FF0000")]
    merged = merge_by_color(items)
    assert merged == [("chr13", "#FF0000")]


def test_merge_by_color_with_overrides():
    from karyoplot.svg.legend import merge_by_color

    items = [("chr13_specific", "#FF0000"), ("chr14_specific", "#FF0000")]
    merged = merge_by_color(items, label_overrides={"chr13_specific": "acrocentric"})
    assert merged == [("acrocentric", "#FF0000")]


def test_make_legend_drawing_dark_default_background(tmp_path: Path):
    from karyoplot.svg.legend import make_legend_drawing

    items = [("a", "#FF0000", False), ("b", "#00FF00", False)]
    d = make_legend_drawing(items)
    out = tmp_path / "legend.svg"
    d.save_svg(str(out))
    svg = out.read_text()
    # default theme is dark: black background rect
    assert 'fill="#000000"' in svg or 'fill="black"' in svg
    # Default font is sans-serif
    assert 'font-family="sans-serif"' in svg


def test_make_legend_drawing_with_light_theme(tmp_path: Path):
    from karyoplot.core.theme import LIGHT
    from karyoplot.svg.legend import make_legend_drawing

    items = [("a", "#FF0000", False)]
    d = make_legend_drawing(items, theme=LIGHT)
    out = tmp_path / "legend.svg"
    d.save_svg(str(out))
    svg = out.read_text()
    # light theme uses white background
    assert 'fill="#FFFFFF"' in svg


def test_make_legend_drawing_handles_headers(tmp_path: Path):
    from karyoplot.svg.legend import make_legend_drawing

    items = [
        ("Chromosomes", "", True),
        ("chr1", "#FF0000", False),
        ("chr2", "#00FF00", False),
        ("Repeats", "", True),
        ("L1", "#0000FF", False),
    ]
    d = make_legend_drawing(items, cols=2)
    out = tmp_path / "legend.svg"
    d.save_svg(str(out))
    svg = out.read_text()
    assert "Chromosomes" in svg
    assert "Repeats" in svg


def test_make_legend_drawing_empty_items():
    from karyoplot.svg.legend import make_legend_drawing

    d = make_legend_drawing([])
    # Should produce a small empty drawing without crashing
    assert d.width > 0


# ----- export -----


def test_svg_to_png_missing_tool_returns_none(monkeypatch, tmp_path: Path):
    from karyoplot.svg import export

    svg = tmp_path / "test.svg"
    svg.write_text('<svg xmlns="http://www.w3.org/2000/svg"></svg>')

    def fake_run(*args, **kwargs):
        raise FileNotFoundError("rsvg-convert")

    monkeypatch.setattr(export.subprocess, "run", fake_run)
    result = export.svg_to_png(svg, raise_on_error=False)
    assert result is None


def test_svg_to_png_missing_tool_raises_when_requested(monkeypatch, tmp_path: Path):
    from karyoplot.svg import export

    svg = tmp_path / "test.svg"
    svg.write_text('<svg xmlns="http://www.w3.org/2000/svg"></svg>')

    def fake_run(*args, **kwargs):
        raise FileNotFoundError("rsvg-convert")

    monkeypatch.setattr(export.subprocess, "run", fake_run)
    with pytest.raises(export.RsvgConvertMissingError):
        export.svg_to_png(svg, raise_on_error=True)


def test_svg_to_png_scale_vs_dpi_mutually_exclusive(monkeypatch, tmp_path: Path):
    from karyoplot.svg import export

    svg = tmp_path / "test.svg"
    svg.write_text('<svg xmlns="http://www.w3.org/2000/svg"></svg>')
    monkeypatch.setattr(export.subprocess, "run", lambda *a, **kw: None)
    with pytest.raises(ValueError):
        export.svg_to_png(svg, scale=4, dpi=300)


def test_svg_to_png_dpi_emits_d_and_p_flags(monkeypatch, tmp_path: Path):
    from karyoplot.svg import export

    svg = tmp_path / "test.svg"
    svg.write_text('<svg xmlns="http://www.w3.org/2000/svg"></svg>')

    captured = {}

    def fake_run(cmd, **kwargs):
        captured["cmd"] = cmd

    monkeypatch.setattr(export.subprocess, "run", fake_run)
    export.svg_to_png(svg, dpi=300)
    assert "-d" in captured["cmd"] and "-p" in captured["cmd"]
    assert "300" in captured["cmd"]
    assert "-z" not in captured["cmd"]


def test_svg_to_png_scale_emits_z_flag(monkeypatch, tmp_path: Path):
    from karyoplot.svg import export

    svg = tmp_path / "test.svg"
    svg.write_text('<svg xmlns="http://www.w3.org/2000/svg"></svg>')

    captured = {}

    def fake_run(cmd, **kwargs):
        captured["cmd"] = cmd

    monkeypatch.setattr(export.subprocess, "run", fake_run)
    export.svg_to_png(svg, scale=4)
    assert "-z" in captured["cmd"]
    assert "4" in captured["cmd"]
    assert "-d" not in captured["cmd"]
