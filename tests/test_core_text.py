"""Unit tests for karyoplot.core.text."""

from karyoplot.core.text import abbreviate_read_name


def test_pacbio_format_returns_zmw():
    assert abbreviate_read_name("m84132_240112_213928_s2/201131976/ccs") == "201131976"


def test_pacbio_format_truncates_long_zmw():
    assert abbreviate_read_name("m1/123456789012345/ccs", max_len=12) == "123456789012"


def test_pacbio_subread_format():
    assert abbreviate_read_name("m54000_180101_000000/4194305/0_5000") == "4194305"


def test_ont_uuid_format():
    name = "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
    assert abbreviate_read_name(name) == "a1b2c3d4-e5f"


def test_generic_short_name_unchanged():
    assert abbreviate_read_name("short", max_len=20) == "short"


def test_max_len_zero_returns_empty():
    assert abbreviate_read_name("anything", max_len=0) == ""


def test_max_len_default_is_12():
    assert len(abbreviate_read_name("a" * 100)) == 12


def test_single_slash_no_second_part_falls_back():
    # Only one "/" — split gives 2 parts; returns parts[1] which may be empty
    assert abbreviate_read_name("foo/") == ""
    # Trailing slash with content
    assert abbreviate_read_name("foo/bar") == "bar"
