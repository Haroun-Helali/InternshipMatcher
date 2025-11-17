param(
  [ValidateSet("install","backend","frontend","all")]
  [string]$Task = "all"
)

$ErrorActionPreference = "Stop"

function Write-Section($text) { Write-Host "`n=== $text ===" -ForegroundColor Cyan }
function Write-Info($text) { Write-Host "$text" -ForegroundColor Gray }
function Write-Ok($text) { Write-Host "$text" -ForegroundColor Green }
function Write-Warn($text) { Write-Warning $text }

function Get-PythonCmd {
  if (Get-Command py -ErrorAction SilentlyContinue) { return "py -3.11" }
  elseif (Get-Command python -ErrorAction SilentlyContinue) { return "python" }
  else { throw "Python not found. Install Python 3.11 and retry." }
}

function Ensure-Venv {
  $python = Get-PythonCmd
  if (-not (Test-Path "venv")) {
    Write-Section "Create Python venv"
    & $python -m venv venv
  } else {
    Write-Info "venv already exists"
  }
  Write-Info "Activating venv"
  . "./venv/Scripts/Activate.ps1"
  Write-Ok "Python: $(python --version)"
}

function Install-BackendDeps {
  Write-Section "Install backend Python deps"
  python -m pip install --upgrade pip
  pip install -r requirements.txt
}

function Test-Ollama {
  try { $null = Invoke-WebRequest -Uri "http://localhost:11434/api/tags" -UseBasicParsing -TimeoutSec 3; return $true } catch { return $false }
}

function Ensure-Ollama {
  Write-Section "Ensure Ollama running"
  if (-not (Test-Ollama)) {
    Write-Info "Starting 'ollama serve' in background..."
    try {
      Start-Process -FilePath "ollama" -ArgumentList "serve" -WindowStyle Minimized | Out-Null
      Start-Sleep -Seconds 3
    } catch { Write-Warn "Failed to auto-start Ollama. Start it manually with: ollama serve" }
  }
  if (Test-Ollama) { Write-Ok "Ollama is reachable at http://localhost:11434" } else { Write-Warn "Ollama is not reachable; LLM calls will fail." }
}

function Install-FrontendDeps {
  Write-Section "Install frontend Node deps"
  Push-Location frontend
  try {
    if (-not (Test-Path "node_modules")) {
      if (Get-Command npm -ErrorAction SilentlyContinue) { npm install } else { Write-Warn "npm not found. Install Node.js 18+." }
    } else { Write-Info "node_modules present" }
  } finally { Pop-Location }
}

function Start-Backend {
  Write-Section "Start backend"
  $cmd = "& `"$PWD/venv/Scripts/Activate.ps1`"; python -m backend.app.main"
  Start-Process powershell -ArgumentList "-NoExit","-Command",$cmd -WindowStyle Minimized | Out-Null
  Write-Ok "Backend starting on http://localhost:8000"
}

function Start-Frontend {
  Write-Section "Start frontend"
  $cmd = "cd `"$PWD/frontend`"; if (-not (Test-Path node_modules)) { npm install }; npm run dev"
  Start-Process powershell -ArgumentList "-NoExit","-Command",$cmd -WindowStyle Minimized | Out-Null
  Write-Ok "Frontend starting on http://localhost:3000"
}

try {
  switch ($Task) {
    "install" {
      Ensure-Venv
      Install-BackendDeps
      Ensure-Ollama
      Install-FrontendDeps
      Write-Ok "Install complete"
    }
    "backend" {
      Ensure-Venv
      Start-Backend
    }
    "frontend" {
      Install-FrontendDeps
      Start-Frontend
    }
    "all" {
      Ensure-Venv
      Install-BackendDeps
      Ensure-Ollama
      Install-FrontendDeps
      Start-Backend
      Start-Frontend
      Write-Ok "All services starting"
    }
  }
} catch {
  Write-Error $_
  exit 1
}
