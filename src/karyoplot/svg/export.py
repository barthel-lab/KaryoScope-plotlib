"""SVG -> PNG export via ``rsvg-convert``.

Replaces the inline ``_svg_to_png`` helpers that exist in many
KaryoScope scripts (cluster_plot, plot_reads, draw_legend, etc.).
"""

from __future__ import annotations

import os
import subprocess


class RsvgConvertMissingError(RuntimeError):
    """Raised when ``rsvg-convert`` is not available on PATH."""


def svg_to_png(
    svg_path: str | os.PathLike,
    png_path: str | os.PathLike | None = None,
    *,
    scale: int | None = None,
    dpi: int | None = None,
    raise_on_error: bool = False,
    quiet: bool = False,
) -> str | None:
    """Convert an SVG file to PNG using ``rsvg-convert``.

    Two upscaling modes (mutually exclusive):

    - ``scale=N`` → invokes ``rsvg-convert -z N`` (zoom factor). Used by
      the BIR clustering plots.
    - ``dpi=D`` → invokes ``rsvg-convert -d D -p D`` (x/y DPI). Used by
      the ISCN assembly figures.

    If neither is given, defaults to ``scale=4`` (matches the cluster_plot
    historical behaviour).

    Args:
        svg_path: Path to the source SVG.
        png_path: Output path. If ``None``, replaces the ``.svg`` extension
            with ``.png``.
        scale: Zoom factor passed as ``-z`` (mutually exclusive with ``dpi``).
        dpi: Output DPI for x and y, passed as ``-d`` ``-p``.
        raise_on_error: If ``True``, raise on missing tool / failure.
        quiet: Suppress the warning print on missing-tool fallback (useful
            in tight loops where the warning is repeated).

    Returns:
        The PNG path on success, ``None`` if ``rsvg-convert`` is missing
        or conversion failed and ``raise_on_error`` is ``False``.
    """
    if scale is not None and dpi is not None:
        raise ValueError("svg_to_png: pass scale OR dpi, not both")

    svg = str(svg_path)
    out = str(png_path) if png_path else svg.rsplit(".svg", 1)[0] + ".png"

    if dpi is not None:
        cmd = ["rsvg-convert", "-d", str(dpi), "-p", str(dpi), "-f", "png", "-o", out, svg]
    else:
        z = scale if scale is not None else 4
        cmd = ["rsvg-convert", "-z", str(z), "-f", "png", "-o", out, svg]

    try:
        subprocess.run(cmd, check=True, capture_output=True)
    except FileNotFoundError:
        if raise_on_error:
            raise RsvgConvertMissingError(
                "rsvg-convert not found on PATH; install librsvg"
            ) from None
        if not quiet:
            print("  Warning: rsvg-convert not found, skipping PNG export")
        return None
    except subprocess.CalledProcessError as e:
        if raise_on_error:
            raise
        msg = e.stderr.decode().strip() if e.stderr else str(e)
        if not quiet:
            print(f"  Warning: PNG export failed: {msg}")
        return None

    return out


def is_rsvg_convert_available() -> bool:
    """Return ``True`` if ``rsvg-convert`` can be invoked."""
    try:
        subprocess.run(
            ["rsvg-convert", "--version"],
            capture_output=True,
            check=True,
        )
    except (FileNotFoundError, subprocess.CalledProcessError):
        return False
    return True
