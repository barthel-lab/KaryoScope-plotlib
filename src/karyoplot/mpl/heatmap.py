"""Per-sample clustered heatmap with optional covariate annotation.

Ported from ``KaryoScope-BIR/scripts/feature_comparison_lib/visualizations.py``
(``plot_heatmap`` and supporting clustering / covariate helpers).

Public API:
    plot_heatmap(rates_df, config, output_prefix)

The clustering helpers (:func:`fix_leaf_ordering`, :func:`push_leaves_to_edge`,
:func:`cluster_and_reorder`) are also exported for reuse in other plotting code.
"""

from __future__ import annotations

from typing import Optional

import numpy as np
import pandas as pd

from .style import fg_color, save_fig
from .types import ComparisonConfig, CovariateConfig

_DENDRO_COLOR_LIGHT = "black"
_DENDRO_COLOR_DARK = "white"


# ---------------------------------------------------------------------------
# Clustering helpers (also useful for KaryoScope_cluster_analysis migrations)
# ---------------------------------------------------------------------------

def fix_leaf_ordering(Z, X):
    """Greedy flip pass to fix sub-optimal scipy ``optimal_leaf_ordering`` results.

    At each internal node, tries swapping left/right children and keeps the
    swap if it reduces the total adjacent-leaf distance. Iterates until no
    further improvement is found.
    """
    from scipy.cluster.hierarchy import leaves_list
    from scipy.spatial.distance import pdist, squareform

    Z = Z.copy()
    D = squareform(pdist(X, metric="euclidean"))

    def _adj_cost(order):
        return sum(D[order[i], order[i + 1]] for i in range(len(order) - 1))

    improved = True
    while improved:
        improved = False
        for i in range(Z.shape[0]):
            cur_cost = _adj_cost(leaves_list(Z))
            Z[i, 0], Z[i, 1] = Z[i, 1], Z[i, 0]
            new_cost = _adj_cost(leaves_list(Z))
            if new_cost < cur_cost:
                improved = True
            else:
                Z[i, 0], Z[i, 1] = Z[i, 1], Z[i, 0]
    return Z


def push_leaves_to_edge(Z, target_indices, n_leaves, bottom: bool = True):
    """Flip dendrogram nodes so target leaves end up at the bottom (or top).

    Walks from root to leaves; at each node whose subtrees split the
    targets from non-targets, ensures the target-containing subtree is on
    the right (bottom) or left (top). Only flips nodes where one child
    has targets and the other doesn't — never reorders within a purely
    target subtree.
    """
    Z = Z.copy()
    target_set = set(target_indices)

    def _get_leaves(node_id):
        if node_id < n_leaves:
            return {node_id}
        row = int(node_id - n_leaves)
        return _get_leaves(int(Z[row, 0])) | _get_leaves(int(Z[row, 1]))

    def _fix(node_id):
        if node_id < n_leaves:
            return
        row = int(node_id - n_leaves)
        left_id, right_id = int(Z[row, 0]), int(Z[row, 1])
        left_has = bool(_get_leaves(left_id) & target_set)
        right_has = bool(_get_leaves(right_id) & target_set)

        if left_has and not right_has:
            if bottom:
                Z[row, 0], Z[row, 1] = Z[row, 1], Z[row, 0]
            _fix(int(Z[row, 1]) if bottom else int(Z[row, 0]))
        elif right_has and not left_has:
            if not bottom:
                Z[row, 0], Z[row, 1] = Z[row, 1], Z[row, 0]
            _fix(int(Z[row, 1]) if bottom else int(Z[row, 0]))
        else:
            _fix(left_id)
            _fix(right_id)

    _fix(n_leaves + Z.shape[0] - 1)
    return Z


