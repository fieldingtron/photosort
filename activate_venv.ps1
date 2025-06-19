# Activate the Python virtual environment
# Run this script from PowerShell: .\activate_venv.ps1

Write-Host "Activating Python virtual environment..." -ForegroundColor Green
Set-Location $PSScriptRoot
.\venv\Scripts\Activate.ps1
Write-Host "Virtual environment activated!" -ForegroundColor Green
Write-Host "Python version:" -ForegroundColor Yellow
python --version
Write-Host "Installed packages:" -ForegroundColor Yellow
pip list
