"""Unit tests for karyoplot.mpl modules.

These tests use Agg backend and tmp_path-based output to avoid display
dependencies. End-to-end plot rendering is exercised via small synthetic
inputs rather than full-scale data.
"""

from pathlib import Path

import matplotlib
import numpy as np
import pandas as pd
import pytest

matplotlib.use("Agg")


# ----- types -----


def test_feature_group_columns():
    from karyoplot.mpl.types import FeatureGroup

    fg = FeatureGroup(
        name="repeats", label="Repeats", color="#FF0000", features=["L1", "Alu"], aggregation="sum"
    )
    assert fg.get_columns("repeat", "dmax") == [
        "repeat_dmax__L1",
        "repeat_dmax__Alu",
    ]


def test_comparison_config_minimal_construction():
    from karyoplot.mpl.types import (
        ComparisonConfig,
        Condition,
        FeatureGroup,
    )

    cfg = ComparisonConfig(
        name="t",
        annotations_dir="/tmp",
        output_dir="/tmp",
        output_prefix="t",
        featureset="repeat",
        metric="dmax",
        threshold=0.5,
        comparison_mode="reference",
        reference_condition="a",
        conditions={
            "a": Condition("a", "A", "#FF0000", ["s1"]),
            "b": Condition("b", "B", "#00FF00", ["s2"]),
        },
        feature_groups={
            "L1": FeatureGroup("L1", "LINE-1", "#0000FF", ["L1"]),
        },
    )
    assert cfg.dark_mode is False
    assert cfg.covariates is None


# ----- style -----


def test_apply_default_style_runs(tmp_path: Path):
    import matplotlib.pyplot as plt

    from karyoplot.mpl import style

    style.apply_default_style(dark_mode=False)
    assert plt.rcParams["font.size"] == 10
    assert plt.rcParams["axes.spines.top"] is False


def test_fg_color():
    from karyoplot.mpl.style import fg_color

    assert fg_color(True) == "white"
    assert fg_color(False) == "black"


def test_sig_label():
    from karyoplot.mpl.style import sig_label

    assert sig_label(0.0001) == "***"
    assert sig_label(0.005) == "**"
    assert sig_label(0.04) == "*"
    assert sig_label(0.5) == "ns"


def test_save_fig_writes_both(tmp_path: Path):
    import matplotlib.pyplot as plt

    from karyoplot.mpl.style import save_fig

    fig, ax = plt.subplots()
    ax.plot([0, 1], [0, 1])
    svg, png = save_fig(fig, str(tmp_path / "out"), "test")
    assert Path(svg).exists()
    assert Path(png).exists()


# ----- data_loader -----


def _build_min_config(annot_dir: str) -> "object":
    from karyoplot.mpl.types import (
        ComparisonConfig,
        Condition,
        FeatureGroup,
    )

    return ComparisonConfig(
        name="t",
        annotations_dir=annot_dir,
        output_dir="/tmp",
        output_prefix="t",
        featureset="repeat",
        metric="dmax",
        threshold=0.5,
        comparison_mode="reference",
        reference_condition="a",
        conditions={
            "a": Condition("a", "A", "#FF0000", ["s1"]),
            "b": Condition("b", "B", "#00FF00", ["s2"]),
        },
        feature_groups={
            "L1": FeatureGroup("L1", "LINE-1", "#0000FF", ["L1"]),
            "Alu": FeatureGroup("Alu", "Alu", "#888888", ["Alu"]),
        },
    )


def _make_annot_file(dirpath: Path, sample: str, n_reads: int = 4) -> None:
    """Write a tiny .sequence_annotations.tsv.gz fixture."""
    df = pd.DataFrame(
        {
            "sequence": [f"{sample}_read{i}" for i in range(n_reads)],
            "sequencing_approach": ["ONT"] * n_reads,
            "repeat_dmax__L1": np.linspace(0.1, 0.9, n_reads),
            "repeat_dmax__Alu": [0.2, 0.6, 0.8, 0.4][:n_reads],
        }
    )
    df.to_csv(
        dirpath / f"{sample}.sequence_annotations.tsv.gz", sep="\t", index=False, compression="gzip"
    )


