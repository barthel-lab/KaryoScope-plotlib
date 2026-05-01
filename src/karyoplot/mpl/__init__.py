"""matplotlib-based publication plots.

Modules:
    types:        dataclasses describing a feature-comparison analysis
    style:        font + theme defaults; ``apply_default_style(dark_mode)``
    data_loader:  load sequence-annotation TSVs, compute per-sample rates
    statistics:   Fisher exact, Mann-Whitney, BH-FDR, comparison runner
    heatmap:      clustered per-sample heatmap with optional covariate panel
    comparison:   volcano, dot-strip, lollipop plots; ``generate_all_plots``
    legend:       (Phase 6) matplotlib legend helpers
"""

from . import comparison, data_loader, heatmap, legend, statistics, style, types

__all__ = [
    "comparison",
    "data_loader",
    "heatmap",
    "legend",
    "statistics",
    "style",
    "types",
]
