"""Volcano, dot-strip, and lollipop comparison plots.

Ported from ``KaryoScope-BIR/scripts/feature_comparison_lib/visualizations.py``.

Public API:
    plot_volcano(stats_df, config, output_prefix, cond_a_name, cond_b_name)
    plot_dot_strip(rates_df, stats_df, config, output_prefix, cond_a_name, cond_b_name)
    plot_lollipop(rates_df, stats_df, config, output_prefix, cond_a_name, cond_b_name)
    generate_all_plots(rates_df, all_stats, config, output_prefix)

The dispatcher :func:`generate_all_plots` calls
:func:`karyoplot.mpl.heatmap.plot_heatmap` for the cross-condition heatmap,
then iterates the per-comparison plots.
"""

from __future__ import annotations

import logging

import numpy as np
import pandas as pd

from .style import apply_default_style, fg_color, save_fig
from .types import ComparisonConfig

logger = logging.getLogger(__name__)


def _arcsin_sqrt(pct):
    """Arcsin-square-root transform for percentage values (0-100)."""
    return np.arcsin(np.sqrt(np.clip(pct / 100.0, 0, 1)))


def plot_volcano(
    stats_df: pd.DataFrame,
    config: ComparisonConfig,
    output_prefix: str,
    cond_a_name: str,
    cond_b_name: str,
) -> tuple[str, str] | None:
    """Volcano plot: log2FC vs -log10(Fisher p-value) for all feature groups.

    Returns ``(svg_path, png_path)`` on success, ``None`` if ``stats_df`` is empty.
    """
    if stats_df.empty:
        return None

    import matplotlib.pyplot as plt
    from adjustText import adjust_text

    fig, ax = plt.subplots(figsize=(7, 6))

    fc_vals = []
    p_vals = []
    labels = []
    colors = []

    for _, row in stats_df.iterrows():
        fc = row["log2FC"]
        if isinstance(fc, str):
            fc = float(fc) if fc not in ("inf", "-inf") else (5.0 if fc == "inf" else -5.0)
        p = row["pooled_fisher_p"]
        if p <= 0:
            p = 1e-300

        fc_vals.append(fc)
        p_vals.append(-np.log10(p))
        labels.append(row["feature_label"])
        colors.append(config.feature_groups[row["feature"]].color)

    fc_vals = np.array(fc_vals)
    p_vals = np.array(p_vals)

    line_color = "#888888"
    ax.axhline(-np.log10(0.05), color=line_color, linestyle="--", linewidth=0.8, alpha=0.5)
    ax.axvline(0, color=line_color, linestyle="--", linewidth=0.8, alpha=0.5)

    edge_c = fg_color(config.dark_mode)
    for i in range(len(fc_vals)):
        ax.scatter(
            fc_vals[i], p_vals[i], color=colors[i], s=80, edgecolors=edge_c, linewidth=0.5, zorder=3
        )

    texts = [
        ax.text(fc_vals[i], p_vals[i], labels[i], fontsize=9, ha="center", va="center")
        for i in range(len(fc_vals))
    ]

    adjust_text(
        texts,
        x=fc_vals,
        y=p_vals,
        ax=ax,
        force_text=(1.0, 2.0),
        force_points=(2.0, 2.0),
        force_explode=(1.5, 2.0),
        expand=(2.0, 2.0),
        ensure_inside_axes=True,
    )

    # Connector lines for displaced labels
    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()
    marker_radius_px = np.sqrt(80) / 72 * fig.get_dpi()
    min_dist = marker_radius_px * 3
    for i, txt in enumerate(texts):
        pt_disp = ax.transData.transform((fc_vals[i], p_vals[i]))
        bbox = txt.get_window_extent(renderer)
        cx = max(bbox.x0, min(pt_disp[0], bbox.x1))
        cy = max(bbox.y0, min(pt_disp[1], bbox.y1))
        dist = np.hypot(cx - pt_disp[0], cy - pt_disp[1])
        if dist > min_dist:
            ax.annotate(
                "",
                xy=(fc_vals[i], p_vals[i]),
                xytext=txt.get_position(),
                arrowprops=dict(arrowstyle="-", color=edge_c, lw=0.5, shrinkA=5, shrinkB=3),
            )

    cond_a = config.conditions[cond_a_name]
    cond_b = config.conditions[cond_b_name]
    ax.set_xlabel(f"log₂(fold change)\n{cond_a.label} enriched  |  {cond_b.label} enriched")
    ax.set_ylabel("−log₁₀(p-value)")  # noqa: RUF001 — display label: minus sign pairs with log₂ above
    ax.set_title(config.name)

    max_fc = max(abs(fc_vals.min()), abs(fc_vals.max()), 1)
    ax.set_xlim(-max_fc * 1.3, max_fc * 1.3)

    fig.tight_layout()
    return save_fig(fig, output_prefix, "volcano")


