"""drawsvg-based vector renderers.

Modules:
    drawing:  primitive helpers (rectangles, scale bars, annotation tracks, axes)
    legend:   legend builders (hexamer, grouped multi-track, standalone)
    export:   SVG -> PNG via rsvg-convert

Stubs awaiting Phase 6/7 migrations:
    ideogram: whole-genome and zoom views
    tracks:   multi-track layouts
    reads:    per-read fiber-seq vertical-bar layouts
"""

from . import drawing, export, ideogram, legend, reads, tracks

__all__ = ["drawing", "export", "ideogram", "legend", "reads", "tracks"]
