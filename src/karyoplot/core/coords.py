"""Genome-coordinate <-> pixel scaling.

Replaces the 20 identical inline `pixels_per_pos` formulas with a
unified PixelScale class supporting full-genome, subtelomere, and
centromere zoom modes.

Populated in Phase 2.
"""

# Phase 2 will fill this with:
#   - class PixelScale:
#       mode: "full" | "subtelomere" | "centromere" | "custom"
#       def pos_to_pixel(pos: int) -> int
#       def pixel_to_pos(px: int) -> int
#   - DEFAULT_SCALES: dict (full=4/1e6, subtel=1/300, centromere=1/25_000)