def plot_dot_strip(
    rates_df: pd.DataFrame,
    stats_df: pd.DataFrame,
    config: ComparisonConfig,
    output_prefix: str,
    cond_a_name: str,
    cond_b_name: str,
) -> tuple[str, str]:
    """Strip plot of individual sample rates per feature group.

    Uses arcsin-sqrt transformed y-axis with original percentage tick labels.
    """
    import matplotlib.patches as mpatches
    import matplotlib.pyplot as plt

    cond_a = config.conditions[cond_a_name]
    cond_b = config.conditions[cond_b_name]
    fg_names = list(config.feature_groups.keys())
    fg_labels = [config.feature_groups[fg].label for fg in fg_names]
    n_features = len(fg_names)

    a_rates = rates_df[rates_df["condition"] == cond_a_name]
    b_rates = rates_df[rates_df["condition"] == cond_b_name]

    fig, ax = plt.subplots(figsize=(max(7, n_features * 0.75), 5))
    x = np.arange(n_features)
    offset = 0.15
    edge_c = fg_color(config.dark_mode)
    rng = np.random.default_rng(0)  # fixed seed -> reproducible jitter across renders

    for i, fg in enumerate(fg_names):
        a_vals = _arcsin_sqrt(a_rates[f"{fg}_rate"].values)
        b_vals = _arcsin_sqrt(b_rates[f"{fg}_rate"].values)

        a_x = np.full(len(a_vals), x[i] - offset) + rng.uniform(-0.06, 0.06, len(a_vals))
        b_x = np.full(len(b_vals), x[i] + offset) + rng.uniform(-0.06, 0.06, len(b_vals))

        ax.scatter(
            a_x,
            a_vals,
            color=cond_a.color,
            s=40,
            edgecolors=edge_c,
            linewidth=0.5,
            zorder=3,
            alpha=0.8,
        )
        ax.scatter(
            b_x,
            b_vals,
            color=cond_b.color,
            s=40,
            edgecolors=edge_c,
            linewidth=0.5,
            zorder=3,
            alpha=0.8,
        )

        ax.plot(
            [x[i] - offset - 0.1, x[i] - offset + 0.1],
            [a_vals.mean(), a_vals.mean()],
            color=cond_a.color,
            linewidth=2,
            zorder=4,
        )
        ax.plot(
            [x[i] + offset - 0.1, x[i] + offset + 0.1],
            [b_vals.mean(), b_vals.mean()],
            color=cond_b.color,
            linewidth=2,
            zorder=4,
        )

    if not stats_df.empty:
        bracket_color = fg_color(config.dark_mode)
        for i, fg in enumerate(fg_names):
            row = stats_df[stats_df["feature"] == fg]
            if row.empty:
                continue
            p = row["sample_mann_whitney_p"].values[0]
            label = "p = NS" if p > 0.05 else f"p = {p:.2e}"

            a_vals = _arcsin_sqrt(a_rates[f"{fg}_rate"].values)
            b_vals = _arcsin_sqrt(b_rates[f"{fg}_rate"].values)
            y_top = max(np.nanmax(a_vals), np.nanmax(b_vals))
            y_range = ax.get_ylim()[1] - ax.get_ylim()[0] if ax.get_ylim()[1] > 0 else 1
            tick_h = y_range * 0.02
            bracket_y = y_top + y_range * 0.04

            x_left, x_right = x[i] - offset, x[i] + offset
            ax.plot(
                [x_left, x_left],
                [bracket_y, bracket_y + tick_h],
                color=bracket_color,
                linewidth=0.8,
                zorder=5,
            )
            ax.plot(
                [x_right, x_right],
                [bracket_y, bracket_y + tick_h],
                color=bracket_color,
                linewidth=0.8,
                zorder=5,
            )
            ax.plot(
                [x_left, x_right],
                [bracket_y + tick_h, bracket_y + tick_h],
                color=bracket_color,
                linewidth=0.8,
                zorder=5,
            )

            ax.text(
                x[i],
                bracket_y + tick_h + y_range * 0.01,
                label,
                ha="center",
                va="bottom",
                fontsize=7,
                fontstyle="italic",
                color=bracket_color,
            )

    ax.set_xticks(x)
    ax.set_xticklabels(fg_labels, rotation=45, ha="right")
    ax.set_xlim(-0.5, n_features - 0.5)
    ax.set_ylabel("% reads above threshold (arcsin√ scale)")
    ax.set_title(config.name)
    ax.set_ylim(bottom=0)

    tick_pcts = [0, 0.5, 2, 5, 10, 20, 50, 75, 100]
    tick_transformed = [_arcsin_sqrt(p) for p in tick_pcts]
    y_top = ax.get_ylim()[1]
    tick_pcts = [p for p, t in zip(tick_pcts, tick_transformed, strict=False) if t <= y_top * 1.05]
    tick_transformed = [t for t in tick_transformed if t <= y_top * 1.05]
    ax.set_yticks(tick_transformed)
    ax.set_yticklabels([f"{p:g}%" for p in tick_pcts])

    handles = [
        mpatches.Patch(color=cond_a.color, label=cond_a.label),
        mpatches.Patch(color=cond_b.color, label=cond_b.label),
    ]
    ax.legend(handles=handles, loc="upper right", framealpha=0.8)

    fig.tight_layout()
    return save_fig(fig, output_prefix, "dot_strip")


