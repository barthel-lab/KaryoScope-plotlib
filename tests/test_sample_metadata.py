"""Unit tests for karyoplot.core.sample_metadata.

These tests verify the unified loader produces the same dicts as the two
legacy implementations would have, on equivalent input.
"""

from pathlib import Path

import pytest

from karyoplot.core.sample_metadata import (
    SampleMetadata,
    load_sample_metadata,
)


# ----- file fixtures -----

def _write_full_metadata(path: Path) -> Path:
    path.write_text(
        "sample\tgroup\tcolor\tgroup_color\tdisplay_name\n"
        "U2OS\tcell_line_alt\t#60A5FA\t#60A5FA\tALT line\n"
        "HeLa\tcell_line_tel\t#F07167\t#F07167\tTel line\n"
        "HeLa_LT\tcell_line_tel\t#F07167\t#F07167\tTel LT\n"
        "BJ\tcell_line_normal\t#545454\t#222222\tNormal\n"
    )
    return path


def _write_minimal_metadata(path: Path) -> Path:
    """Same shape as the real fiberseq_all.sample_metadata.tsv."""
    path.write_text(
        "sample\tgroup\tcolor\n"
        "U2OS\tcell_line_alt\t#60A5FA\n"
        "HeLa\tcell_line_tel\t#F07167\n"
        "HeLa_LT\tcell_line_tel\t#F07167\n"
        "BJ\tcell_line_normal\t#545454\n"
    )
    return path


# ----- core behaviour -----

def test_loads_full_metadata(tmp_path: Path):
    f = _write_full_metadata(tmp_path / "meta.tsv")
    md = load_sample_metadata(f, quiet=True)
    assert md.sample_to_group == {
        "U2OS": "cell_line_alt",
        "HeLa": "cell_line_tel",
        "HeLa_LT": "cell_line_tel",
        "BJ": "cell_line_normal",
    }
    assert md.sample_to_color == {
        "U2OS": "#60A5FA",
        "HeLa": "#F07167",
        "HeLa_LT": "#F07167",
        "BJ": "#545454",
    }
    assert md.group_to_color == {
        "cell_line_alt": "#60A5FA",
        "cell_line_tel": "#F07167",
        "cell_line_normal": "#222222",   # last sample wins iteration order
    }
    assert md.sample_to_display_name == {
        "U2OS": "ALT line",
        "HeLa": "Tel line",
        "HeLa_LT": "Tel LT",
        "BJ": "Normal",
    }


def test_minimal_metadata_no_group_color_no_display(tmp_path: Path):
    f = _write_minimal_metadata(tmp_path / "meta.tsv")
    md = load_sample_metadata(f, quiet=True)
    assert md.group_to_color == {}            # no group_color column
    assert md.sample_to_display_name == {}    # no display_name column
    assert len(md.sample_to_group) == 4


def test_derive_group_colors_from_samples(tmp_path: Path):
    """cluster_plot's group_colors comes from per-sample colors, first wins."""
    f = _write_minimal_metadata(tmp_path / "meta.tsv")
    md = load_sample_metadata(f, quiet=True)
    derived = md.derive_group_colors_from_samples()
    assert derived == {
        "cell_line_alt": "#60A5FA",
        "cell_line_tel": "#F07167",
        "cell_line_normal": "#545454",
    }


# ----- missing-samples auto-fill (cluster_analysis behaviour) -----

def test_sample_labels_fill_missing_as_own_group(tmp_path: Path):
    f = _write_minimal_metadata(tmp_path / "meta.tsv")
    md = load_sample_metadata(
        f,
        sample_labels=["U2OS", "HeLa", "BJ", "EXTRA1", "EXTRA2"],
        quiet=True,
    )
    # Original 4 samples preserved; HeLa_LT not in sample_labels but still present
    assert md.sample_to_group["U2OS"] == "cell_line_alt"
    # Missing samples become their own group
    assert md.sample_to_group["EXTRA1"] == "EXTRA1"
    assert md.sample_to_group["EXTRA2"] == "EXTRA2"


def test_no_metadata_file_with_sample_labels(tmp_path: Path):
    """cluster_analysis path: no metadata file, sample_labels supplied."""
    md = load_sample_metadata(None, sample_labels=["A", "B", "C"], quiet=True)
    assert md.sample_to_group == {"A": "A", "B": "B", "C": "C"}
    assert md.sample_to_color == {}
    assert md.group_to_color == {}


# ----- error / fallback handling -----

def test_no_metadata_file_no_labels_returns_empty():
    md = load_sample_metadata(None, quiet=True)
    assert isinstance(md, SampleMetadata)
    assert md.sample_to_group == {}


def test_missing_sample_column_raises_when_required(tmp_path: Path):
    f = tmp_path / "bad.tsv"
    f.write_text("group\tcolor\nfoo\t#000\n")
    with pytest.raises(ValueError, match="must have 'sample' column"):
        load_sample_metadata(f, require_sample_column=True, quiet=True)


def test_missing_sample_column_silent_when_not_required(tmp_path: Path):
    """cluster_plot path: bad file silently returns empty dicts."""
    f = tmp_path / "bad.tsv"
    f.write_text("group\tcolor\nfoo\t#000\n")
    md = load_sample_metadata(f, require_sample_column=False, quiet=True)
    assert md.sample_to_group == {}


def test_nonexistent_file_returns_empty(tmp_path: Path):
    md = load_sample_metadata(tmp_path / "no-such-file.tsv", quiet=True)
    assert md.sample_to_group == {}


# ----- regression equivalence: cluster_plot legacy behaviour -----

def test_cluster_plot_4_tuple_equivalence(tmp_path: Path):
    """Reproduce cluster_plot's load_sample_metadata 4-tuple signature."""
    f = _write_full_metadata(tmp_path / "meta.tsv")
    md = load_sample_metadata(f, require_sample_column=False, quiet=True)
    # cluster_plot legacy 4-tuple:
    sample_to_group = md.sample_to_group
    sample_colors = md.sample_to_color
    group_colors = md.derive_group_colors_from_samples()
    sample_display_names = md.sample_to_display_name

    assert sample_to_group["U2OS"] == "cell_line_alt"
    # cluster_plot's group_colors derives from sample_to_color, FIRST seen wins
    assert group_colors["cell_line_normal"] == "#545454"  # BJ sample's color
    assert sample_display_names["U2OS"] == "ALT line"


def test_cluster_analysis_3_tuple_equivalence(tmp_path: Path):
    """Reproduce cluster_analysis's load_sample_metadata 3-tuple signature."""
    f = _write_full_metadata(tmp_path / "meta.tsv")
    md = load_sample_metadata(
        f,
        sample_labels=["U2OS", "HeLa", "HeLa_LT", "BJ", "EXTRA"],
        require_sample_column=True,
        quiet=True,
    )
    sample_to_group = md.sample_to_group
    sample_to_color = md.sample_to_color
    group_to_color = md.group_to_color  # explicit column, last wins
    assert sample_to_group["EXTRA"] == "EXTRA"
    # explicit column: cell_line_normal had a different group_color (#222222)
    assert group_to_color["cell_line_normal"] == "#222222"
    assert sample_to_color["U2OS"] == "#60A5FA"
