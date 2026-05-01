"""File IO: BED loaders (gzip-aware), FASTA via samtools, feature aggregation.

Consolidates the 68 BED-loading variants across scripts plus the FASTA
extraction logic from karyoscope_utils/sequence.py.

Populated in Phase 2.
"""

# Phase 2 will fill this with:
#   - load_bed(path, featureset=None, columns=None) -> pd.DataFrame
#       (auto-detects .gz, optional featureset filter, configurable columns)
#   - fetch_fasta_region(fasta, region) -> str   (samtools faidx wrapper)
#   - aggregate_features(df, by=("sample","chrom","feature")) -> pd.DataFrame
#   - smart_open(path, mode="rt")   (gzip-aware context manager)