def cluster_and_reorder(
    z_matrix, raw_matrix, sample_labels, cond_colors, fg_labels,
    cov_df=None, reference_samples=None, display_labels=None,
):
    """Hierarchical (Ward) row + column clustering with optimal leaf ordering.

    Returns the reordered arrays plus the row/column linkage matrices.
    """
    from scipy.cluster.hierarchy import dendrogram, linkage, optimal_leaf_ordering

    row_link = linkage(z_matrix, method="ward", metric="euclidean")
    row_link = optimal_leaf_ordering(row_link, z_matrix)
    row_link = fix_leaf_ordering(row_link, z_matrix)

    if reference_samples is not None:
        sample_list = list(sample_labels)
        ref_indices = [sample_list.index(s) for s in reference_samples
                       if s in sample_list]
        if ref_indices:
            row_link = push_leaves_to_edge(
                row_link, ref_indices, len(sample_labels), bottom=True
            )

    row_order = dendrogram(row_link, no_plot=True)["leaves"]

    col_link = linkage(z_matrix.T, method="ward", metric="euclidean")
    col_link = optimal_leaf_ordering(col_link, z_matrix.T)
    col_link = fix_leaf_ordering(col_link, z_matrix.T)
    col_order = dendrogram(col_link, no_plot=True)["leaves"]

    z_matrix = z_matrix[np.ix_(row_order, col_order)]
    raw_matrix = raw_matrix[np.ix_(row_order, col_order)]
    sample_labels = sample_labels[row_order]
    cond_colors = cond_colors[row_order]
    if display_labels is not None:
        display_labels = display_labels[row_order]
    fg_labels = [fg_labels[i] for i in col_order]
    if cov_df is not None:
        cov_df = cov_df.iloc[row_order].reset_index(drop=True)

    return (z_matrix, raw_matrix, sample_labels, cond_colors, fg_labels,
            cov_df, row_link, col_link, display_labels)


def _style_dendro_ax(ax, orientation: str = "top") -> None:
    ax.set_xticks([])
    ax.set_yticks([])
    for spine in ax.spines.values():
        spine.set_visible(False)


# ---------------------------------------------------------------------------
# Covariate panel helpers
# ---------------------------------------------------------------------------

def _load_covariate_data(
    cov_config: CovariateConfig,
    sample_labels: np.ndarray,
) -> Optional[pd.DataFrame]:
    """Load covariate file and align to sample order. Returns ``None`` on failure."""
    try:
        cov_df = pd.read_csv(cov_config.file, sep="\t", dtype=str)
    except Exception as e:
        print(f"  Warning: could not load covariate file {cov_config.file}: {e}")
        return None

    cov_df = cov_df.set_index(cov_config.id_column)
    col_names = list(cov_config.columns.keys())
    return cov_df.reindex(sample_labels)[col_names]


def _draw_covariate_panel(
    ax,
    cov_df: pd.DataFrame,
    cov_config: CovariateConfig,
    dark_mode: bool = False,
    sample_labels: Optional[np.ndarray] = None,
    cond_colors: Optional[np.ndarray] = None,
) -> None:
    """Draw the covariate annotation panel left of the heatmap."""
    import matplotlib.cm as mcm
    import matplotlib.colors as mcolors
    import matplotlib.pyplot as plt

    n_samples, n_covs = cov_df.shape
    fg_c = fg_color(dark_mode)

    for ci, col_name in enumerate(cov_df.columns):
        cov_col = cov_config.columns[col_name]

        if cov_col.type == "continuous":
            raw_vals = pd.to_numeric(cov_df[col_name], errors="coerce")
            valid = raw_vals.dropna()
            if len(valid) > 0:
                vmin, vmax = valid.min(), valid.max()
                if vmax == vmin:
                    vmax = vmin + 1
            else:
                vmin, vmax = 0, 1
            cmap = mcm.get_cmap(cov_col.cmap)

            for ri in range(n_samples):
                val = raw_vals.iloc[ri]
                if pd.isna(val):
                    color, label = "none", ""
                else:
                    norm_val = (val - vmin) / (vmax - vmin)
                    color = mcolors.to_hex(cmap(norm_val))
                    label = str(int(val)) if val == int(val) else f"{val:.1f}"
                ax.add_patch(plt.Rectangle(
                    (ci, ri - 0.5), 1, 1,
                    facecolor=color, edgecolor=fg_c, linewidth=0.5,
                ))
                if label:
                    r, g, b = mcolors.to_rgb(color)
                    lum = 0.299 * r + 0.587 * g + 0.114 * b
                    text_color = "black" if lum > 0.5 else "white"
                    ax.text(ci + 0.5, ri, label,
                            ha="center", va="center",
                            fontsize=7, color=text_color, fontweight="bold")
        else:
            for ri in range(n_samples):
                raw_val = cov_df.iloc[ri, ci]
                if pd.isna(raw_val) or raw_val == "NA":
                    color, label = "none", ""
                elif cov_col.values and raw_val in cov_col.values:
                    cv = cov_col.values[raw_val]
                    color, label = cv.color, cv.label
                else:
                    color, label = "none", str(raw_val)
                ax.add_patch(plt.Rectangle(
                    (ci, ri - 0.5), 1, 1,
                    facecolor=color, edgecolor=fg_c, linewidth=0.5,
                ))
                if label:
                    r, g, b = mcolors.to_rgb(color)
                    lum = 0.299 * r + 0.587 * g + 0.114 * b
                    text_color = "black" if lum > 0.5 else "white"
                    ax.text(ci + 0.5, ri, label,
                            ha="center", va="center",
                            fontsize=7, color=text_color, fontweight="bold")

    ax.set_xlim(0, n_covs)
    ax.set_ylim(-0.5, n_samples - 0.5)
    ax.invert_yaxis()
    ax.set_xticks([i + 0.5 for i in range(n_covs)])
    ax.set_xticklabels(
        [cov_config.columns[c].label for c in cov_df.columns],
        rotation=45, ha="right", fontsize=8,
    )

    if sample_labels is not None:
        ax.set_yticks(range(len(sample_labels)))
        ax.set_yticklabels(sample_labels, fontsize=8)
        ax.yaxis.set_ticks_position("left")
        if cond_colors is not None:
            for label_obj, color in zip(ax.get_yticklabels(), cond_colors):
                label_obj.set_color(color)
    else:
        ax.set_yticks([])

    for spine in ax.spines.values():
        spine.set_visible(False)