def test_load_annotations_and_rates(tmp_path: Path):
    from karyoplot.mpl.data_loader import (
        compute_feature_values,
        compute_per_sample_rates,
        load_annotations,
    )

    _make_annot_file(tmp_path, "s1")
    _make_annot_file(tmp_path, "s2")

    cfg = _build_min_config(str(tmp_path))
    annots = load_annotations(cfg)
    assert "s1" in annots and "s2" in annots
    assert len(annots["s1"]) == 4

    values = compute_feature_values(annots["s1"], cfg.feature_groups, cfg.featureset, cfg.metric)
    assert "L1" in values and "Alu" in values
    assert (values["L1"] > 0.5).sum() == 2  # vals 0.6333..., 0.8666... > 0.5

    rates = compute_per_sample_rates(annots, cfg)
    assert set(rates.columns) >= {
        "sample",
        "condition",
        "L1_count",
        "L1_rate",
        "Alu_count",
        "Alu_rate",
    }
    assert len(rates) == 2


def test_compute_feature_values_sum_aggregation(tmp_path: Path):
    from karyoplot.mpl.data_loader import compute_feature_values
    from karyoplot.mpl.types import FeatureGroup

    df = pd.DataFrame(
        {
            "repeat_dmax__L1": [0.2, 0.3],
            "repeat_dmax__Alu": [0.1, 0.4],
        }
    )
    fg = FeatureGroup("composite", "Composite", "#000", features=["L1", "Alu"], aggregation="sum")
    out = compute_feature_values(df, {"composite": fg}, "repeat", "dmax")
    assert list(out["composite"]) == [pytest.approx(0.3), pytest.approx(0.7)]


def test_compute_feature_values_missing_columns_returns_zero():
    from karyoplot.mpl.data_loader import compute_feature_values
    from karyoplot.mpl.types import FeatureGroup

    df = pd.DataFrame({"other": [1, 2]})
    fg = FeatureGroup("x", "X", "#000", features=["L1"])
    out = compute_feature_values(df, {"x": fg}, "repeat", "dmax")
    assert list(out["x"]) == [0.0, 0.0]


def test_load_annotations_warns_on_missing(tmp_path: Path, capsys):
    from karyoplot.mpl.data_loader import load_annotations

    cfg = _build_min_config(str(tmp_path))  # no files written
    annots = load_annotations(cfg)
    assert annots == {}
    captured = capsys.readouterr()
    assert "WARNING" in captured.out


# ----- statistics -----


def test_apply_fdr_basic():
    from karyoplot.mpl.statistics import apply_fdr

    df = pd.DataFrame({"x_p": [0.001, 0.04, 0.06, 0.5]})
    out = apply_fdr(df)
    assert "x_p_fdr" in out.columns
    # FDR is monotonically non-decreasing across sorted p-values
    sorted_fdr = out.sort_values("x_p")["x_p_fdr"].values
    assert all(sorted_fdr[i] <= sorted_fdr[i + 1] for i in range(len(sorted_fdr) - 1))


def test_apply_fdr_empty_df():
    from karyoplot.mpl.statistics import apply_fdr

    out = apply_fdr(pd.DataFrame())
    assert out.empty


def test_compare_two_conditions_smoke(tmp_path: Path):
    from karyoplot.mpl.data_loader import load_annotations
    from karyoplot.mpl.statistics import compare_two_conditions

    _make_annot_file(tmp_path, "s1")
    _make_annot_file(tmp_path, "s2")
    cfg = _build_min_config(str(tmp_path))
    annots = load_annotations(cfg)

    stats = compare_two_conditions(
        annots,
        cfg.conditions["a"],
        cfg.conditions["b"],
        cfg,
    )
    assert not stats.empty
    assert "pooled_fisher_p" in stats.columns
    assert "log2FC" in stats.columns
    assert set(stats["feature"]) == {"L1", "Alu"}