def plot_lollipop(
    rates_df: pd.DataFrame,
    stats_df: pd.DataFrame,
    config: ComparisonConfig,
    output_prefix: str,
    cond_a_name: str,
    cond_b_name: str,
) -> tuple[str, str]:
    """Paired lollipop / dumbbell plot comparing two conditions per feature.

    Horizontal layout: features on y-axis, arcsin-sqrt percentage on x-axis.
    """
    import matplotlib.patches as mpatches
    import matplotlib.pyplot as plt

    cond_a = config.conditions[cond_a_name]
    cond_b = config.conditions[cond_b_name]
    fg_names = list(config.feature_groups.keys())
    fg_labels = [config.feature_groups[fg].label for fg in fg_names]
    n_features = len(fg_names)

    a_rates = rates_df[rates_df["condition"] == cond_a_name]
    b_rates = rates_df[rates_df["condition"] == cond_b_name]

    fig, ax = plt.subplots(figsize=(7, max(4, n_features * 0.38)))
    y = np.arange(n_features)
    edge_c = fg_color(config.dark_mode)

    row_x_min = np.full(n_features, np.inf)
    row_x_max = np.full(n_features, -np.inf)

    for i, fg in enumerate(fg_names):
        a_vals = a_rates[f"{fg}_rate"].values
        b_vals = b_rates[f"{fg}_rate"].values
        a_mean = _arcsin_sqrt(a_vals.mean())
        b_mean = _arcsin_sqrt(b_vals.mean())

        all_x = [a_mean, b_mean]

        ax.plot([a_mean, b_mean], [y[i], y[i]], color=edge_c, linewidth=1.0, zorder=2, alpha=0.5)

        if len(a_vals) > 1:
            a_t = _arcsin_sqrt(a_vals)
            all_x.extend(a_t)
            ax.scatter(
                a_t,
                np.full(len(a_t), y[i]),
                color=cond_a.color,
                s=20,
                edgecolors=edge_c,
                linewidth=0.3,
                zorder=3,
                alpha=0.5,
            )
        if len(b_vals) > 1:
            b_t = _arcsin_sqrt(b_vals)
            all_x.extend(b_t)
            ax.scatter(
                b_t,
                np.full(len(b_t), y[i]),
                color=cond_b.color,
                s=20,
                edgecolors=edge_c,
                linewidth=0.3,
                zorder=3,
                alpha=0.5,
            )

        ax.scatter(
            a_mean, y[i], color=cond_a.color, s=60, edgecolors=edge_c, linewidth=0.5, zorder=4
        )
        ax.scatter(
            b_mean, y[i], color=cond_b.color, s=60, edgecolors=edge_c, linewidth=0.5, zorder=4
        )

        row_x_min[i] = min(all_x)
        row_x_max[i] = max(all_x)

    ax.set_yticks(y)
    ax.set_yticklabels(fg_labels, fontsize=9)
    ax.set_xlabel("% reads above threshold (arcsin√ scale)")
    ax.set_title(config.name)
    ax.set_xlim(left=0)
    ax.invert_yaxis()

    tick_pcts = [0, 0.5, 2, 5, 10, 20, 50, 75, 100]
    tick_transformed = [_arcsin_sqrt(p) for p in tick_pcts]
    x_top = ax.get_xlim()[1]
    tick_pcts = [p for p, t in zip(tick_pcts, tick_transformed, strict=False) if t <= x_top * 1.05]
    tick_transformed = [t for t in tick_transformed if t <= x_top * 1.05]
    ax.set_xticks(tick_transformed)
    ax.set_xticklabels([f"{p:g}%" for p in tick_pcts])

    handles = [
        mpatches.Patch(color=cond_a.color, label=cond_a.label),
        mpatches.Patch(color=cond_b.color, label=cond_b.label),
    ]
    ax.legend(handles=handles, loc="lower right", framealpha=0.8)

    fig.tight_layout()

    if not stats_df.empty:
        text_color = fg_color(config.dark_mode)
        pad = (ax.get_xlim()[1] - ax.get_xlim()[0]) * 0.015
        fig.canvas.draw()
        renderer = fig.canvas.get_renderer()
        ax_bbox = ax.get_window_extent(renderer)

        for i, fg in enumerate(fg_names):
            row = stats_df[stats_df["feature"] == fg]
            if row.empty:
                continue
            p = row["pooled_fisher_p"].values[0]
            label = f"p = {p:.2e}" if p <= 0.05 else "p = NS"

            txt = ax.text(
                row_x_max[i] + pad,
                y[i],
                label,
                ha="left",
                va="center",
                fontsize=9,
                fontstyle="italic",
                color=text_color,
                zorder=5,
            )
            fig.canvas.draw()
            txt_bbox = txt.get_window_extent(renderer)
            if txt_bbox.x1 > ax_bbox.x1:
                txt.remove()
                ax.text(
                    row_x_min[i] - pad,
                    y[i],
                    label,
                    ha="right",
                    va="center",
                    fontsize=9,
                    fontstyle="italic",
                    color=text_color,
                    zorder=5,
                )

    return save_fig(fig, output_prefix, "lollipop")


def generate_all_plots(
    rates_df: pd.DataFrame,
    all_stats: dict[str, pd.DataFrame],
    config: ComparisonConfig,
    output_prefix: str,
) -> None:
    """Generate all visualizations for all comparisons.

    Calls :func:`karyoplot.mpl.heatmap.plot_heatmap` once for the
    cross-condition heatmap, then iterates volcano/dot-strip/lollipop
    per comparison.
    """
    from .heatmap import plot_heatmap

    apply_default_style(config.dark_mode)

    logger.info("Generating heatmap")
    plot_heatmap(rates_df, config, output_prefix)

    for comp_label, stats_df in all_stats.items():
        parts = comp_label.split("_vs_")
        if len(parts) != 2:
            continue
        cond_a_name, cond_b_name = parts
        comp_prefix = f"{output_prefix}.{comp_label}"
        logger.info("Generating plots for %s", comp_label)
        plot_volcano(stats_df, config, comp_prefix, cond_a_name, cond_b_name)
        plot_dot_strip(rates_df, stats_df, config, comp_prefix, cond_a_name, cond_b_name)
        plot_lollipop(rates_df, stats_df, config, comp_prefix, cond_a_name, cond_b_name)
