"""Load sequence-annotation TSVs and compute feature values.

Ported from ``KaryoScope-BIR/scripts/feature_comparison_lib/data_loader.py``.
The dataclass types it consumes (:class:`~karyoplot.mpl.types.ComparisonConfig`,
:class:`~karyoplot.mpl.types.Condition`, :class:`~karyoplot.mpl.types.FeatureGroup`)
live in :mod:`karyoplot.mpl.types`.
"""

from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd

from .types import ComparisonConfig, Condition, FeatureGroup

logger = logging.getLogger(__name__)


def _needed_columns(config: ComparisonConfig) -> list[str]:
    """Feature columns needed for this config, plus the read-id key ``sequence``."""
    cols = {"sequence"}
    for fg in config.feature_groups.values():
        cols.update(fg.get_columns(config.featureset, config.metric, config.feature_descendants))
    return sorted(cols)


def load_annotations(config: ComparisonConfig) -> dict[str, pd.DataFrame]:
    """Load the per-read feature table for every sample in every condition.

    Consumes the wide per-read matrix from ``build-feature-matrix`` (read-id key
    ``seq_id``) or the legacy ``sequence_annotations`` (key ``sequence``); the key
    is normalized to ``sequence``. Feature-name validity is enforced upstream at
    expansion (:meth:`FeatureGroup.get_columns` raises on a non-hierarchy feature),
    so a *valid* feature column that is merely absent from a sample (0 reads of it)
    is filled with 0 here rather than treated as an error.

    Returns:
        Mapping ``{sample_name: DataFrame}`` (each has a ``sequence`` column).
    """
    all_samples: list[str] = []
    for cond in config.conditions.values():
        all_samples.extend(cond.samples)

    feature_cols = [c for c in _needed_columns(config) if c != "sequence"]
    data: dict[str, pd.DataFrame] = {}

    for sample in all_samples:
        filepath = Path(config.annotations_dir) / f"{sample}.sequence_annotations.tsv.gz"
        if not filepath.exists():
            logger.warning("not found: %s", filepath)
            continue

        header = pd.read_csv(filepath, sep="\t", nrows=0, compression="gzip")
        # Read-id key: build-feature-matrix uses ``seq_id``; the legacy table uses
        # ``sequence``. Normalize to ``sequence``.
        key = "seq_id" if "seq_id" in header.columns else "sequence"
        usecols = [c for c in feature_cols if c in header.columns] + [key]
        df = pd.read_csv(filepath, sep="\t", usecols=usecols, compression="gzip")
        if key != "sequence":
            df = df.rename(columns={key: "sequence"})

        n_present = sum(1 for c in feature_cols if c in df.columns)
        for c in feature_cols:  # valid-but-absent feature (0 reads) -> 0
            if c not in df.columns:
                df[c] = 0.0

        data[sample] = df
        logger.info(
            "%s: %d reads (%d/%d feature columns present)",
            sample,
            len(df),
            n_present,
            len(feature_cols),
        )

    return data


def compute_feature_values(
    df: pd.DataFrame,
    feature_groups: dict[str, FeatureGroup],
    featureset: str,
    metric: str,
    descendants: dict[str, list[str]] | None = None,
) -> dict[str, pd.Series]:
    """Compute per-read feature values for all defined groups.

    Each group's value is the sum of its constituent feature columns present in
    ``df`` (hierarchy-expanded when ``descendants`` is given); absent columns are 0.
    """
    result: dict[str, pd.Series] = {}
    for fg_name, fg in feature_groups.items():
        columns = fg.get_columns(featureset, metric, descendants)
        available = [c for c in columns if c in df.columns]
        if not available:
            result[fg_name] = pd.Series(0.0, index=df.index)
        elif descendants is not None or (fg.aggregation == "sum" and len(available) > 1):
            result[fg_name] = df[available].fillna(0).sum(axis=1)
        else:
            result[fg_name] = df[available[0]].fillna(0)
    return result


def compute_per_sample_rates(
    annotations: dict[str, pd.DataFrame],
    config: ComparisonConfig,
) -> pd.DataFrame:
    """Compute per-sample rates (% reads above threshold) for each feature group.

    Returns:
        DataFrame with columns: ``sample, condition, condition_label,
        condition_color, total_reads, {feature}_count, {feature}_rate``.
    """
    sample_to_cond: dict[str, Condition] = {}
    for cond in config.conditions.values():
        for s in cond.samples:
            sample_to_cond[s] = cond

    rows = []
    for sample, df in annotations.items():
        cond = sample_to_cond.get(sample)
        if cond is None:
            continue

        values = compute_feature_values(
            df,
            config.feature_groups,
            config.featureset,
            config.metric,
            config.feature_descendants,
        )

        row = {
            "sample": sample,
            "condition": cond.name,
            "condition_label": cond.label,
            "condition_color": cond.color,
            "total_reads": len(df),
        }

        for fg_name, vals in values.items():
            above = (vals > config.threshold).sum()
            row[f"{fg_name}_count"] = int(above)
            row[f"{fg_name}_rate"] = round(above / len(df) * 100, 4) if len(df) > 0 else 0.0

        rows.append(row)

    return pd.DataFrame(rows)


def compute_read_level_table(
    annotations: dict[str, pd.DataFrame],
    config: ComparisonConfig,
) -> pd.DataFrame:
    """Build a read-level table of reads exceeding the threshold per feature group."""
    sample_to_cond: dict[str, Condition] = {}
    for cond in config.conditions.values():
        for s in cond.samples:
            sample_to_cond[s] = cond

    rows = []
    for sample, df in annotations.items():
        cond = sample_to_cond.get(sample)
        if cond is None:
            continue

        values = compute_feature_values(
            df,
            config.feature_groups,
            config.featureset,
            config.metric,
            config.feature_descendants,
        )
        seq_approach = df["sequencing_approach"] if "sequencing_approach" in df.columns else None

        for fg_name, vals in values.items():
            mask = vals > config.threshold
            if not mask.any():
                continue
            hits = df.loc[mask]
            fg_label = config.feature_groups[fg_name].label
            for idx in hits.index:
                raw_id = hits.at[idx, "sequence"]
                rid = raw_id.split(";")[0] if ";" in raw_id else raw_id
                rows.append(
                    {
                        "read_id": rid,
                        "group": fg_label,
                        "subgroup": cond.label,
                        "sample": sample,
                        "sequencing_approach": seq_approach.at[idx]
                        if seq_approach is not None
                        else "",
                    }
                )

    return pd.DataFrame(
        rows,
        columns=["read_id", "group", "subgroup", "sample", "sequencing_approach"],
    )


def get_pooled_data(
    annotations: dict[str, pd.DataFrame],
    condition: Condition,
) -> pd.DataFrame:
    """Concatenate all sample DataFrames for a given condition."""
    dfs = [annotations[s] for s in condition.samples if s in annotations]
    if not dfs:
        return pd.DataFrame()
    return pd.concat(dfs, ignore_index=True)
