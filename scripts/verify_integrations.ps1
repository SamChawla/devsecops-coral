# Verify Coral sources and run smoke-test queries.
$ErrorActionPreference = "Continue"

$Coral = "wsl -d Ubuntu -e /root/.local/bin/coral"

Write-Host "=== Coral sources ==="
& wsl -d Ubuntu -e /root/.local/bin/coral source list

$expected = @("github", "osv", "sentry", "jira", "grafana")
$sourceList = & wsl -d Ubuntu -e /root/.local/bin/coral source list 2>&1 | Out-String

Write-Host "`n=== Connection status ==="
foreach ($name in $expected) {
    if ($sourceList -match "\b$name\b") {
        Write-Host "  [OK]   $name"
    }
    else {
        Write-Host "  [MISS] $name — run: wsl -d Ubuntu -e /root/.local/bin/coral source add --interactive $name"
    }
}

$owner = $env:GITHUB_OWNER
$repo = $env:GITHUB_REPO
if (-not $owner) {
    $envFile = Join-Path $PSScriptRoot "..\.env"
    if (Test-Path $envFile) {
        Get-Content $envFile | ForEach-Object {
            if ($_ -match "^GITHUB_OWNER=(.+)$") { $owner = $Matches[1].Trim() }
            if ($_ -match "^GITHUB_REPO=(.+)$") { $repo = $Matches[1].Trim() }
        }
    }
}
if (-not $repo) { $repo = "devsecops-coral" }

Write-Host "`n=== Smoke queries ==="

$queries = @{
    "osv"     = "SELECT id, severity FROM osv.search_vulnerabilities(package => 'django', ecosystem => 'PyPI') LIMIT 3"
    "github"  = "SELECT number, title FROM github.pulls WHERE owner = '$owner' AND repo = '$repo' LIMIT 3"
    "sentry"  = "SELECT title, level FROM sentry.issues LIMIT 3"
    "jira"    = "SELECT key, summary FROM jira.issues LIMIT 3"
    "grafana" = "SELECT name FROM grafana.alert_rules LIMIT 3"
}

foreach ($source in $queries.Keys) {
    Write-Host "`n--- $source ---"
    if ($sourceList -notmatch "\b$source\b") {
        Write-Host "  skipped (not connected)"
        continue
    }
    $sql = $queries[$source]
    & wsl -d Ubuntu -e /root/.local/bin/coral sql $sql 2>&1
}

Write-Host "`n=== CLI ==="
try {
    devsecops-coral integrations list 2>&1
}
catch {
    Write-Host "  devsecops-coral not on PATH — pip install -e ."
}

Write-Host "`n=== Dashboard API (optional) ==="
Write-Host "  Start server: devsecops-coral serve"
Write-Host "  Or dev mode:"
Write-Host "    Terminal 1: uvicorn devsecops_coral.api:app --reload"
Write-Host "    Terminal 2: cd frontend && npm run dev"
Write-Host "  Endpoints: /api/scan /api/correlate /api/timeline /api/posture /api/sources /api/ask"
