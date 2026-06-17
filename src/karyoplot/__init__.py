"""karyoplot — shared plotting library for KaryoScope analyses.

Subpackages:
    core: backend-agnostic utilities (chromosomes, colors, coords, fonts, io)
    svg:  drawsvg-based vector renderers
    mpl:  matplotlib-based publication plots
"""

from karyoplot._version import __version__

__all__ = ["__version__"]
