"""Chromosome facts: ordering, acrocentric set, telomeric motifs.

Consolidates the duplicated chromosome-sort and acrocentric-handling
logic across KaryoScope plotting scripts. Reference-specific data
(lengths, centromere positions, q-arm starts) is loaded lazily via
:func:`reference` so the library has no hardcoded path dependencies.

Examples:
    >>> from karyoplot.core import chromosomes as ch
    >>> sorted(["chrY", "chr1", "chr10", "chrX"], key=ch.chrom_sort_key)
    ['chr1', 'chr10', 'chrX', 'chrY']
    >>> "chr13" in ch.ACROCENTRIC
    True
    >>> ch.TELOMERIC_MOTIFS["TTAGGG"]["color"]
    '#F07167'
"""

from __future__ import annotations

ACROCENTRIC: frozenset[str] = frozenset(
    {"chr13", "chr14", "chr15", "chr21", "chr22"}
)
"""Acrocentric chromosomes (carry rDNA arrays in humans)."""

CANONICAL_CHROMS: tuple[str, ...] = tuple(
    [f"chr{i}" for i in range(1, 23)] + ["chrX", "chrY", "chrM"]
)


def chrom_sort_key(name: str) -> tuple[int, str]:
    """Sort key that orders chromosomes 1–22, X, Y, M, then alphabetically.

    Strips a leading ``chr`` prefix. Unknown labels sort after numeric
    chromosomes by their original name to keep ordering stable.
    """
    s = name[3:] if name.startswith("chr") else name
    if s.isdigit():
        return (int(s), "")
    if s == "X":
        return (23, "")
    if s == "Y":
        return (24, "")
    if s == "M" or s == "MT":
        return (25, "")
    return (1000, s)


# Telomeric hexamer motifs with default Barthel-palette colors.
# Used by sequence-search and per-read visualization scripts.
TELOMERIC_MOTIFS: dict[str, dict[str, str]] = {
    # Canonical (Coral / Blue)
    "TTAGGG": {"color": "#F07167", "type": "canonical", "label": "TTAGGG"},
    "CCCTAA": {"color": "#60A5FA", "type": "canonical_rc", "label": "CCCTAA"},
    # Variants (Green / Lavender / Yellow)
    "TCAGGG": {"color": "#40D392", "type": "variant", "label": "TCAGGG"},
    "CCCTGA": {"color": "#40D392", "type": "variant_rc", "label": "CCCTGA"},
    "TGAGGG": {"color": "#C4A9E8", "type": "variant", "label": "TGAGGG"},
    "CCCTCA": {"color": "#C4A9E8", "type": "variant_rc", "label": "CCCTCA"},
    "TTGGGG": {"color": "#FBBF24", "type": "variant", "label": "TTGGGG"},
    "CCCCAA": {"color": "#FBBF24", "type": "variant_rc", "label": "CCCCAA"},
}


# Reference-specific data lives in dataclasses returned by `reference()`.
# This keeps the module import-cheap and avoids hardcoded paths.

from dataclasses import dataclass


@dataclass(frozen=True)
class Reference:
    """Reference-specific chromosome metadata.

    Attributes:
        name: Reference name (e.g. ``"CHM13_v2"``, ``"GRCh38"``).
        lengths: Chromosome lengths in bp.
        q_arm_starts: For acrocentric chromosomes, the coordinate where
            the long arm begins (short arm contains rDNA).
    """

    name: str
    lengths: dict[str, int]
    q_arm_starts: dict[str, int]


# Subset of CHM13_v2 lengths and acrocentric q-arm starts taken from
# karyoscope_utils.constants. Extend as needed; not authoritative.
CHM13_V2 = Reference(
    name="CHM13_v2",
    lengths={
        "chr13": 113_566_656,
        "chr14": 101_161_118,
        "chr15": 99_753_195,
        "chr21": 45_090_682,
        "chr22": 51_324_926,
    },
    q_arm_starts={
        "chr13": 22_498_291,
        "chr14": 17_708_240,
        "chr15": 22_694_129,
        "chr21": 16_341_849,
        "chr22": 20_711_065,
    },
)


_REFERENCES: dict[str, Reference] = {"CHM13_v2": CHM13_V2}


def reference(name: str) -> Reference:
    """Look up a registered :class:`Reference` by name."""
    if name not in _REFERENCES:
        raise ValueError(
            f"unknown reference {name!r}; available: {sorted(_REFERENCES)}"
        )
    return _REFERENCES[name]


def register_reference(ref: Reference) -> None:
    """Register a custom :class:`Reference` (e.g. for GRCh38, mouse)."""
    _REFERENCES[ref.name] = ref
