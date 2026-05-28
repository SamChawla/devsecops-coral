"""Tests for configuration helpers."""

import pytest

from devsecops_coral.config import parse_packages, validate_ecosystem, validate_package_name


def test_validate_package_name_accepts_valid() -> None:
    """Valid package names pass validation unchanged."""
    assert validate_package_name("django") == "django"
    assert validate_package_name("requests") == "requests"


def test_validate_package_name_rejects_invalid() -> None:
    """Package names with unsafe characters are rejected."""
    with pytest.raises(ValueError):
        validate_package_name("django; DROP TABLE")


def test_validate_ecosystem() -> None:
    """Valid ecosystem names pass validation unchanged."""
    assert validate_ecosystem("PyPI") == "PyPI"


def test_parse_packages() -> None:
    """Comma-separated package strings parse into a trimmed list."""
    assert parse_packages("django, flask,requests") == ["django", "flask", "requests"]
