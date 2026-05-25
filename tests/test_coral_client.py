"""Tests for Coral client utilities."""

import pytest

from devsecops_coral.coral_client import parse_since


def test_parse_since_days() -> None:
    assert parse_since("7d") == "INTERVAL '7' days"


def test_parse_since_hours() -> None:
    assert parse_since("24h") == "INTERVAL '24' hours"


def test_parse_since_invalid() -> None:
    with pytest.raises(ValueError):
        parse_since("invalid")
