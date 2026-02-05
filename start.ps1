# Kenya Procurement AI - Quick Start
Write-Host "Starting Kenya Smart Procurement AI..." -ForegroundColor Cyan

# Check if venv exists
if (-not (Test-Path "venv")) {
    Write-Host "Creating virtual environment..." -ForegroundColor Yellow
    python -m venv venv
}

# Activate
Write-Host "Activating environment..." -ForegroundColor Yellow
.\venv\Scripts\Activate.ps1

# Check if requirements installed
try {
    python -c "import streamlit" 2>
    Write-Host "Dependencies already installed" -ForegroundColor Green
} catch {
    Write-Host "Installing dependencies..." -ForegroundColor Yellow
    pip install -r requirements.txt
}

# Run app
Write-Host "Starting Streamlit app..." -ForegroundColor Green
streamlit run ui/app.py
