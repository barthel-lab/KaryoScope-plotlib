"""Chromosome facts: ordering, acrocentric set, scaffold mappings, telomeric motifs.

Consolidates the ~20 inline copies of `chrom_sort_key` and the hardcoded
acrocentric set scattered across KaryoScope plotting scripts.

Populated in Phase 2.
"""

# Phase 2 will fill this with:
#   - ACROCENTRIC: frozenset = frozenset({"chr13","chr14","chr15","chr21","chr22"})
#   - chrom_sort_key(name) -> int
#   - chrom_lengths(reference="CHM13") -> dict[str, int]
#   - centromere_position(chrom, reference) -> tuple[int, int]
#   - TELOMERIC_MOTIFS: dict (canonical, variant, etc.)
