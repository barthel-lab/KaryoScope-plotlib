"""Statistical comparisons used by the heatmap / volcano / dot-strip / lollipop plots.

Ported from ``KaryoScope-BIR/scripts/feature_comparison_lib/statistics.py``.

Tests performed per feature group in :func:`compare_two_conditions`:

- Pooled Fisher exact (reads above threshold)
- Pooled Mann-Whitney U (continuous values)
- Per-sample Fisher exact + combined Fisher
- Sample-level Mann-Whitney (rates per sample)
- Log2 fold change, direction, consistency, rank
"""

from __future__ import annotations

import itertools
import logging

import numpy as np
import pandas as pd
from scipy.stats import combine_pvalues, fisher_exact, mannwhitneyu

from .data_loader import compute_feature_values, get_pooled_data
from .types import ComparisonConfig, Condition

logger = logging.getLogger(__name__)


def compare_two_conditions(
    annotations: dict[str, pd.DataFrame],
    cond_a: Condition,
    cond_b: Condition,
    config: ComparisonConfig,
) -> pd.DataFrame:
    """Run all statistical tests comparing condition A vs condition B.

    Returns:
        DataFrame with one row per feature group.
    """
    pooled_a = get_pooled_data(annotations, cond_a)
    pooled_b = get_pooled_data(annotations, cond_b)

    if pooled_a.empty or pooled_b.empty:
        logger.warning("empty data for %s or %s", cond_a.name, cond_b.name)
        return pd.DataFrame()

    values_a = compute_feature_values(
        pooled_a,
        config.feature_groups,
        config.featureset,
        config.metric,
        config.feature_descendants,
    )
    values_b = compute_feature_values(
        pooled_b,
        config.feature_groups,
        config.featureset,
        config.metric,
        config.feature_descendants,
    )

    stat_rows = []
    for fg_name, fg in config.feature_groups.items():
        va = values_a[fg_name]
        vb = values_b[fg_name]

        a_count = int((va > config.threshold).sum())
        a_total = len(pooled_a)
        a_rate = a_count / a_total * 100 if a_total > 0 else 0.0

        b_count = int((vb > config.threshold).sum())
        b_total = len(pooled_b)
        b_rate = b_count / b_total * 100 if b_total > 0 else 0.0

        # Pooled Fisher exact
        table = [[a_count, b_count], [a_total - a_count, b_total - b_count]]
        try:
            fisher_OR, fisher_p = fisher_exact(table, alternative="two-sided")
        except Exception:
            fisher_OR, fisher_p = float("nan"), 1.0

        # Pooled Mann-Whitney U
        try:
            _, mw_p = mannwhitneyu(va, vb, alternative="two-sided")
        except Exception:
            mw_p = 1.0

        # Per-sample rates
        a_sample_rates: list[float] = []
        for a_sample in cond_a.samples:
            if a_sample not in annotations:
                continue
            a_df = annotations[a_sample]
            a_vals_s = compute_feature_values(
                a_df, {fg_name: fg}, config.featureset, config.metric, config.feature_descendants
            )[fg_name]
            ac = int((a_vals_s > config.threshold).sum())
            at = len(a_df)
            a_sample_rates.append(ac / at * 100 if at > 0 else 0.0)

        # Per-sample Fisher + combined
        per_sample_pvals: list[float] = []
        per_sample_directions: list[str] = []
        b_sample_rates: list[float] = []

        for b_sample in cond_b.samples:
            if b_sample not in annotations:
                continue
            b_df = annotations[b_sample]
            b_vals = compute_feature_values(
                b_df, {fg_name: fg}, config.featureset, config.metric, config.feature_descendants
            )[fg_name]
            bc = int((b_vals > config.threshold).sum())
            bt = len(b_df)
            br = bc / bt * 100 if bt > 0 else 0.0
            b_sample_rates.append(br)

            t = [[a_count, bc], [a_total - a_count, bt - bc]]
            try:
                _, pp = fisher_exact(t, alternative="two-sided")
            except Exception:
                pp = 1.0
            per_sample_pvals.append(pp)

            d = "UP" if a_rate > br else "DN" if a_rate < br else "="
            per_sample_directions.append(d)

        n_sig = sum(1 for p in per_sample_pvals if p < 0.05)
        if per_sample_pvals:
            _, combined_p = combine_pvalues(per_sample_pvals, method="fisher")
        else:
            combined_p = 1.0

        # Sample-level Mann-Whitney
        try:
            _, sample_mw_p = mannwhitneyu(a_sample_rates, b_sample_rates, alternative="two-sided")
        except Exception:
            sample_mw_p = 1.0

        b_mean_rate = float(np.mean(b_sample_rates)) if b_sample_rates else b_rate

        # Log2 fold change (B / A)
        if b_mean_rate > 0 and a_rate > 0:
            log2fc = np.log2(b_mean_rate / a_rate)
        elif b_mean_rate > 0:
            log2fc = float("inf")
        elif a_rate > 0:
            log2fc = float("-inf")
        else:
            log2fc = 0.0

        if b_mean_rate > a_rate:
            direction = f"{cond_b.name}_UP"
        elif a_rate > b_mean_rate:
            direction = f"{cond_a.name}_UP"
        else:
            direction = "none"

        # Rank of condition A among all samples
        all_rates = [*b_sample_rates, a_rate]
        all_rates_sorted = sorted(all_rates)
        a_rank = all_rates_sorted.index(a_rate) + 1
        n_total_samples = len(all_rates)

        # Consistency
        non_eq = [d for d in per_sample_directions if d != "="]
        consistent = "consistent" if non_eq and all(d == non_eq[0] for d in non_eq) else "mixed"

        stat_rows.append(
            {
                "feature": fg_name,
                "feature_label": fg.label,
                f"{cond_a.name}_count": a_count,
                f"{cond_a.name}_total": a_total,
                f"{cond_a.name}_rate_pct": round(a_rate, 4),
                f"{cond_b.name}_count": b_count,
                f"{cond_b.name}_total": b_total,
                f"{cond_b.name}_rate_pct": round(b_rate, 4),
                f"{cond_b.name}_mean_rate_pct": round(b_mean_rate, 4),
                "log2FC": (
                    round(log2fc, 4) if not np.isinf(log2fc) else ("-inf" if log2fc < 0 else "inf")
                ),
                "direction": direction,
                f"{cond_a.name}_rank_of_{n_total_samples}": a_rank,
                "consistency": consistent,
                "pooled_fisher_p": fisher_p,
                "pooled_fisher_OR": (
                    round(fisher_OR, 4)
                    if not np.isinf(fisher_OR) and not np.isnan(fisher_OR)
                    else str(fisher_OR)
                ),
                "mann_whitney_p": mw_p,
                "sample_mann_whitney_p": sample_mw_p,
                "n_individual_sig": n_sig,
                "combined_fisher_p": combined_p,
            }
        )

    return pd.DataFrame(stat_rows)


