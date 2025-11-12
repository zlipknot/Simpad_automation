Param(
  [switch]$Force # пересоздать .venv если уже есть
)

$ErrorActionPreference = "Stop"
$ROOT = Split-Path -Parent $PSCommandPath
$PROJ = Split-Path -Parent $ROOT

Write-Host "== SimPad bootstrap ==" -ForegroundColor Cyan
Write-Host "Project root: $PROJ"

# ---- 1) Проверка Python ----
$py = Get-Command python -ErrorAction SilentlyContinue
if (-not $py) {
  Write-Host "Python не найден в PATH. Установи Python 3.11+ и перезапусти." -ForegroundColor Red
  exit 1
}

# ---- 2) Создание виртуального окружения ----
$venvPath = Join-Path $PROJ ".venv"
if (Test-Path $venvPath -and $Force) {
  Write-Host "Удаляю старое .venv (force)..." -ForegroundColor Yellow
  Remove-Item -Recurse -Force $venvPath
}

if (-not (Test-Path $venvPath)) {
  Write-Host "Создаю новое окружение..." -ForegroundColor Cyan
  python -m venv $venvPath
} else {
  Write-Host "Окружение уже существует (.venv) — пропускаем создание." -ForegroundColor Green
}

$venvBin = Join-Path $venvPath "Scripts"
$pip = Join-Path $venvBin "pip.exe"

# ---- 3) Установка зависимостей ----
Write-Host "Обновляю pip и устанавливаю зависимости..." -ForegroundColor Cyan
& $pip install --upgrade pip setuptools wheel
if (Test-Path (Join-Path $PROJ "requirements.txt")) {
  & $pip install -r (Join-Path $PROJ "requirements.txt")
} else {
  & $pip install pytest pytest-html pytest-metadata
}

# ---- 4) Конфиг VSCode (без pytest-html при discovery) ----
$vscodeDir = Join-Path $PROJ ".vscode"
$settingsJson = Join-Path $vscodeDir "settings.json"
if (-not (Test-Path $vscodeDir)) {
  New-Item -ItemType Directory $vscodeDir | Out-Null
}

$settings = @{}
if (Test-Path $settingsJson) {
  try { $settings = Get-Content $settingsJson -Raw | ConvertFrom-Json } catch {}
}

$settings."python.defaultInterpreterPath" = "${PROJ}\.venv\Scripts\python.exe"
$settings."python.testing.pytestEnabled" = $true
$settings."python.testing.pytestArgs" = @("-p","no:html","tests")
$settings."python.envFile" = "${PROJ}\.env"
$settings."python.testing.autoTestDiscoverOnSaveEnabled" = $false

($settings | ConvertTo-Json -Depth 6) | Set-Content -Encoding UTF8 $settingsJson
Write-Host "VS Code настроен (.vscode/settings.json)" -ForegroundColor Green

# ---- 5) pytest.ini: почистим html-аргументы ----
$pytestIni = Join-Path $PROJ "pytest.ini"
if (Test-Path $pytestIni) {
  $ini = Get-Content $pytestIni -Raw
  if ($ini -match "--html") {
    $bak = "$pytestIni.bak"
    if (-not (Test-Path $bak)) { Copy-Item $pytestIni $bak }
    $ini2 = $ini -replace "(?ms)--html[^\r\n]*","" -replace "(?ms)--self-contained-html",""
    $ini2 = ($ini2 -replace "[ ]{2,}"," " -replace "[\t ]+`r?`n","`r`n").Trim()
    Set-Content -Path $pytestIni -Value $ini2 -Encoding UTF8
    Write-Host "Удалены --html параметры из pytest.ini (backup: $bak)" -ForegroundColor Yellow
  }
} else {
  @"
[pytest]
addopts = -q
markers =
    ui: UI tests requiring Windows
    e2e: end-to-end UI flows
"@ | Set-Content -Encoding UTF8 $pytestIni
  Write-Host "Создан базовый pytest.ini" -ForegroundColor Green
}

# ---- 6) Создаём run-скрипты ----
$runUi = Join-Path $ROOT "run_ui.ps1"
$runUnit = Join-Path $ROOT "run_unit.ps1"

@"
`$ts = Get-Date -Format 'yyyyMMdd_HHmmss'
`$env:PYTEST_HTML_TAG = `$ts
`$venv = '${venvPath}\Scripts\Activate.ps1'
. `$venv
pytest -m "ui or e2e" --html "reports/report_`$ts.html" --self-contained-html -q
"@ | Set-Content -Encoding UTF8 $runUi

@"
`$venv = '${venvPath}\Scripts\Activate.ps1'
. `$venv
pytest -m "not ui and not e2e" -q
"@ | Set-Content -Encoding UTF8 $runUnit

Write-Host "`n✅ Bootstrap завершён!" -ForegroundColor Green
Write-Host "Команды запуска:" -ForegroundColor Cyan
Write-Host "  scripts\run_ui.ps1   — UI/E2E тесты (с HTML отчётом)"
Write-Host "  scripts\run_unit.ps1 — юниты без отчёта"
