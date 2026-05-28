"""Tests for output formatters."""

from devsecops_coral.formatters.json_output import to_json
from devsecops_coral.formatters.markdown_output import scan_markdown


def test_to_json_serializes_rows() -> None:
    """JSON formatter includes row data in output."""
    data = {"rows": [{"cve": "GHSA-1"}]}
    output = to_json(data)
    assert "GHSA-1" in output


def test_scan_markdown_includes_header() -> None:
    """Markdown scan report includes title and package rows."""
    md = scan_markdown([{"package": "django", "cve": "GHSA-1", "severity": "HIGH"}])
    assert "# Security Posture Scan" in md
    assert "django" in md
