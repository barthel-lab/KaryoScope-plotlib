"""matplotlib defaults: font registration + dark/light rcParams.

Wraps :mod:`karyoplot.core.fonts` so that the same Basic Sans / Bicyclette
opt-in path is used by both the SVG and matplotlib backends. When the
Barthel fonts aren't available the matplotlib font.family falls back to
``["sans-serif", "DejaVu Sans"]`` (DejaVu provides Greek glyphs needed
for β/γ labels).

Examples:
    >>> from karyoplot.mpl import style
    >>> style.apply_default_style(dark_mode=True)
"""

from __future__ import annotations

from ..core.fonts import DEFAULT_FONT_FAMILY, register_fonts


def apply_default_style(dark_mode: bool = False) -> None:
    """Register fonts and set matplotlib rcParams.

    Args:
        dark_mode: If ``True``, use the dark theme (black background, white
            text/spines). If ``False``, use the light theme (white background,
            dark text). Default is ``False`` to preserve the historical
            ``feature_comparison_lib.visualizations.setup_plotting`` behaviour.
    """
    import matplotlib.pyplot as plt

    registered = register_fonts()
    if "Basic Sans" in registered:
        plt.rcParams["font.family"] = ["Basic Sans", "DejaVu Sans"]
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