def _draw_covariate_legends(fig, ax_cov, cov_df, cov_config, dark_mode: bool = False) -> None:
    """Draw per-covariate legends below the covariate panel."""
    import matplotlib.cm as mcm
    import matplotlib.colors as mcolors
    import matplotlib.pyplot as plt

    text_color = fg_color(dark_mode)

    bbox = ax_cov.get_position()
    x_start = bbox.x0
    x_end = bbox.x1
    y_cursor = bbox.y0 - 0.03

    for col_name in cov_df.columns:
        cov_col = cov_config.columns[col_name]

        if cov_col.type == "continuous":
            raw_vals = pd.to_numeric(cov_df[col_name], errors="coerce")
            valid = raw_vals.dropna()
            vmin = valid.min() if len(valid) > 0 else 0
            vmax = valid.max() if len(valid) > 0 else 1

            fig.text(x_start, y_cursor, f"{cov_col.label}:",
                     fontsize=7, fontweight="bold", color=text_color,
                     va="top", ha="left", transform=fig.transFigure)

            cbar_height = 0.008
            cbar_width = (x_end - x_start) * 0.7
            cbar_left = x_start + (x_end - x_start) * 0.02
            cbar_bottom = y_cursor - 0.015
            cbar_ax = fig.add_axes([cbar_left, cbar_bottom, cbar_width, cbar_height])
            cmap = mcm.get_cmap(cov_col.cmap)
            norm = mcolors.Normalize(vmin=vmin, vmax=vmax)
            cb = plt.colorbar(
                mcm.ScalarMappable(norm=norm, cmap=cmap),
                cax=cbar_ax, orientation="horizontal",
            )
            cb.ax.tick_params(labelsize=6)
            vmin_label = str(int(vmin)) if vmin == int(vmin) else f"{vmin:.1f}"
            vmax_label = str(int(vmax)) if vmax == int(vmax) else f"{vmax:.1f}"
            cb.set_ticks([vmin, vmax])
            cb.set_ticklabels([vmin_label, vmax_label])

            y_cursor = cbar_bottom - 0.02
        else:
            if not cov_col.values:
                continue

            fig.text(x_start, y_cursor, f"{cov_col.label}:",
                     fontsize=7, fontweight="bold", color=text_color,
                     va="top", ha="left", transform=fig.transFigure)

            x_pos = x_start + (x_end - x_start) * 0.02
            entry_y = y_cursor - 0.015

            for val_key, cv in cov_col.values.items():
                sq_size = 0.008
                sq_ax = fig.add_axes([x_pos, entry_y, sq_size, sq_size])
                sq_ax.set_facecolor(cv.color)
                sq_ax.set_xticks([])
                sq_ax.set_yticks([])
                for spine in sq_ax.spines.values():
                    spine.set_visible(False)
                fig.text(x_pos + sq_size + 0.003, entry_y + sq_size / 2,
                         cv.label, fontsize=6, color=text_color,
                         va="center", ha="left", transform=fig.transFigure)
                x_pos += sq_size + 0.003 + len(cv.label) * 0.005 + 0.008

            y_cursor = entry_y - 0.015


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def plot_heatmap(
    rates_df: pd.DataFrame,
    config: ComparisonConfig,
    output_prefix: str,
) -> tuple[str, str]:
    """Per-sample clustered heatmap with optional covariate annotation panel.

    Z-score normalises each feature column, applies Ward hierarchical
    clustering to both rows and columns, and renders dendrograms on the
    left (rows) and top (columns). The reference condition (if any) is
    pushed to the bottom of the row dendrogram for visual consistency.

    Args:
        rates_df: DataFrame from
            :func:`karyoplot.mpl.data_loader.compute_per_sample_rates`.
        config: :class:`~karyoplot.mpl.types.ComparisonConfig`.
        output_prefix: Path prefix for ``.heatmap.svg`` / ``.heatmap.png``.

    Returns:
        ``(svg_path, png_path)`` tuple.
    """
    import matplotlib.colors as mcolors
    import matplotlib.patches as mpatches
    import matplotlib.pyplot as plt
    from scipy.cluster.hierarchy import dendrogram

    fg_names = list(config.feature_groups.keys())
    fg_labels = [config.feature_groups[fg].label for fg in fg_names]

    rates_sorted = rates_df.copy()
    raw_matrix = np.zeros((len(rates_sorted), len(fg_names)))
    for j, fg in enumerate(fg_names):
        raw_matrix[:, j] = rates_sorted[f"{fg}_rate"].values

    z_matrix = np.zeros_like(raw_matrix)
    for j in range(raw_matrix.shape[1]):
        col = raw_matrix[:, j]
        std = col.std()
        if std > 0:
            z_matrix[:, j] = (col - col.mean()) / std

    sample_labels = rates_sorted["sample"].values
    cond_colors = rates_sorted["condition_color"].values

    cov_df = None
    if config.covariates:
        cov_df = _load_covariate_data(config.covariates, sample_labels)

    ref_samples = None
    if config.reference_condition and config.reference_condition in config.conditions:
        ref_samples = config.conditions[config.reference_condition].samples
    (z_matrix, raw_matrix, sample_labels, cond_colors, fg_labels,
     cov_df, row_link, col_link, _) = cluster_and_reorder(
        z_matrix, raw_matrix, sample_labels, cond_colors, fg_labels,
        cov_df, reference_samples=ref_samples,
    )

    # Layout
    n_rows, n_cols = z_matrix.shape
    cell_size = 0.3
    hm_w = n_cols * cell_size
    hm_h = n_rows * cell_size
    dendro_w_in = 0.6
    cbar_w_in = 0.3
    dendro_h_in = 0.6

    has_cov = cov_df is not None
    n_covs = len(cov_df.columns) if has_cov else 0
    cov_w_in = max(0.4, n_covs * 0.25) if has_cov else 0

    fig_width = cov_w_in + hm_w + dendro_w_in + cbar_w_in + 2.5
    fig_height = hm_h + dendro_h_in + 2.0
    fig = plt.figure(figsize=(fig_width, fig_height))

    height_ratios = [dendro_h_in, hm_h]
    if has_cov:
        width_ratios = [cov_w_in, hm_w, dendro_w_in, cbar_w_in]
        gs = fig.add_gridspec(2, 4, width_ratios=width_ratios,
                              height_ratios=height_ratios,
                              hspace=0.01, wspace=0.02)
        ax_col_dg = fig.add_subplot(gs[0, 1])
        ax_cov = fig.add_subplot(gs[1, 0])
        ax_hm = fig.add_subplot(gs[1, 1])
        ax_row_dg = fig.add_subplot(gs[1, 2])
        ax_cbar = fig.add_subplot(gs[1, 3])
    else:
        width_ratios = [hm_w, dendro_w_in, cbar_w_in]
        gs = fig.add_gridspec(2, 3, width_ratios=width_ratios,
                              height_ratios=height_ratios,
                              hspace=0.01, wspace=0.02)
        ax_col_dg = fig.add_subplot(gs[0, 0])
        ax_hm = fig.add_subplot(gs[1, 0])
        ax_row_dg = fig.add_subplot(gs[1, 1])
        ax_cbar = fig.add_subplot(gs[1, 2])

    # Dendrograms
    dendro_c = _DENDRO_COLOR_DARK if config.dark_mode else _DENDRO_COLOR_LIGHT
    with plt.rc_context({"lines.linewidth": 0.8}):
        dendrogram(row_link, ax=ax_row_dg, orientation="right",
                   no_labels=True, color_threshold=0,
                   above_threshold_color=dendro_c)
    _style_dendro_ax(ax_row_dg, orientation="right")
    ax_row_dg.set_ylim(0, 10 * n_rows)
    ax_row_dg.invert_yaxis()

    with plt.rc_context({"lines.linewidth": 0.8}):
        dendrogram(col_link, ax=ax_col_dg, no_labels=True,
                   color_threshold=0, above_threshold_color=dendro_c)
    _style_dendro_ax(ax_col_dg, orientation="top")
    ax_col_dg.set_xlim(0, 10 * n_cols)

    # Heatmap with custom diverging colormap
    _blue = mcolors.to_rgb("#3b4cc0")
    _red = mcolors.to_rgb("#b40426")
    _mid = (0.0, 0.0, 0.0) if config.dark_mode else (1.0, 1.0, 1.0)
    cmap = mcolors.LinearSegmentedColormap.from_list(
        "custom_div", [_blue, _mid, _red], N=256,
    )

    vmax = max(np.abs(z_matrix).max(), 0.01)
    im = ax_hm.imshow(z_matrix, aspect="auto", cmap=cmap,
                      vmin=-vmax, vmax=vmax, interpolation="nearest")
    ax_hm.set_xlim(-0.5, n_cols - 0.5)
    ax_hm.set_ylim(n_rows - 0.5, -0.5)
    ax_hm.set_xticks(range(len(fg_labels)))
    ax_hm.set_xticklabels(fg_labels, rotation=45, ha="right", fontsize=9)

    if has_cov:
        ax_hm.set_yticks([])
    else:
        ax_hm.set_yticks(range(len(sample_labels)))
        ax_hm.set_yticklabels(sample_labels, fontsize=8)
        ax_hm.yaxis.set_ticks_position("left")
        for label_obj, color in zip(ax_hm.get_yticklabels(), cond_colors):
            label_obj.set_color(color)

    # Cell text — raw % values
    fg_c = fg_color(config.dark_mode)
    for i in range(raw_matrix.shape[0]):
        for j in range(raw_matrix.shape[1]):
            raw_val = raw_matrix[i, j]
            z_val = z_matrix[i, j]
            if not np.isnan(raw_val):
                text_color = "white" if abs(z_val) > vmax * 0.6 else fg_c
                ax_hm.text(j, i, f"{raw_val:.2f}",
                           ha="center", va="center",
                           fontsize=7, color=text_color)

    for spine in ax_hm.spines.values():
        spine.set_visible(True)
        spine.set_edgecolor(fg_c)
        spine.set_linewidth(1.0)

    cbar = fig.colorbar(im, cax=ax_cbar)
    cbar.set_label("z-score", fontsize=9)

    # Condition legend (above colorbar)
    handles = [mpatches.Patch(color=cond.color, label=cond.label)
               for cond in config.conditions.values()]
    ax_cbar.legend(handles=handles, loc="lower left", fontsize=8,
                   framealpha=0.8, bbox_to_anchor=(0, 1.02), borderaxespad=0)

    fig.suptitle(config.name, y=1.02)

    if has_cov:
        _draw_covariate_panel(ax_cov, cov_df, config.covariates,
                              dark_mode=config.dark_mode,
                              sample_labels=sample_labels,
                              cond_colors=cond_colors)
        ax_cov.set_ylim(ax_hm.get_ylim())
        fig.canvas.draw()
        _draw_covariate_legends(fig, ax_cov, cov_df, config.covariates,
                                dark_mode=config.dark_mode)

    # Hide empty gridspec cells in the dendrogram row
    if has_cov:
        for idx in [gs[0, 0], gs[0, 2], gs[0, 3]]:
            ax_empty = fig.add_subplot(idx)
            ax_empty.set_visible(False)
    else:
        for idx in [gs[0, 1], gs[0, 2]]:
            ax_empty = fig.add_subplot(idx)
            ax_empty.set_visible(False)

    return save_fig(fig, output_prefix, "heatmap")
