# MemNet development helpers (PowerShell)
param(
    [Parameter(Position = 0)]
    [ValidateSet("setup", "test", "lint", "fmt", "cli")]
    [string]$Task = "setup"
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

function Ensure-Venv {
    if (-not (Test-Path ".venv\Scripts\python.exe")) {
        python -m venv .venv
    }
}

function Get-Python {
    Ensure-Venv
    return ".\.venv\Scripts\python.exe"
}

switch ($Task) {
    "setup" {
        Ensure-Venv
        & (Get-Python) -m pip install --upgrade pip
        & (Get-Python) -m pip install -e ".[dev]"
        Write-Host "Dev environment ready. Activate with: .\.venv\Scripts\Activate.ps1"
    }
    "test" {
        & (Get-Python) -m pytest
    }
    "lint" {
        & (Get-Python) -m ruff check src tests
    }
    "fmt" {
        & (Get-Python) -m ruff format src tests
        & (Get-Python) -m ruff check --fix src tests
    }
    "cli" {
        & (Get-Python) -m memnet --help
    }
}
