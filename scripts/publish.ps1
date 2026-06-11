# Build and upload memnet-llm to PyPI.
# Prerequisites: pip install hatch twine
# Auth: $env:TWINE_USERNAME = "__token__"; $env:TWINE_PASSWORD = "<pypi-api-token>"

$ErrorActionPreference = "Stop"
Set-Location (Resolve-Path (Join-Path $PSScriptRoot ".."))

Write-Host "Building sdist + wheel..."
python -m hatch build
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "Checking dist..."
python -m twine check dist/*
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

if (-not $env:TWINE_PASSWORD) {
    Write-Host ""
    Write-Host "Set TWINE_USERNAME=__token__ and TWINE_PASSWORD, then re-run with -Upload"
    Write-Host "  .\scripts\publish.ps1 -Upload"
    exit 0
}

if ($args -contains "-Upload") {
    Write-Host "Uploading to PyPI..."
    python -m twine upload dist/*
} else {
    Write-Host "Build OK. Run: .\scripts\publish.ps1 -Upload"
}
