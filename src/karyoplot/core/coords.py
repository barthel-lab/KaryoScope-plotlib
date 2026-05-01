"""Genome-coordinate <-> pixel scaling.

Replaces the 20+ inline copies of:

    pixels_per_pos = 4 / 1_000_000
    def pos_to_y(pos):
        return initial_y + floor(pos * pixels_per_pos)

with a single :class:`PixelScale` class that supports the three
common zoom modes used across KaryoScope plots.

Examples:
    >>> from karyoplot.core.coords import PixelScale
    >>> s = PixelScale(mode="full", origin=10)
    >>> s.pos_to_pixel(1_000_000)
    14
    >>> s = PixelScale(mode="subtelomere")
    >>> s.pos_to_pixel(3000)
    10
"""

from __future__ import annotations

from dataclasses import dataclass
from math import floor

# Default scale factors (pixels per bp), matching the inline values
# used across the existing KaryoScope plotting scripts.
DEFAULT_SCALES: dict[str, float] = {
    "full": 4 / 1_000_000,        # 4 px per Mb (whole-genome ideogram)
    "subtelomere": 1 / 300,        # 1 px per 300 bp (subtelomere zoom)
    "centromere": 1 / 25_000,      # 1 px per 25 kb (centromere zoom)
}


@dataclass
class PixelScale:
    """Convert between genome coordinates (bp) and pixel offsets.

    Attributes:
        mode: One of ``"full"``, ``"subtelomere"``, ``"centromere"``,
            or ``"custom"`` (then supply ``pixels_per_bp`` directly).
        origin: Pixel offset added to every conversion (i.e. the
            top/left margin where the track starts).
        pixels_per_bp: Conversion factor; if ``None``, it is taken
            from :data:`DEFAULT_SCALES` for the chosen mode.
    """

    mode: str = "full"
    origin: int = 0
    pixels_per_bp: float | None = None

    def __post_init__(self) -> None:
        if self.pixels_per_bp is None:
            if self.mode not in DEFAULT_SCALES:
                raise ValueError(
                    f"unknown mode {self.mode!r}; "
                    "use 'custom' and supply pixels_per_bp"
                )
            object.__setattr__(self, "pixels_per_bp", DEFAULT_SCALES[self.mode])

    def pos_to_pixel(self, pos: int) -> int:
        """Convert a genome position (bp) to a pixel offset."""
        return self.origin + floor(pos * self.pixels_per_bp)

    def pixel_to_pos(self, px: int) -> int:
        """Convert a pixel offset back to a genome position (bp)."""
        return int((px - self.origin) / self.pixels_per_bp)

    def span_pixels(self, start: int, end: int) -> int:
        """Pixel span (positive integer) between two genome positions."""
        return self.pos_to_pixel(end) - self.pos_to_pixel(start)
