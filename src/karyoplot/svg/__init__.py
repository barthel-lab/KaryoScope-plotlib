"""drawsvg-based vector renderers.

Modules:
    drawing:  primitive helpers (rectangles, scale bars, annotation tracks, axes)
    legend:   legend builders (hexamer, grouped multi-track, standalone)
    reads:    per-read fiber-seq vertical-bar layouts
    export:   SVG -> PNG via rsvg-convert
"""

from . import drawing, export, legend, reads

__all__ = ["drawing", "export", "legend", "reads"]
