"""Load sequence-annotation TSVs and compute feature values.

Ported from ``KaryoScope-BIR/scripts/feature_comparison_lib/data_loader.py``.
The dataclass types it consumes (:class:`~karyoplot.mpl.types.ComparisonConfig`,
:class:`~karyoplot.mpl.types.Condition`, :class:`~karyoplot.mpl.types.FeatureGroup`)
live in :mod:`karyoplot.mpl.types`.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from .types import ComparisonConfig, Condition, FeatureGroup


def _needed_columns(config: ComparisonConfig) -> list[str]:
    """Get list of all annotation columns needed for this config."""
    cols = {"sequence", "sequencing_approach"}
    for fg in config.feature_groups.values():
        cols.update(fg.get_columns(config.featureset, config.metric))
    return sorted(cols)


def load_annotations(config: ComparisonConfig) -> dict[str, pd.DataFrame]:
    """Load sequence annotation TSVs for all samples in all conditions.

    Only reads the columns needed for the configured feature groups. Missing
    columns (e.g. ``hsat1A`` absent from samples with no such reads) are
    filled with 0.

    Returns:
        Mapping ``{sample_name: DataFrame}``.
    """
    all_samples: list[str] = []
    for cond in config.conditions.values():
        all_samples.extend(cond.samples)

    needed = _needed_columns(config)
    data: dict[str, pd.DataFrame] = {}

    for sample in all_samples:
        filepath = Path(config.annotations_dir) / f"{sample}.sequence_annotations.tsv.gz"
        if not filepath.exists():
            print(f"  WARNING: not found: {filepath}")
            continue

        df_header = pd.read_csv(filepath, sep="\t", nrows=0, compression="gzip")
        available = [c for c in needed if c in df_header.columns]
        df = pd.read_csv(filepath, sep="\t", usecols=available, compression="gzip")

        for col in needed:
            if col not in df.columns and col != "sequence":
                df[col] = 0.0

        data[sample] = df
        print(f"  {sample}: {len(df)} reads ({len(available)}/{len(needed)} columns found)")

    return data


def compute_feature_values(
    df: pd.DataFrame,
    feature_groups: dict[str, FeatureGroup],
    featureset: str,
    metric: str,
) -> dict[str, pd.Series]:
    """Compute per-read feature values for all defined groups.

    For composite groups (``aggregation="sum"``), sums the constituent columns.
    For single-feature groups, returns the column directly.
    """
    result: dict[str, pd.Series] = {}
    for fg_name, fg in feature_groups.items():
        columns = fg.get_columns(featureset, metric)
        available = [c for c in columns if c in df.columns]
        if not available:
            result[fg_name] = pd.Series(0.0, index=df.index)
        elif fg.aggregation == "sum" and len(available) > 1:
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

        values = compute_feature_values(df, config.feature_groups, config.featureset, config.metric)

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

        values = compute_feature_values(df, config.feature_groups, config.featureset, config.metric)
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
