"""Test Coral WSL integration from Python."""

from devsecops_coral.coral_client import execute_query


def main() -> None:
    """Run a sample OSV query via Coral and print row count."""
    rows = execute_query(
        "SELECT id, summary FROM osv.search_vulnerabilities"
        "(package => 'django', ecosystem => 'PyPI') LIMIT 2"
    )
    print(f"Got {len(rows)} rows")
    for row in rows:
        print(row)


if __name__ == "__main__":
    main()
