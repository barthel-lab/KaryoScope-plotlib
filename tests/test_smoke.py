"""Smoke test: verify the package imports cleanly."""


def test_top_level_import():
    import karyoplot

    assert karyoplot.__version__ == "0.1.0"


def test_subpackage_imports():

    # core modules
    from karyoplot.core import chromosomes, colors, coords, fonts, io  # noqa: F401

    # mpl modules
    from karyoplot.mpl import (  # noqa: F401
        comparison,
        data_loader,
        heatmap,
        statistics,
        style,
    )

    # svg modules
    from karyoplot.svg import drawing, export, legend, reads  # noqa: F401
