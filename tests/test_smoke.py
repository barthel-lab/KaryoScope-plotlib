"""Smoke test: verify the package imports cleanly."""


def test_top_level_import():
    import karyoplot

    assert karyoplot.__version__ == "0.1.0"


def test_subpackage_imports():
    from karyoplot import core, svg, mpl

    # core modules
    from karyoplot.core import chromosomes, colors, coords, fonts, io  # noqa: F401

    # svg modules
    from karyoplot.svg import drawing, ideogram, tracks, reads, legend, export  # noqa: F401

    # mpl modules
    from karyoplot.mpl import (  # noqa: F401
        style,
        heatmap,
        comparison,
        statistics,
        data_loader,
        legend as mpl_legend,
    )
