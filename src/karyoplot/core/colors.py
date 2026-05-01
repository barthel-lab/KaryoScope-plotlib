"""Color file loaders + hex/RGB conversion utilities.

Consolidates color loading patterns across ~80 scripts and replaces
`matplotlib.colors` usage in scripts that don't otherwise need matplotlib
(e.g. KaryoScope_cluster_plot.py).

Populated in Phase 2.
"""

# Phase 2 will fill this with:
#   - load_palette(path) -> dict[str, str]    # feature -> "#RRGGBB"
#   - hex_to_rgb(hex_str) -> tuple[int, int, int]
#   - hex_to_rgba(hex_str, alpha=255) -> tuple[int, int, int, int]
#   - rgb_to_hex(r, g, b) -> str
