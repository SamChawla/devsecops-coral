"""Tests for Coral client utilities."""

import pytest

from devsecops_coral.coral_client import parse_since


def test_parse_since_days() -> None:
    """Day durations convert to SQL INTERVAL literals."""
    assert parse_since("7d") == "INTERVAL '7' days"


def test_parse_since_hours() -> None:
    """Hour durations convert to SQL INTERVAL literals."""
    assert parse_since("24h") == "INTERVAL '24' hours"


def test_parse_since_invalid() -> None:
    """Invalid duration strings raise ValueError."""
    with pytest.raises(ValueError):
        parse_since("invalid")
