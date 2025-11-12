Param(
  [switch]$Force  # recreate .venv if exists
)

$ErrorActionPreference = "Stop"

# Resolve project paths
$SCRIPT_DIR = Split-Path -Parent $PSCommandPath
$PROJECT_DIR = Split-Path -Parent $SCRIPT_DIR
Write-Host "== SimPad bootstrap ==" -ForegroundColor Cyan
Write-Host "Project root: $PROJECT_DIR"

# 1) Check Python
$py = Get-Command python -ErrorAction SilentlyContinue
if (-not $py) {
  Write-Host "Python not found in PATH. Please install Python 3.11+ and retry." -ForegroundColor Red
  exit 1
}

# 2) Create .venv
$venvPath = Join-Path $PROJECT_DIR ".venv"
if ((Test-Path $venvPath) -and $Force) {
  Write-Host "Removing existing .venv (force)..." -ForegroundColor Yellow
  Remove-Item -Recurse -Force $venvPath
}
if (-not (Test-Path $venvPath)) {
  Write-Host "Creating virtual environment..." -ForegroundColor Cyan
  python -m venv "$venvPath"
} else {
  Write-Host ".venv already exists - keeping it." -ForegroundColor Green
}

$venvBin = Join-Path $venvPath "Scripts"
$pip = Join-Path $venvBin "pip.exe"

# 3) Install deps
Write-Host "Installing dependencies..." -ForegroundColor Cyan
& "$pip" install --upgrade pip setuptools wheel
$req = Join-Path $PROJECT_DIR "requirements.txt"
if (Test-Path $req) {
  & "$pip" install -r "$req"
} else {
  & "$pip" install pytest pytest-html pytest-metadata
}

# 4) VS Code settings: disable pytest-html for VS Code runs
$vscodeDir = Join-Path $PROJECT_DIR ".vscode"
$settingsJson = Join-Path $vscodeDir "settings.json"
if (-not (Test-Path $vscodeDir)) { New-Item -ItemType Directory "$vscodeDir" | Out-Null }

# read existing settings if any
$settings = @{}
if (Test-Path $settingsJson) {
  try { $settings = Get-Content $settingsJson -Raw | ConvertFrom-Json } catch {}
}

$settings."python.defaultInterpreterPath" = (Join-Path $PROJECT_DIR ".venv\Scripts\python.exe")
$settings."python.testing.pytestEnabled" = $true
# Critical: prevents empty HTML reports from VS Code discovery
$settings."python.testing.pytestArgs" = @("-p","no:html","tests")
$settings."python.envFile" = (Join-Path $PROJECT_DIR ".env")
$settings."python.testing.autoTestDiscoverOnSaveEnabled" = $false

($settings | ConvertTo-Json -Depth 6) | Set-Content -Encoding UTF8 "$settingsJson"
Write-Host "VS Code configured (.vscode/settings.json)" -ForegroundColor Green

# 5) Clean pytest.ini from --html flags (backup once)
$pytestIni = Join-Path $PROJECT_DIR "pytest.ini"
if (Test-Path $pytestIni) {
  $ini = Get-Content $pytestIni -Raw
  if ($ini -match "--html" -or $ini -match "--self-contained-html") {
    $bak = "$pytestIni.bak"
    if (-not (Test-Path $bak)) { Copy-Item "$pytestIni" "$bak" }
    $ini2 = $ini -replace "(?ms)--html[^\r\n]*","" -replace "(?ms)--self-contained-html",""
    $ini2 = ($ini2 -replace "[ ]{2,}"," " -replace "[\t ]+`r?`n","`r`n").Trim()
    Set-Content -Path "$pytestIni" -Value $ini2 -Encoding UTF8
    Write-Host "Removed --html flags from pytest.ini (backup saved as pytest.ini.bak)" -ForegroundColor Yellow
  }
} else {
  @"
[pytest]
addopts = -q
markers =
    ui: UI tests requiring Windows
    e2e: end-to-end UI flows
"@ | Set-Content -Encoding UTF8 "$pytestIni"
  Write-Host "Created minimal pytest.ini" -ForegroundColor Green
}

# 6) Create run scripts
$runUi = Join-Path $SCRIPT_DIR "run_ui.ps1"
$runUnit = Join-Path $SCRIPT_DIR "run_unit.ps1"

@"
# Activate venv and run UI/E2E tests with HTML report
`$ts = Get-Date -Format 'yyyyMMdd_HHmmss'
`$env:PYTEST_HTML_TAG = `$ts
`$venv = '${venvPath}\Scripts\Activate.ps1'
. `$venv
pytest -m "ui or e2e" --html "reports/report_`$ts.html" --self-contained-html -q
"@ | Set-Content -Encoding UTF8 "$runUi"

@"
# Activate venv and run only unit tests (no HTML)
`$venv = '${venvPath}\Scripts\Activate.ps1'
. `$venv
pytest -m "not ui and not e2e" -q
"@ | Set-Content -Encoding UTF8 "$runUnit"

Write-Host ""
Write-Host "Bootstrap completed." -ForegroundColor Green
Write-Host "Run UI tests:   powershell -ExecutionPolicy Bypass -File scripts\run_ui.ps1"
Write-Host "Run unit tests: powershell -ExecutionPolicy Bypass -File scripts\run_unit.ps1"