# ----- heatmap helpers -----


def test_fix_leaf_ordering_preserves_shape():
    from scipy.cluster.hierarchy import linkage

    from karyoplot.mpl.heatmap import fix_leaf_ordering

    rng = np.random.default_rng(0)
    X = rng.normal(size=(8, 4))
    Z = linkage(X, method="ward")
    Z2 = fix_leaf_ordering(Z, X)
    assert Z2.shape == Z.shape


def test_cluster_and_reorder_runs():
    from karyoplot.mpl.heatmap import cluster_and_reorder

    rng = np.random.default_rng(1)
    n = 5
    z = rng.normal(size=(n, 3))
    raw = rng.uniform(0, 100, size=(n, 3))
    sample_labels = np.array([f"s{i}" for i in range(n)])
    cond_colors = np.array(["#FF0000"] * n)
    fg_labels = ["A", "B", "C"]

    (z2, raw2, sl2, _cc2, _fgl2, _, row_link, col_link, _) = cluster_and_reorder(
        z,
        raw,
        sample_labels,
        cond_colors,
        fg_labels,
    )
    assert z2.shape == z.shape
    assert raw2.shape == raw.shape
    assert len(sl2) == n
    assert row_link.shape == (n - 1, 4)
    assert col_link.shape == (2, 4)


def test_plot_heatmap_end_to_end(tmp_path: Path):
    from karyoplot.mpl.data_loader import compute_per_sample_rates, load_annotations
    from karyoplot.mpl.heatmap import plot_heatmap

    # Need >1 sample per condition for clustering, and at least 2 features
    for s in ("s1", "s2", "s3", "s4"):
        _make_annot_file(tmp_path, s)
    from karyoplot.mpl.types import Condition

    cfg = _build_min_config(str(tmp_path))
    cfg.conditions["a"] = Condition("a", "A", "#FF0000", ["s1", "s2"])
    cfg.conditions["b"] = Condition("b", "B", "#00FF00", ["s3", "s4"])

    annots = load_annotations(cfg)
    rates = compute_per_sample_rates(annots, cfg)
    svg, png = plot_heatmap(rates, cfg, str(tmp_path / "out"))
    assert Path(svg).exists()
    assert Path(png).exists()


# ----- comparison plots -----


def test_arcsin_sqrt_transform():
    from karyoplot.mpl.comparison import _arcsin_sqrt

    assert _arcsin_sqrt(0) == 0
    assert _arcsin_sqrt(100) == pytest.approx(np.pi / 2)


def test_plot_volcano_returns_none_on_empty(tmp_path: Path):
    from karyoplot.mpl.comparison import plot_volcano

    cfg = _build_min_config(str(tmp_path))
    out = plot_volcano(pd.DataFrame(), cfg, str(tmp_path / "v"), "a", "b")
    assert out is None


def test_plot_dot_strip_runs(tmp_path: Path):
    from karyoplot.mpl.comparison import plot_dot_strip
    from karyoplot.mpl.data_loader import compute_per_sample_rates, load_annotations
    from karyoplot.mpl.statistics import compare_two_conditions
    from karyoplot.mpl.types import Condition

    for s in ("s1", "s2", "s3", "s4"):
        _make_annot_file(tmp_path, s)
    cfg = _build_min_config(str(tmp_path))
    cfg.conditions["a"] = Condition("a", "A", "#FF0000", ["s1", "s2"])
    cfg.conditions["b"] = Condition("b", "B", "#00FF00", ["s3", "s4"])

    annots = load_annotations(cfg)
    rates = compute_per_sample_rates(annots, cfg)
    stats = compare_two_conditions(annots, cfg.conditions["a"], cfg.conditions["b"], cfg)
    svg, png = plot_dot_strip(rates, stats, cfg, str(tmp_path / "ds"), "a", "b")
    assert Path(svg).exists()
    assert Path(png).exists()
