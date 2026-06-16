"""Font registration for KaryoScope plots.

The library defaults to the generic CSS ``sans-serif`` family so plots
work without any extra font files. The optional Barthel brand fonts
(Basic Sans, Bicyclette) can be registered with :func:`register_fonts`
when available — a silent no-op if the font directory is missing.

Examples:
    >>> from karyoplot.core import fonts
    >>> registered = fonts.register_fonts()      # quiet, returns list
    >>> fonts.is_available("Basic Sans")          # check before using
"""

from __future__ import annotations

import os
from pathlib import Path

DEFAULT_FONT_FAMILY = "sans-serif"

BARTHEL_FONT_DIR = Path.home() / "Documents" / "Barthel-Custom-Powerpoint-Theme" / "fonts"

BARTHEL_FONT_FAMILIES = ("Basic Sans", "Bicyclette")


def register_fonts(font_dir: str | os.PathLike | None = None) -> list[str]:
    """Register Barthel brand fonts with matplotlib if available.

    Args:
        font_dir: Directory containing ``BasicSans-*.otf`` and/or
            ``Bicyclette-*.otf`` files. Defaults to
            ``~/Documents/Barthel-Custom-Powerpoint-Theme/fonts``.

    Returns:
        List of font family names that were registered. Empty list
        if matplotlib is not importable or the directory is missing.
    """
    try:
        import matplotlib.font_manager as fm
    except ImportError:
        return []

    path = Path(font_dir) if font_dir is not None else BARTHEL_FONT_DIR
    if not path.exists():
        return []

    registered: set[str] = set()
    for pattern in ("BasicSans-*.otf", "Bicyclette-*.otf"):
        for font_file in path.glob(pattern):
            try:
                fm.fontManager.addfont(str(font_file))
                family = fm.FontProperties(fname=str(font_file)).get_name()
                registered.add(family)
            except Exception:
                continue
    return sorted(registered)


def set_default_font(name: str = DEFAULT_FONT_FAMILY) -> None:
    """Set matplotlib's default font family.

    No-op if matplotlib is not installed.
    """
    try:
        import matplotlib as mpl
    except ImportError:
        return
    mpl.rcParams["font.family"] = name


def is_available(family: str) -> bool:
    """Return True if ``family`` is currently registered with matplotlib."""
    try:
        import matplotlib.font_manager as fm
    except ImportError:
        return False
    return any(f.name == family for f in fm.fontManager.ttflist)


def resolve_family(preferred: str = "Basic Sans") -> str:
    """Return ``preferred`` if registered, else ``DEFAULT_FONT_FAMILY``.

    Useful for plotting code that wants to opt in to Barthel fonts
    when present without forcing them as a hard dependency.
    """
    return preferred if is_available(preferred) else DEFAULT_FONT_FAMILY


_BARTHEL_PIL_FILES: dict[str, str] = {
    "Basic Sans": "BasicSans-Regular.otf",
    "Basic Sans Bold": "BasicSans-Bold.otf",
    "Basic Sans Italic": "BasicSans-Italic.otf",
    "Bicyclette": "Bicyclette-Regular.otf",
    "Bicyclette Bold": "Bicyclette-Bold.otf",
}


def pil_font(size: int, family: str = "Basic Sans", fallback: str = "Arial"):
    """Load a PIL ``ImageFont`` with a Barthel-first / system fallback chain.

    Used by raster-output scripts (PNG / GIF / MP4 frames) such as
    ``KaryoScope_plot_reads.py``. Tries:

    1. ``BARTHEL_FONT_DIR / <font_file>`` for the requested ``family``.
    2. The system font named ``fallback`` (e.g. ``Arial``).
    3. Pillow's bundled default (always succeeds).

    Returns the loaded ``ImageFont`` instance. Never raises.
    """
    from PIL import ImageFont  # imported lazily so karyoplot.core.fonts has no PIL dep

    font_file = _BARTHEL_PIL_FILES.get(family)
    if font_file is not None:
        path = BARTHEL_FONT_DIR / font_file
        try:
            return ImageFont.truetype(str(path), size)
        except OSError:
            pass

    if fallback:
        try:
            return ImageFont.truetype(fallback, size)
        except OSError:
            pass

    return ImageFont.load_default()
