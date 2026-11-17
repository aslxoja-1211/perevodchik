# =========================================================
# Ovozli Tarjimon — Ishga Tushirish Skripti (PowerShell)
# =========================================================

$ErrorActionPreference = "Stop"

Write-Host "=================================================" -ForegroundColor Cyan
Write-Host "  Ovozli Tarjimon (Uzbek -> Russian Voice AI)   " -ForegroundColor Yellow
Write-Host "=================================================" -ForegroundColor Cyan

# 1. Python virtual muhitini aniqlash
$LocalVenv = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
$AquaVenv = Join-Path $PSScriptRoot "..\aqua voice\backend\.venv\Scripts\python.exe"

$PythonExe = $null
if (Test-Path $LocalVenv) {
    $PythonExe = $LocalVenv
} elseif (Test-Path $AquaVenv) {
    $PythonExe = $AquaVenv
    Write-Host "[OK] Aqua Voice mavjud Python muhiti ulandi." -ForegroundColor Green
} else {
    Write-Host "[...] Yangi virtual muhit yaratilmoqda..." -ForegroundColor Yellow
    python -m venv (Join-Path $PSScriptRoot ".venv")
    $PythonExe = $LocalVenv
    & $PythonExe -m pip install --upgrade pip
    & $PythonExe -m pip install -r (Join-Path $PSScriptRoot "requirements.txt")
}

# 2. .env mavjudligini tekshirish
$EnvPath = Join-Path $PSScriptRoot ".env"
$EnvExPath = Join-Path $PSScriptRoot ".env.example"
if (-not (Test-Path $EnvPath)) {
    if (Test-Path $EnvExPath) {
        Copy-Item $EnvExPath $EnvPath
        Write-Host "[OK] .env.example dan .env nusxalandi." -ForegroundColor Green
    }
}

# Mahalliy Wi-Fi / Tarmoq IP manzilini topish
$LanIP = "127.0.0.1"
try {
    $foundIp = (Get-NetIPAddress -AddressFamily IPv4 -ErrorAction SilentlyContinue | Where-Object { 
        $_.InterfaceAlias -notmatch "Loopback" -and $_.IPAddress -notmatch "^169\.254\." 
    } | Select-Object -ExpandProperty IPAddress -First 1)
    if ($foundIp) { $LanIP = $foundIp }
} catch {}

Write-Host "`n[+] Server ishga tushirilmoqda..." -ForegroundColor Cyan
Write-Host "    - Web interfeys (Lokal): http://127.0.0.1:8000" -ForegroundColor White
Write-Host "    - Android / Wi-Fi IP:    http://${LanIP}:8000" -ForegroundColor Yellow
Write-Host "    - API Docs:              http://127.0.0.1:8000/docs" -ForegroundColor White
Write-Host "    - Health check:          http://127.0.0.1:8000/health`n" -ForegroundColor White

Set-Location $PSScriptRoot
& $PythonExe -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
