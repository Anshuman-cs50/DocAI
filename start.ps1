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
Write-Host "[1/3] Checking Docker Desktop..." -ForegroundColor Yellow

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
Write-Host "[2/3] Checking PostgreSQL container ($CONTAINER_NAME)..." -ForegroundColor Yellow

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

# ── Step 3: Start Flask Server ───────────────────────────────────────────────
Write-Host ""
Write-Host "[3/3] Starting Flask server..." -ForegroundColor Yellow
Write-Host ""
Write-Host "--------------------------------------------" -ForegroundColor DarkGray
Write-Host "  Server:  http://127.0.0.1:5000" -ForegroundColor White
Write-Host "  Stop:    Ctrl+C" -ForegroundColor White
Write-Host "--------------------------------------------" -ForegroundColor DarkGray
Write-Host ""

Set-Location $PROJECT_ROOT
python run.py
