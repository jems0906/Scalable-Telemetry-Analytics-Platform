param(
    [switch]$IncludeTests
)

$ErrorActionPreference = 'Stop'

Write-Host "[1/5] Starting TrailMetrics stack with Docker Compose..."
docker compose up --build -d | Out-Host

Write-Host "[2/5] Waiting for backend health endpoint..."
$healthy = $false
for ($i = 1; $i -le 30; $i++) {
    try {
        $health = Invoke-RestMethod -Uri "http://localhost:8000/health" -Method Get
        if ($health.status -eq "ok") {
            $healthy = $true
            break
        }
    }
    catch {
        # Backend may still be booting.
    }
    Start-Sleep -Seconds 2
}

if (-not $healthy) {
    throw "Backend did not become healthy in time."
}
Write-Host "Backend is healthy."

Write-Host "[3/5] Verifying auth and RBAC (viewer/operator)..."
$viewerLogin = Invoke-RestMethod -Uri "http://localhost:8000/auth/login" -Method Post -ContentType "application/json" -Body (@{ username = "viewer"; password = "viewer123" } | ConvertTo-Json)
$operatorLogin = Invoke-RestMethod -Uri "http://localhost:8000/auth/login" -Method Post -ContentType "application/json" -Body (@{ username = "operator"; password = "operator123" } | ConvertTo-Json)

$viewerToken = $viewerLogin.access_token
$operatorToken = $operatorLogin.access_token

$services = Invoke-RestMethod -Uri "http://localhost:8000/metrics/services" -Method Get -Headers @{ Authorization = "Bearer $viewerToken" }
Write-Host "Viewer read access OK. Services:" ($services.services -join ', ')

$viewerDenied = $false
try {
    Invoke-RestMethod -Uri "http://localhost:8000/slo/evaluate" -Method Post -Headers @{ Authorization = "Bearer $viewerToken" } | Out-Null
}
catch {
    if ($_.Exception.Response.StatusCode.value__ -eq 403) {
        $viewerDenied = $true
    }
}
if (-not $viewerDenied) {
    throw "Viewer role unexpectedly allowed operator action."
}
Write-Host "Viewer write restriction OK (403)."

$operatorEval = Invoke-RestMethod -Uri "http://localhost:8000/slo/evaluate" -Method Post -Headers @{ Authorization = "Bearer $operatorToken" }
Write-Host "Operator action OK. Evaluated services:" $operatorEval.evaluated

Write-Host "[4/5] Verifying alert history endpoint..."
$alerts = Invoke-RestMethod -Uri "http://localhost:8000/alerts/history?limit=5" -Method Get -Headers @{ Authorization = "Bearer $operatorToken" }
Write-Host "Alert history reachable. Returned entries:" $alerts.alerts.Count

if ($IncludeTests) {
    Write-Host "[5/5] Running backend automated tests..."
    & ".\.venv\Scripts\python.exe" -m pip install -r "backend/requirements-dev.txt" | Out-Host
    & ".\.venv\Scripts\python.exe" -m pytest "backend/tests" -q | Out-Host
}
else {
    Write-Host "[5/5] Skipping tests (use -IncludeTests to run them)."
}

Write-Host ""
Write-Host "TrailMetrics quick start and verification completed successfully."
Write-Host "Dashboard: http://localhost:5173"
Write-Host "API Docs:   http://localhost:8000/docs"
