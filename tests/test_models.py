from activy_checker.models import format_duration

from .conftest import make_activity


def test_format_duration():
    assert format_duration(0) == "0:00:00"
    assert format_duration(59) == "0:00:59"
    assert format_duration(3661) == "1:01:01"
    assert format_duration(36 * 3600 + 2 * 60 + 35) == "36:02:35"


def test_format_duration_handles_none():
    assert format_duration(None) == "0:00:00"


def test_duration_hms_property():
    a = make_activity("garmin", "2026-09-01", 12003)
    assert a.duration_hms == "3:20:03"
