# Setup script for Internship RAG Application
# Run this script to set up your development environment

Write-Host "Internship RAG Application - Setup Script" -ForegroundColor Cyan
Write-Host "=============================================" -ForegroundColor Cyan
Write-Host ""

# Check Python version
Write-Host "Checking Python version..." -ForegroundColor Yellow
$pythonVersion = python --version 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Python is not installed or not in PATH" -ForegroundColor Red
    Write-Host "Please install Python 3.10+ from https://www.python.org/downloads/" -ForegroundColor Red
    exit 1
}
Write-Host "SUCCESS: $pythonVersion" -ForegroundColor Green

# Check if virtual environment exists
if (Test-Path "venv") {
    Write-Host "WARNING: Virtual environment already exists" -ForegroundColor Yellow
    $response = Read-Host "Do you want to recreate it? (y/N)"
    if (($response -eq "y") -or ($response -eq "Y")) {
        Write-Host "Removing existing virtual environment..." -ForegroundColor Yellow
        Remove-Item -Recurse -Force venv
    } else {
        Write-Host "SUCCESS: Using existing virtual environment" -ForegroundColor Green
    }
}

# Create virtual environment
if (-not (Test-Path "venv")) {
    Write-Host "Creating virtual environment..." -ForegroundColor Yellow
    python -m venv venv
    if ($LASTEXITCODE -ne 0) {
        Write-Host "ERROR: Failed to create virtual environment" -ForegroundColor Red
        exit 1
    }
    Write-Host "SUCCESS: Virtual environment created" -ForegroundColor Green
}

# Activate virtual environment
Write-Host "Activating virtual environment..." -ForegroundColor Yellow
& ".\venv\Scripts\Activate.ps1"

# Upgrade pip
Write-Host "Upgrading pip..." -ForegroundColor Yellow
python -m pip install --upgrade pip --quiet

# Install dependencies
Write-Host "Installing Python dependencies..." -ForegroundColor Yellow
Write-Host "This may take a few minutes..." -ForegroundColor Gray
pip install -r requirements.txt --quiet
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Failed to install dependencies" -ForegroundColor Red
    exit 1
}
Write-Host "SUCCESS: Dependencies installed" -ForegroundColor Green

# Create .env file if it doesn't exist
if (-not (Test-Path ".env")) {
    Write-Host "Creating .env file from template..." -ForegroundColor Yellow
    Copy-Item .env.example .env
    Write-Host "SUCCESS: .env file created" -ForegroundColor Green
    Write-Host "WARNING: Please review and update .env with your settings" -ForegroundColor Yellow
} else {
    Write-Host "SUCCESS: .env file already exists" -ForegroundColor Green
}

# Create necessary directories
Write-Host "Creating necessary directories..." -ForegroundColor Yellow
$directories = @("logs", "chroma_data", "uploads", "temp_files")
foreach ($dir in $directories) {
    if (-not (Test-Path $dir)) {
        New-Item -ItemType Directory -Path $dir -Force | Out-Null
        Write-Host "  Created $dir/" -ForegroundColor Green
    }
}

# Check Ollama installation
Write-Host ""
Write-Host "Checking Ollama installation..." -ForegroundColor Yellow
try {
    $ollamaVersion = ollama --version 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "SUCCESS: Ollama is installed" -ForegroundColor Green
        
        # Check required models
        Write-Host "Checking required models..." -ForegroundColor Yellow
        $ollamaList = ollama list 2>&1 | Out-String
        
        $requiredModels = @("llama3.2", "mxbai-embed-large")
        $missingModels = @()
        
        foreach ($model in $requiredModels) {
            if ($ollamaList -notmatch $model) {
                $missingModels += $model
            }
        }
        
        if ($missingModels.Count -gt 0) {
            Write-Host "WARNING: Missing Ollama models:" -ForegroundColor Yellow
            foreach ($model in $missingModels) {
                Write-Host "  - $model" -ForegroundColor Yellow
            }
            Write-Host ""
            Write-Host "To download missing models, run:" -ForegroundColor Cyan
            foreach ($model in $missingModels) {
                Write-Host "  ollama pull $model`:latest" -ForegroundColor White
            }
        } else {
            Write-Host "SUCCESS: All required Ollama models are installed" -ForegroundColor Green
        }
    }
} catch {
    Write-Host "ERROR: Ollama is not installed or not in PATH" -ForegroundColor Red
    Write-Host "Please install Ollama from https://ollama.ai/download" -ForegroundColor Red
}

# Run tests
Write-Host ""
Write-Host "Running tests..." -ForegroundColor Yellow
pytest tests/unit/test_config.py -v
if ($LASTEXITCODE -eq 0) {
    Write-Host "SUCCESS: Tests passed" -ForegroundColor Green
} else {
    Write-Host "WARNING: Some tests failed - this is expected if dependencies aren't fully installed" -ForegroundColor Yellow
}

# Final summary
Write-Host ""
Write-Host "=============================================" -ForegroundColor Cyan
Write-Host "Setup Complete!" -ForegroundColor Green
Write-Host "=============================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Cyan
Write-Host "1. Review and update .env file if needed" -ForegroundColor White
Write-Host "2. Ensure Ollama models are downloaded (see above)" -ForegroundColor White
Write-Host "3. Run the application:" -ForegroundColor White
Write-Host "   python -m backend.app.main" -ForegroundColor Yellow
Write-Host "4. Visit http://localhost:8000/api/v1/docs" -ForegroundColor White
Write-Host ""
Write-Host "For more information, see README.md" -ForegroundColor Gray
Write-Host ""
