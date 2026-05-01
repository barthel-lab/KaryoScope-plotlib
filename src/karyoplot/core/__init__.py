"""Backend-agnostic utilities shared between karyoplot.svg and karyoplot.mpl.

Modules:
    chromosomes: chromosome sort, lengths, acrocentric set, telomeric motifs
    colors:      color file loaders, hex<->RGB, Barthel palette
    coords:      genome-coord <-> pixel scaling (full / subtelomere / centromere)
    fonts:       optional Barthel brand font registration (defaults to sans-serif)
    io:          gzip-aware BED loader, FASTA via samtools, smart_open
    theme:       dark / light visual themes (background, text, line, font defaults)
"""

from . import chromosomes, colors, coords, fonts, io, sample_metadata, text, theme

__all__ = [
    "chromosomes",
    "colors",
    "coords",
    "fonts",
    "io",
    "sample_metadata",
    "text",
    "theme",
]
