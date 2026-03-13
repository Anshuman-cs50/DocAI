# =============================================================================
# DocAI Startup Script
# Starts Docker, the PostgreSQL container, and the Flask dev server.
# Run from the project root: .\start.ps1
# =============================================================================

$PROJECT_ROOT = $PSScriptRoot
$CONTAINER_NAME = "postgres_ts_vector"
$DB_PORT = 5432
$DOCKER_IMAGE = "ankane/pgvector"
$POSTGRES_USER = "admin"
$POSTGRES_PASSWORD = "0987654321"
$POSTGRES_DB = "DocAI"

Write-Host ""
Write-Host "============================================" -ForegroundColor Cyan
Write-Host "   DocAI Startup Script" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""

# ── Step 1: Check / Start Docker Desktop ────────────────────────────────────
Write-Host "[1/4] Checking Docker Desktop..." -ForegroundColor Yellow

$dockerProcess = Get-Process "Docker Desktop" -ErrorAction SilentlyContinue
if (-not $dockerProcess) {
    Write-Host "      Docker Desktop is not running. Starting it..." -ForegroundColor Gray
    Start-Process "C:\Program Files\Docker\Docker\Docker Desktop.exe"

    Write-Host "      Waiting for Docker engine to become ready..." -ForegroundColor Gray
    $maxWait = 90   # seconds
    $elapsed = 0
    do {
        Start-Sleep -Seconds 3
        $elapsed += 3
        $dockerReady = (docker info 2>&1) -notmatch "error"
        if ($elapsed -ge $maxWait) {
            Write-Host "[ERROR] Docker didn't start within $maxWait seconds. Please start it manually." -ForegroundColor Red
            exit 1
        }
    } while (-not $dockerReady)

    Write-Host "      Docker Desktop is ready. ($elapsed s)" -ForegroundColor Green
} else {
    Write-Host "      Docker Desktop is already running." -ForegroundColor Green
}

# ── Step 2: Start / Resume PostgreSQL Container ──────────────────────────────
Write-Host ""
Write-Host "[2/4] Checking PostgreSQL container ($CONTAINER_NAME)..." -ForegroundColor Yellow

$containerExists = docker ps -a --format "{{.Names}}" | Where-Object { $_ -eq $CONTAINER_NAME }

if ($containerExists) {
    $containerRunning = docker ps --format "{{.Names}}" | Where-Object { $_ -eq $CONTAINER_NAME }
    if ($containerRunning) {
        Write-Host "      Container is already running." -ForegroundColor Green
    } else {
        Write-Host "      Container exists but is stopped. Starting it..." -ForegroundColor Gray
        docker start $CONTAINER_NAME | Out-Null
    }
} else {
    Write-Host "      Container not found. Creating and starting a new one..." -ForegroundColor Gray
    docker run -d `
        --name $CONTAINER_NAME `
        -e POSTGRES_USER=$POSTGRES_USER `
        -e POSTGRES_PASSWORD=$POSTGRES_PASSWORD `
        -e POSTGRES_DB=$POSTGRES_DB `
        -p "${DB_PORT}:5432" `
        $DOCKER_IMAGE | Out-Null
    Write-Host "      Container created." -ForegroundColor Green
}

# Wait until PostgreSQL is accepting connections
Write-Host "      Waiting for PostgreSQL to be ready..." -ForegroundColor Gray
$maxWait = 30
$elapsed = 0
do {
    Start-Sleep -Seconds 2
    $elapsed += 2
    $pgReady = docker exec $CONTAINER_NAME pg_isready -U $POSTGRES_USER -d $POSTGRES_DB 2>&1
    if ($elapsed -ge $maxWait) {
        Write-Host "[ERROR] PostgreSQL didn't become ready within $maxWait seconds." -ForegroundColor Red
        exit 1
    }
} while ($pgReady -notmatch "accepting connections")

Write-Host "      PostgreSQL is ready. ($elapsed s)" -ForegroundColor Green

# ── Step 3: Start Flask Server (persistent window) ───────────────────────────
Write-Host ""
Write-Host "[3/4] Starting Flask server..." -ForegroundColor Yellow

