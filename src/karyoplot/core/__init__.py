"""Backend-agnostic utilities shared between karyoplot.svg and karyoplot.mpl.

Modules:
    chromosomes: chromosome sort, lengths, acrocentric set, telomeric motifs
    colors:      color file loaders, hex<->RGB, palette dict
    coords:      genome-coord <-> pixel scaling (full / subtelomere / centromere)
    fonts:       Basic Sans / Bicyclette font registration
    io:          gzip-aware BED loader, FASTA via samtools, feature aggregation
"""
