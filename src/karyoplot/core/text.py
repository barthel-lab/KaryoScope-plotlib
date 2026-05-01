"""Text helpers for KaryoScope plotting (read names, distances, labels)."""

from __future__ import annotations


def format_genomic_distance(bp: int, *, style: str = "kb_short") -> str:
    """Format a base-pair count as a human-readable label.

    Styles:

    * ``"kb_short"`` (default) — ``"5 kb"`` for ≥ 1000 bp (integer division,
      lowercase ``kb``), ``"500 bp"`` otherwise. Matches the
      ``KaryoScope_cluster_plot.draw_scale_bar`` convention.
    * ``"auto"`` — ``"1 Mb"`` / ``"5 kb"`` / ``"500 bp"`` chosen by magnitude,
      decimal places shown only when meaningful. Matches the
      ``KaryoScope_assembly_contig_zoom_plot._format_genomic_pos`` convention.
    * ``"kbp"`` — ``"5 Kbp"`` (capital K). Matches the
      ``KaryoScope_telogator_reads_viz`` convention.

    Examples:
        >>> format_genomic_distance(5000)                 # default
        '5 kb'
        >>> format_genomic_distance(500)
        '500 bp'
        >>> format_genomic_distance(1_500_000, style="auto")
        '1.5 Mb'
        >>> format_genomic_distance(2_000_000, style="auto")
        '2 Mb'
        >>> format_genomic_distance(10_000, style="kbp")
        '10 Kbp'
    """
    if style == "kb_short":
        if bp >= 1000:
            return f"{bp // 1000} kb"
        return f"{bp} bp"
    if style == "kbp":
        return f"{bp // 1000} Kbp"
    if style == "auto":
        if bp >= 1_000_000:
            val = bp / 1_000_000
            return f"{int(val)} Mb" if val == int(val) else f"{val:.1f} Mb"
        if bp >= 1000:
            val = bp / 1000
            return f"{int(val)} kb" if val == int(val) else f"{val:.1f} kb"
        return f"{bp} bp"
    raise ValueError(f"unknown style {style!r}; use 'kb_short', 'kbp', or 'auto'")


def abbreviate_read_name(read_name: str, max_len: int = 12) -> str:
    """Abbreviate a read name to a short, unique-ish identifier.

    Handles common long-read naming conventions:

    - **PacBio HiFi** (``movie/zmw/ccs`` or ``movie/zmw/subread``) — returns
      the ZMW number (second slash-delimited part), truncated to ``max_len``.
    - **ONT / generic** — returns the first ``max_len`` characters.

    Examples:
        >>> abbreviate_read_name("m84132_240112_213928_s2/201131976/ccs")
        '201131976'
        >>> abbreviate_read_name("a1b2c3d4-e5f6-7890-abcd-ef1234567890")
        'a1b2c3d4-e5f'
        >>> abbreviate_read_name("short_name", max_len=20)
        'short_name'
    """
    if "/" in read_name:
        parts = read_name.split("/")
        if len(parts) >= 2:
            return parts[1][:max_len]
    return read_name[:max_len]
