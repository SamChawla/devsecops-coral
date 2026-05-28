# Hit demo FastAPI endpoints to generate Sentry events.
# Start the app first: uvicorn main:app --reload --port 8000

$BaseUrl = if ($env:DEMO_APP_URL) { $env:DEMO_APP_URL } else { "http://localhost:8000" }
$Endpoints = @(
    "/vulnerable",
    "/unhandled",
    "/dependency-error",
    "/generate-errors"
)

Write-Host "Seeding Sentry errors via $BaseUrl ..."
foreach ($path in $Endpoints) {
    try {
        Invoke-WebRequest "$BaseUrl$path" -UseBasicParsing -TimeoutSec 30 | Out-Null
        Write-Host "  OK $path"
    }
    catch {
        Write-Host "  FAIL $path — $($_.Exception.Message)"
    }
}

Write-Host "Repeating /vulnerable (10x) and /unhandled (5x) for frequency..."
1..10 | ForEach-Object { Invoke-WebRequest "$BaseUrl/vulnerable" -UseBasicParsing -TimeoutSec 30 | Out-Null }
1..5 | ForEach-Object { Invoke-WebRequest "$BaseUrl/unhandled" -UseBasicParsing -TimeoutSec 30 | Out-Null }
Write-Host "Done. Check Sentry dashboard for new issues."