def apply_fdr(stats_df: pd.DataFrame, p_columns: list[str] | None = None) -> pd.DataFrame:
    """Apply Benjamini-Hochberg FDR correction to p-value columns.

    Args:
        stats_df: DataFrame with statistical results.
        p_columns: P-value columns to correct. If ``None``, auto-detects
            columns ending in ``_p``.
    """
    if stats_df.empty:
        return stats_df

    df = stats_df.copy()

    if p_columns is None:
        p_columns = [c for c in df.columns if c.endswith("_p")]

    for col in p_columns:
        if col not in df.columns:
            continue
        pvals = pd.to_numeric(df[col], errors="coerce").fillna(1.0).values
        n = len(pvals)
        if n == 0:
            continue

        ranked = np.argsort(pvals)
        fdr = np.ones(n)
        for i, idx in enumerate(ranked):
            fdr[idx] = pvals[idx] * n / (i + 1)

        # Enforce monotonicity
        for i in range(n - 2, -1, -1):
            rank_idx = ranked[i]
            next_rank_idx = ranked[i + 1]
            if fdr[rank_idx] > fdr[next_rank_idx]:
                fdr[rank_idx] = fdr[next_rank_idx]

        fdr = np.minimum(fdr, 1.0)
        df[f"{col}_fdr"] = fdr

    return df


def run_all_comparisons(
    annotations: dict[str, pd.DataFrame],
    config: ComparisonConfig,
) -> dict[str, pd.DataFrame]:
    """Run comparisons based on ``config.comparison_mode``.

    Returns:
        Mapping ``{comparison_label: stats_df}``.
    """
    results: dict[str, pd.DataFrame] = {}
    conds = list(config.conditions.values())

    if config.comparison_mode == "reference":
        ref_name = config.reference_condition
        if ref_name is None:
            ref_name = conds[0].name
        ref_cond = config.conditions[ref_name]

        for cond in conds:
            if cond.name == ref_name:
                continue
            label = f"{ref_name}_vs_{cond.name}"
            logger.info("Comparing %s vs %s", ref_cond.label, cond.label)
            stats = compare_two_conditions(annotations, ref_cond, cond, config)
            stats = apply_fdr(stats)
            results[label] = stats

    elif config.comparison_mode == "pairwise":
        if config.comparisons:
            pairs = [(config.conditions[a], config.conditions[b]) for a, b in config.comparisons]
        else:
            pairs = list(itertools.combinations(conds, 2))
        for cond_a, cond_b in pairs:
            label = f"{cond_a.name}_vs_{cond_b.name}"
            logger.info("Comparing %s vs %s", cond_a.label, cond_b.label)
            stats = compare_two_conditions(annotations, cond_a, cond_b, config)
            stats = apply_fdr(stats)
            results[label] = stats

    return results
