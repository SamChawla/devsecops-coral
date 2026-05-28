# OSV Coral Source Spec

Custom Coral source for the [OSV (Open Source Vulnerabilities)](https://osv.dev) API.

## Install

```bash
coral source lint sources/osv/osv.yaml
coral source add --file sources/osv/osv.yaml
coral source test osv
```

## Tables & Functions

| Name | Type | Description |
|---|---|---|
| `osv.search_vulnerabilities` | Search function | Query by package + ecosystem via `POST /v1/query` |
| `osv.vulnerability_detail` | Table | Lookup by vulnerability ID via `GET /v1/vulns/{id}` |

## Example Queries

```sql
-- Search vulnerabilities for a package
SELECT id, summary, severity
FROM osv.search_vulnerabilities(package => 'django', ecosystem => 'PyPI')
LIMIT 10

-- Cross-source JOIN with GitHub
SELECT osv.id, osv.severity, g.title AS pr_title
FROM osv.search_vulnerabilities(package => 'django', ecosystem => 'PyPI') osv
LEFT JOIN github.pulls g ON g.state = 'merged'
LIMIT 20

-- Detail lookup
SELECT id, summary, details
FROM osv.vulnerability_detail
WHERE id = 'GHSA-xxxx-xxxx-xxxx'
```

## Schema Inspection

```bash
coral sql "SELECT * FROM coral.table_functions WHERE schema_name = 'osv'"
coral sql "SELECT * FROM coral.columns WHERE schema_name = 'osv'"
```

## Notes

- No authentication required (public API)
- DSL v3 with `search` function syntax (named arguments)
- Severity from `database_specific.severity` when available
