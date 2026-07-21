"""Dataclasses describing a feature-comparison analysis.

These types are the data structures consumed by :mod:`karyoplot.mpl.data_loader`,
:mod:`karyoplot.mpl.statistics`, :mod:`karyoplot.mpl.heatmap`, and
:mod:`karyoplot.mpl.comparison`. They were promoted from
``KaryoScope-BIR/scripts/feature_comparison_lib/config.py`` so that the
plotting library has no YAML dependency — YAML loading lives in
``karyoscope_conductor.config.feature_comparison`` (Phase 5) and
instantiates these classes.

A typical workflow:

    >>> from karyoplot.mpl.types import (
    ...     FeatureGroup, Condition, ComparisonConfig
    ... )
    >>> cfg = ComparisonConfig(
    ...     name="primary_vs_E6E7",
    ...     annotations_dir="results/annotations",
    ...     output_dir="results/comparison",
    ...     output_prefix="primary_vs_E6E7",
    ...     featureset="repeat",
    ...     metric="dmax",
    ...     threshold=0.5,
    ...     comparison_mode="reference",
    ...     reference_condition="primary",
    ...     conditions={...},
    ...     feature_groups={...},
    ... )
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class FeatureGroup:
    """Definition of a feature group for comparison."""

    name: str
    label: str
    color: str
    features: list[str]
    aggregation: str = "single"  # "single" or "sum"

    def get_columns(
        self,
        featureset: str,
        metric: str,
        descendants: dict[str, list[str]] | None = None,
    ) -> list[str]:
        """Build full column names ``{featureset}__{metric}__{feature}``.

        ``__`` is the sole delimiter so featureset/metric/feature names containing
        single underscores (``region_subtelomere_flat``, ``dterminal_min``,
        ``active_hor``) stay unambiguous, and to match the columns emitted by
        ``karyoscope-analysis build-feature-matrix``.

        When ``descendants`` is given — a resolved ``{feature: [feature, *descendants]}``
        map derived from the DB hierarchy by the (DB-aware) consumer — each referenced
        feature is expanded to its whole hierarchy subtree. So a group referencing a
        parent (e.g. ``aSat``) covers all of its descendants (``alpha_hor``,
        ``active_hor``, ``mon``, …), which is correct because the flat annotation labels
        each interval at exactly one node. A referenced feature that is **not** a node
        in ``descendants`` raises ``KeyError`` — a missing feature is a typo/stale name
        to fix, not a silent zero.
        """
        if descendants is None:
            feats = list(self.features)
        else:
            feats = []
            for f in self.features:
                if f not in descendants:
                    raise KeyError(
                        f"feature {f!r} in group {self.name!r} is not a node in the DB "
                        "hierarchy for this featureset — check the feature name"
                    )
                for d in descendants[f]:
                    if d not in feats:
                        feats.append(d)
        return [f"{featureset}__{metric}__{f}" for f in feats]


@dataclass
class Condition:
    """Definition of a sample condition / group."""

    name: str
    label: str
    color: str
    samples: list[str]


@dataclass
class CovariateValue:
    """A single categorical covariate value with display label and color."""

    label: str
    color: str


@dataclass
class CovariateColumn:
    """Definition of a single covariate column."""

    source_column: str  # column name in the TSV file
    label: str  # display label
    type: str  # "categorical" or "continuous"
    values: dict[str, CovariateValue] | None = None  # for categorical
    cmap: str = "YlOrRd"  # for continuous


@dataclass
class CovariateConfig:
    """Optional covariate annotation block."""

    file: str
    id_column: str
    columns: dict[str, CovariateColumn]  # keyed by source column name


@dataclass
class ComparisonConfig:
    """Full comparison configuration consumed by the mpl plot functions."""

    name: str
    annotations_dir: str
    output_dir: str
    output_prefix: str
    featureset: str
    metric: str
    threshold: float
    comparison_mode: str  # "reference" or "pairwise"
    reference_condition: str | None
    conditions: dict[str, Condition]
    feature_groups: dict[str, FeatureGroup]
    dark_mode: bool = False
    covariates: CovariateConfig | None = None
    comparisons: list[tuple[str, str]] | None = None
    #: Resolved DB-hierarchy closure ``{feature: [feature, *descendants]}`` for this
    #: config's featureset, supplied by the (DB-aware) consumer. When set, feature
    #: groups are expanded to whole hierarchy subtrees and unknown features error.
    #: ``None`` keeps the literal (non-hierarchy) behavior. karyoplot stays DB-agnostic:
    #: it receives this resolved map, never a hierarchy file.
    feature_descendants: dict[str, list[str]] | None = None
