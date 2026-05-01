"""Visual themes (background, foreground, line, font defaults).

Themes consolidate the ``background_color``-driven branching seen in
many KaryoScope scripts (``line_color = '#FFFFFF' if bg == 'black' else '#333333'``).

The ``DARK`` theme matches the most recent reference output style
(black background, white text/lines, generic ``sans-serif`` font) used
by ``KaryoScope_cluster_plot.py --background black``.

Examples:
    >>> from karyoplot.core import theme
    >>> t = theme.DARK
    >>> t.background, t.text, t.line
    ('#000000', '#FFFFFF', '#FFFFFF')
    >>> theme.get("light").background
    '#FFFFFF'
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .colors import BARTHEL
from .fonts import DEFAULT_FONT_FAMILY


@dataclass(frozen=True)
class Theme:
    """A visual theme bundle.

    Attributes:
        name: Identifier (``"dark"`` or ``"light"``).
        background: Background fill color (hex).
        text: Default text fill color (hex).
        line: Default line/stroke color (hex).
        muted_line: Lighter line color for secondary elements (hex).
        font_family: Default font family.
        font_sizes: Named font sizes (``label``, ``axis``, ``title``).
    """

    name: str
    background: str
    text: str
    line: str
    muted_line: str
    font_family: str = DEFAULT_FONT_FAMILY
    font_sizes: dict[str, int] = field(
        default_factory=lambda: {"label": 7, "axis": 8, "title": 10}
    )


DARK = Theme(
    name="dark",
    background=BARTHEL["black"],
    text=BARTHEL["white"],
    line=BARTHEL["white"],
    muted_line="#AAAAAA",
)

LIGHT = Theme(
    name="light",
    background=BARTHEL["white"],
    text="#333333",
    line="#333333",
    muted_line="#444444",
)

DEFAULT_THEME = DARK
"""Default theme is dark to match the most recent cluster_plot_black style."""

_THEMES: dict[str, Theme] = {"dark": DARK, "black": DARK, "light": LIGHT, "white": LIGHT}


def get(name: str | None = None) -> Theme:
    """Look up a theme by name. ``None`` returns :data:`DEFAULT_THEME`."""
    if name is None:
        return DEFAULT_THEME
    key = name.lower()
    if key not in _THEMES:
        raise ValueError(
            f"unknown theme {name!r}; available: {sorted(set(_THEMES))}"
        )
    return _THEMES[key]


def line_color_for(background: str) -> str:
    """Return the appropriate line color for a given background hex.

    Mirrors the ``line_color = '#FFFFFF' if bg == 'black' else '#333333'``
    pattern found in many existing scripts.
    """
    bg = background.lower()
    if bg in ("#000000", "black"):
        return BARTHEL["white"]
    return "#333333"


def text_color_for(background: str) -> str:
    """Return the appropriate text color for a given background hex."""
    return line_color_for(background)