# Launch Flask in its own persistent window so it stays alive independently
Start-Process powershell.exe -ArgumentList "-NoExit", "-Command", "Set-Location '$PROJECT_ROOT'; python run.py"

# Poll http://127.0.0.1:5000 until Flask actually responds (can take 60-90s
# while BioBERT / ConsultationLLM load at startup)
$flaskReady = $false
$maxWait    = 120
$elapsed    = 0
Write-Host "      Waiting for Flask to be ready (BioBERT loads slowly -- up to ${maxWait}s)..." -ForegroundColor Gray

do {
    Start-Sleep -Seconds 5
    $elapsed += 5
    try {
        $res = Invoke-WebRequest -Uri "http://127.0.0.1:5000/" -TimeoutSec 3 -ErrorAction Stop
        $flaskReady = $true
    } catch [System.Net.WebException] {
        # Connection refused = still loading; any HTTP response = ready
        if ($_.Exception.Response -ne $null) { $flaskReady = $true }
    } catch { }

    if ($elapsed -ge $maxWait) {
        Write-Host "      [WARNING] Flask did not respond after ${maxWait}s. Check the Flask window for errors." -ForegroundColor Red
        break
    }
} while (-not $flaskReady)

if ($flaskReady) {
    Write-Host "      Flask is ready at http://127.0.0.1:5000 ($elapsed s)" -ForegroundColor Green
}

# ── Step 4: Start ngrok tunnel ───────────────────────────────────────────────
Write-Host ""
Write-Host "[4/4] Starting ngrok tunnel (port 5000)..." -ForegroundColor Yellow

# Verify ngrok is available
if (-not (Get-Command ngrok -ErrorAction SilentlyContinue)) {
    Write-Host "      [WARNING] ngrok not found in PATH. Skipping tunnel step." -ForegroundColor Red
    Write-Host "                Install ngrok from https://ngrok.com/download" -ForegroundColor Gray
    $ngrokUrl = $null
} else {
    # Kill any leftover ngrok processes first
    Stop-Process -Name "ngrok" -ErrorAction SilentlyContinue
    Start-Sleep -Seconds 2

    # WindowsApps aliases MUST run in an interactive powershell.exe window
    # Start-Job and Start-Process -FilePath both fail for App Execution Aliases
    Start-Process powershell.exe -ArgumentList "-NoExit", "-Command", "ngrok http 5000"

    # Poll the ngrok local API for up to 30 seconds
    $ngrokUrl = $null
    $maxWait  = 30
    $elapsed  = 0
    Write-Host "      Waiting for ngrok tunnel (up to $maxWait s)..." -ForegroundColor Gray

    do {
        Start-Sleep -Seconds 3
        $elapsed += 3
        try {
            $ngrokApi = Invoke-RestMethod -Uri "http://127.0.0.1:4040/api/tunnels" -ErrorAction Stop
            $https    = $ngrokApi.tunnels | Where-Object { $_.proto -eq "https" }
            if ($https) { $ngrokUrl = $https[0].public_url }
        } catch { }
    } while (-not $ngrokUrl -and $elapsed -lt $maxWait)
}

Write-Host ""
Write-Host "============================================" -ForegroundColor Green
Write-Host "   DocAI is fully running!" -ForegroundColor Green
Write-Host "============================================" -ForegroundColor Green
Write-Host ""
Write-Host "  Flask  ->  http://127.0.0.1:5000" -ForegroundColor White

if ($ngrokUrl) {
    Write-Host "  ngrok  ->  $ngrokUrl" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "  [Kaggle Secret to add]" -ForegroundColor Yellow
    Write-Host "     Name : DOCAI_SERVER_URL" -ForegroundColor Yellow
    Write-Host "     Value: $ngrokUrl" -ForegroundColor Yellow
} else {
    Write-Host "  ngrok  ->  [could not retrieve URL -- check ngrok window]" -ForegroundColor Red
    Write-Host "             Run: Invoke-RestMethod http://127.0.0.1:4040/api/tunnels" -ForegroundColor Gray
}

Write-Host ""
Write-Host "  Flask and ngrok are running in separate windows." -ForegroundColor DarkGray
Write-Host "  Close those windows to stop them." -ForegroundColor DarkGray
Write-Host ""
