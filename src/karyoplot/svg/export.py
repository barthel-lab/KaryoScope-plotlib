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
    scale: int = 4,
    raise_on_error: bool = False,
) -> str | None:
    """Convert an SVG file to PNG using ``rsvg-convert``.

    Args:
        svg_path: Path to the source SVG.
        png_path: Output path. If ``None``, replaces the ``.svg`` extension
            with ``.png``.
        scale: Zoom factor passed as ``-z``. Default 4 matches the value
            used in existing KaryoScope scripts.
        raise_on_error: If ``True``, raise on missing tool / failure;
            otherwise emit a warning print and return ``None``.

    Returns:
        The PNG path on success, ``None`` if ``rsvg-convert`` is missing
        or conversion failed and ``raise_on_error`` is ``False``.
    """
    svg = str(svg_path)
    out = str(png_path) if png_path else svg.rsplit(".svg", 1)[0] + ".png"

    try:
        subprocess.run(
            ["rsvg-convert", "-z", str(scale), "-f", "png", "-o", out, svg],
            check=True,
            capture_output=True,
        )
    except FileNotFoundError:
        if raise_on_error:
            raise RsvgConvertMissingError(
                "rsvg-convert not found on PATH; install librsvg"
            )
        print("  Warning: rsvg-convert not found, skipping PNG export")
        return None
    except subprocess.CalledProcessError as e:
        if raise_on_error:
            raise
        msg = e.stderr.decode().strip() if e.stderr else str(e)
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
