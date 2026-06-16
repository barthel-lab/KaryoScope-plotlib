"""File IO: gzip-aware open, BED loaders, FASTA region fetch.

Consolidates the BED-loading and FASTA-extraction patterns previously
duplicated across KaryoScope scripts. Loaders are deliberately thin
wrappers around the standard formats so they're easy to compose.

Examples:
    >>> from karyoplot.core import io
    >>> with io.smart_open("file.bed.gz") as f:
    ...     first = f.readline()
    >>> df = io.load_bed("file.bed", featureset="repeat")
"""

from __future__ import annotations

import gzip
import os
import subprocess
from collections.abc import Iterator
from contextlib import contextmanager

DEFAULT_BED_COLUMNS: tuple[str, ...] = ("chrom", "start", "end", "name")


@contextmanager
def smart_open(path: str | os.PathLike, mode: str = "rt") -> Iterator:
    """Open a file transparently, decompressing ``.gz`` automatically."""
    p = str(path)
    opener = gzip.open if p.endswith(".gz") else open
    with opener(p, mode) as f:
        yield f


def load_bed(
    path: str | os.PathLike,
    columns: tuple[str, ...] | None = None,
    featureset: str | None = None,
):
    """Load a BED-style file into a pandas DataFrame.

    Args:
        path: BED or BED.gz file.
        columns: Column names (defaults to ``chrom, start, end, name``).
            Extra columns in the file beyond ``len(columns)`` are kept
            with auto-generated names ``col5, col6, ...``.
        featureset: If given, filter rows to ``df["name"] == featureset``.

    Returns:
        ``pandas.DataFrame``.
    """
    import pandas as pd

    cols = columns or DEFAULT_BED_COLUMNS
    df = pd.read_csv(
        path,
        sep="\t",
        header=None,
        comment="#",
        compression="infer",
        low_memory=False,
    )
    n_named = min(len(cols), df.shape[1])
    new_names = list(cols[:n_named]) + [f"col{i + 1}" for i in range(n_named, df.shape[1])]
    df.columns = new_names

    if featureset is not None and "name" in df.columns:
        df = df[df["name"] == featureset].reset_index(drop=True)
    return df


def iter_bed_records(
    path: str | os.PathLike,
    min_columns: int = 4,
) -> Iterator[tuple]:
    """Stream BED records as tuples ``(chrom, start, end, name, *rest)``.

    More memory-efficient than :func:`load_bed` for very large files.
    Skips lines with fewer than ``min_columns`` whitespace-separated fields.
    """
    with smart_open(path, "rt") as f:
        for line in f:
            if not line or line.startswith("#"):
                continue
            parts = line.rstrip("\n").split("\t")
            if len(parts) < min_columns:
                continue
            chrom = parts[0]
            start = int(parts[1])
            end = int(parts[2])
            rest = tuple(parts[3:])
            yield (chrom, start, end, *rest)


def fetch_fasta_region(
    fasta_path: str | os.PathLike,
    chrom: str,
    start: int,
    end: int,
) -> str:
    """Fetch a sequence from an indexed FASTA via ``samtools faidx``.

    Coordinates are 0-based half-open (``start`` inclusive, ``end`` exclusive),
    matching BED. Returns the uppercased sequence; empty string on any error.
    """
    region = f"{chrom}:{start + 1}-{end}"
    try:
        result = subprocess.run(
            ["samtools", "faidx", str(fasta_path), region],
            capture_output=True,
            text=True,
            check=True,
        )
    except (FileNotFoundError, subprocess.CalledProcessError):
        return ""
    lines = result.stdout.strip().split("\n")
    if len(lines) <= 1:
        return ""
    return "".join(lines[1:]).upper()


class FastaCache:
    """Process-local cache for repeated ``fetch_fasta_region`` calls.

    Replaces the module-level cache in
    ``karyoscope_utils.sequence._sequence_cache`` with an explicit
    object you instantiate (so unit tests don't share state).
    """

    def __init__(self, fasta_path: str | os.PathLike) -> None:
        self.fasta_path = str(fasta_path)
        self._cache: dict[tuple[str, int, int], str] = {}

    def fetch(self, chrom: str, start: int, end: int) -> str:
        key = (chrom, start, end)
        if key not in self._cache:
            self._cache[key] = fetch_fasta_region(self.fasta_path, chrom, start, end)
        return self._cache[key]

    def clear(self) -> None:
        self._cache.clear()
