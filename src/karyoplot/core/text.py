"""Text helpers for KaryoScope plotting (read names, labels)."""

from __future__ import annotations


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
