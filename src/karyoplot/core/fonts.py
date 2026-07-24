"""Font registration for KaryoScope plots.

For publication figures the library ships its own freely-licensed font,
**Liberation Sans** (SIL OFL 1.1, metric-compatible with Arial), as package
data. :func:`register_vendored_fonts` registers it with matplotlib, so every
consumer renders identically on any host — no system font install, no
license-encumbered brand fonts, fully reproducible. This is the intended
default for the manuscript figures.

The optional Barthel *presentation* fonts (Basic Sans, Bicyclette) remain an
explicit opt-in via :func:`register_fonts` when a caller genuinely wants the
slide typeface — a silent no-op if the font directory is missing. They are
commercial (Adobe Fonts) and must not be vendored/redistributed, which is why
they are not the figure default.

Examples:
    >>> from karyoplot.core import fonts
    >>> fonts.register_vendored_fonts()           # ['Liberation Sans']
    >>> fonts.is_available("Liberation Sans")
    True
"""

from __future__ import annotations

import os
from pathlib import Path

DEFAULT_FONT_FAMILY = "sans-serif"

#: Freely-licensed figure font shipped in ``karyoplot/data/fonts`` (OFL 1.1).
VENDORED_FONT_FAMILY = "Liberation Sans"

#: Optional Barthel *presentation* fonts. The ``.otf`` files live in the Barthel
#: ``Powerpoint-Themes`` repo (``fonts/``); point ``$BARTHEL_FONT_DIR`` at that
#: directory to opt in. Commercial (Adobe Fonts) — never vendored here.
BARTHEL_FONT_DIR = Path(
    os.environ.get(
        "BARTHEL_FONT_DIR", Path.home() / "Documents" / "Barthel-Custom-Powerpoint-Theme" / "fonts"
    )
)

BARTHEL_FONT_FAMILIES = ("Basic Sans", "Bicyclette")


def _vendored_font_dir() -> Path | None:
    """Filesystem path of the bundled fonts, or ``None`` if it can't be resolved.

    Uses ``importlib.resources`` so it works for an editable checkout and a normal
    (unpacked) wheel install alike. matplotlib stores the font path and re-opens it
    at draw time, so a real, persistent path is required.
    """
    try:
        from importlib.resources import files

        path = Path(str(files("karyoplot").joinpath("data", "fonts")))
    except Exception:
        return None
    return path if path.is_dir() else None


def register_vendored_fonts() -> list[str]:
    """Register the bundled Liberation Sans family with matplotlib.

    Returns:
        The font family names registered (``["Liberation Sans"]``), or ``[]`` if
        matplotlib is not importable or the bundled fonts can't be found.
    """
    try:
        import matplotlib.font_manager as fm
    except ImportError:
        return []

    font_dir = _vendored_font_dir()
    if font_dir is None:
        return []

    registered: set[str] = set()
    for font_file in font_dir.glob("LiberationSans-*.ttf"):
        try:
            fm.fontManager.addfont(str(font_file))
            registered.add(fm.FontProperties(fname=str(font_file)).get_name())
        except Exception:
            continue
    return sorted(registered)


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


_VENDORED_PIL_FILES: dict[str, str] = {
    "Liberation Sans": "LiberationSans-Regular.ttf",
    "Liberation Sans Bold": "LiberationSans-Bold.ttf",
    "Liberation Sans Italic": "LiberationSans-Italic.ttf",
}

_BARTHEL_PIL_FILES: dict[str, str] = {
    "Basic Sans": "BasicSans-Regular.otf",
    "Basic Sans Bold": "BasicSans-Bold.otf",
    "Basic Sans Italic": "BasicSans-Italic.otf",
    "Bicyclette": "Bicyclette-Regular.otf",
    "Bicyclette Bold": "Bicyclette-Bold.otf",
}


def pil_font(size: int, family: str = "Liberation Sans", fallback: str = "Arial"):
    """Load a PIL ``ImageFont`` with a vendored-first / system fallback chain.

    Used by raster-output scripts (PNG / GIF / MP4 frames) such as
    ``KaryoScope_plot_reads.py``. Tries, in order:

    1. The bundled Liberation Sans file for the requested ``family`` (always present).
    2. ``BARTHEL_FONT_DIR / <font_file>`` for a requested Barthel ``family``.
    3. The system font named ``fallback`` (e.g. ``Arial``).
    4. matplotlib's bundled DejaVu Sans at the requested ``size``.
    5. Pillow's bundled default (always succeeds, but a fixed ~10 px bitmap).

    Returns the loaded ``ImageFont`` instance. Never raises.
    """
    from PIL import ImageFont  # imported lazily so karyoplot.core.fonts has no PIL dep

    vendored_file = _VENDORED_PIL_FILES.get(family)
    vendored_dir = _vendored_font_dir()
    if vendored_file is not None and vendored_dir is not None:
        try:
            return ImageFont.truetype(str(vendored_dir / vendored_file), size)
        except OSError:
            pass

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

    # Before Pillow's fixed ~10 px bitmap default: matplotlib bundles DejaVu Sans
    # and is a karyoplot dependency, so use it at the requested ``size``. This keeps
    # raster labels legible on hosts that lack Basic Sans / Arial (e.g. headless
    # compute nodes) instead of collapsing every label to the load_default() bitmap.
    try:
        from matplotlib import font_manager as _fm

        return ImageFont.truetype(_fm.findfont("DejaVu Sans", fallback_to_default=True), size)
    except Exception:
        pass

    return ImageFont.load_default()
