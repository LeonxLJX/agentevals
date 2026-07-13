import pytest

from agentevals.streaming.incremental_processor import _normalize_ts


@pytest.mark.parametrize(
    ("raw_ts", "expected"),
    [
        (1770000000, 1770000000.0),  # seconds
        (1770000000000, 1770000000.0),  # milliseconds
        (1770000000000000, 1770000000.0),  # microseconds
        (1770000000000000000, 1770000000.0),  # nanoseconds
    ],
)
def test_normalizes_timestamp_units(raw_ts, expected):
    assert _normalize_ts(raw_ts) == expected


def test_normalizes_numeric_string():
    assert _normalize_ts("1770000000000000") == 1770000000.0


@pytest.mark.parametrize("raw_ts", [None, "invalid"])
def test_invalid_timestamp_returns_zero(raw_ts):
    # Preserve the existing fallback for missing or malformed timestamps.
    assert _normalize_ts(raw_ts) == 0.0
