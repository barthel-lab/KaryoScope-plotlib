"""matplotlib defaults: font registration + dark/light rcParams.

Wraps :mod:`karyoplot.core.fonts`. Figures render in the bundled, freely-licensed
**Liberation Sans** (registered from package data, so they reproduce identically on
any host), with **DejaVu Sans** kept as the secondary family for the Greek letters,
subscripts, and minus sign some labels use (beta/gamma, log2, -log10 axis titles).
If the bundled font can't be loaded, the family falls back to
``["sans-serif", "DejaVu Sans"]``.

Examples:
    >>> from karyoplot.mpl import style
    >>> style.apply_default_style(dark_mode=True)
"""

from __future__ import annotations

from ..core.fonts import DEFAULT_FONT_FAMILY, VENDORED_FONT_FAMILY, register_vendored_fonts


def apply_default_style(dark_mode: bool = False) -> None:
    """Register fonts and set matplotlib rcParams.

    Args:
        dark_mode: If ``True``, use the dark theme (black background, white
            text/spines). If ``False``, use the light theme (white background,
            dark text). Default is ``False`` to preserve the historical
            ``feature_comparison_lib.visualizations.setup_plotting`` behaviour.
    """
    import matplotlib.pyplot as plt

    registered = register_vendored_fonts()
    if VENDORED_FONT_FAMILY in registered:
        plt.rcParams["font.family"] = [VENDORED_FONT_FAMILY, "DejaVu Sans"]
    else:
        plt.rcParams["font.family"] = [DEFAULT_FONT_FAMILY, "DejaVu Sans"]

    plt.rcParams["font.size"] = 10
    plt.rcParams["svg.fonttype"] = "none"
    plt.rcParams["mathtext.fontset"] = "dejavusans"
    plt.rcParams["axes.spines.top"] = False
    plt.rcParams["axes.spines.right"] = False

    if dark_mode:
        plt.rcParams["figure.facecolor"] = "#000000"
        plt.rcParams["axes.facecolor"] = "#000000"
        plt.rcParams["text.color"] = "white"
        plt.rcParams["axes.labelcolor"] = "white"
        plt.rcParams["xtick.color"] = "white"
        plt.rcParams["ytick.color"] = "white"
        plt.rcParams["axes.edgecolor"] = "#888888"
    else:
        plt.rcParams["figure.facecolor"] = "white"
        plt.rcParams["axes.facecolor"] = "white"
        plt.rcParams["text.color"] = "#000000"


def fg_color(dark_mode: bool) -> str:
    """Return foreground color: ``white`` on dark, ``black`` on light."""
    return "white" if dark_mode else "black"


def sig_label(p: float) -> str:
    """Convert a p-value to a significance star label (``***``, ``**``, ``*``, ``ns``)."""
    if p < 0.001:
        return "***"
    if p < 0.01:
        return "**"
    if p < 0.05:
        return "*"
    return "ns"


def save_fig(fig, output_prefix: str, suffix: str) -> tuple[str, str]:
    """Save a matplotlib figure as SVG (150 dpi) and PNG (300 dpi).

    Args:
        fig: matplotlib Figure.
        output_prefix: Path prefix (e.g. ``"results/foo"``).
        suffix: Plot type suffix (e.g. ``"heatmap"``); appended after a dot.

    Returns:
        ``(svg_path, png_path)`` tuple.
    """
    import matplotlib.pyplot as plt

    svg_path = f"{output_prefix}.{suffix}.svg"
    png_path = f"{output_prefix}.{suffix}.png"
    fig.savefig(svg_path, bbox_inches="tight", dpi=150)
    fig.savefig(png_path, bbox_inches="tight", dpi=300)
    plt.close(fig)
    return svg_path, png_path
