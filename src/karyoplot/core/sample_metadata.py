"""Sample metadata loader.

Unifies the two metadata loaders previously living in
``KaryoScope_cluster_plot.py`` (4-tuple return) and
``KaryoScope_cluster_analysis.py`` (3-tuple return).

The library returns a single :class:`SampleMetadata` bundle; each consumer
projects it into the shape it needs at the call site.
"""

from __future__ import annotations

import os
from collections.abc import Iterable
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class SampleMetadata:
    """Bundle of sample/group/color/display-name lookups loaded from a TSV.

    Attributes:
        sample_to_group: ``{sample_name: group_name}``.
        sample_to_color: ``{sample_name: hex_color}`` (from the ``color`` column).
        group_to_color: ``{group_name: hex_color}`` (from the explicit
            ``group_color`` column when present; empty otherwise).
        sample_to_display_name: ``{sample_name: display_label}``
            (from the ``display_name`` column when present; empty otherwise).
    """

    sample_to_group: dict[str, str] = field(default_factory=dict)
    sample_to_color: dict[str, str] = field(default_factory=dict)
    group_to_color: dict[str, str] = field(default_factory=dict)
    sample_to_display_name: dict[str, str] = field(default_factory=dict)

    def derive_group_colors_from_samples(self) -> dict[str, str]:
        """Build a ``{group: color}`` map from per-sample colors.

        First sample seen in each group wins (insertion order). Used by
        ``KaryoScope_cluster_plot.py`` which derives group colors implicitly
        rather than reading an explicit ``group_color`` column.
        """
        result: dict[str, str] = {}
        for sample, group in self.sample_to_group.items():
            if group not in result and sample in self.sample_to_color:
                result[group] = self.sample_to_color[sample]
        return result


def load_sample_metadata(
    metadata_file: str | os.PathLike | None,
    sample_labels: Iterable[str] | None = None,
    *,
    require_sample_column: bool = True,
    quiet: bool = False,
) -> SampleMetadata:
    """Load a sample-metadata TSV into a :class:`SampleMetadata` bundle.

    Args:
        metadata_file: Path to a TSV with at least a ``sample`` column.
            Optional additional columns: ``group``, ``color``,
            ``group_color``, ``display_name``. May be ``None``, in which case
            an empty :class:`SampleMetadata` is returned (and missing-sample
            fill from ``sample_labels`` still applies).
        sample_labels: If provided, samples not present in the metadata file
            are auto-filled as their own group (each missing sample → its own
            single-sample group). Mirrors the cluster_analysis behaviour.
        require_sample_column: If ``True`` (cluster_analysis behaviour), raise
            ``ValueError`` when the file is missing the ``sample`` column. If
            ``False`` (cluster_plot behaviour), swallow read errors with a
            warning and fall back to empty dicts.
        quiet: Suppress the standard ``"Loaded sample metadata: N samples"``
            log line and the missing-samples warning.

    Returns:
        A :class:`SampleMetadata` bundle.
    """
    import pandas as pd  # local import to keep core.io light when unused

    md = SampleMetadata()
    file_provided = metadata_file is not None
    file_exists = file_provided and Path(str(metadata_file)).exists()

    meta_df = None
    if file_exists:
        try:
            meta_df = pd.read_csv(metadata_file, sep="\t")
        except Exception as e:
            if require_sample_column:
                raise
            if not quiet:
                print(f"  Warning: Could not load sample metadata: {e}")
            meta_df = None

        if meta_df is not None and "sample" not in meta_df.columns:
            if require_sample_column:
                raise ValueError("Sample metadata file must have 'sample' column")
            meta_df = None  # cluster_plot tolerates this case silently

        if meta_df is not None:
            cols = set(meta_df.columns)
            for _, row in meta_df.iterrows():
                sample = row["sample"]
                group = row.get("group", sample) if "group" in cols else sample
                md.sample_to_group[sample] = group
                if "color" in cols and pd.notna(row.get("color")):
                    md.sample_to_color[sample] = row["color"]
                if "group_color" in cols and pd.notna(row.get("group_color")):
                    md.group_to_color[group] = row["group_color"]
                if "display_name" in cols and pd.notna(row.get("display_name")):
                    md.sample_to_display_name[sample] = row["display_name"]
            if not quiet:
                print(f"  Loaded sample metadata: {len(meta_df)} samples")

    # Auto-fill missing samples (cluster_analysis behaviour)
    if sample_labels is not None:
        sample_labels = list(sample_labels)
        missing = [s for s in sample_labels if s not in md.sample_to_group]
        if missing:
            if file_provided and meta_df is not None and not quiet:
                # Match the original message format: "Warning: Samples not in metadata file: {missing}"
                print(f"  Warning: Samples not in metadata file: {set(missing)}")
            for s in missing:
                md.sample_to_group[s] = s

    return md
