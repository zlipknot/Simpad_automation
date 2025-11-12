$ts = Get-Date -Format 'yyyyMMdd_HHmmss'
$env:PYTEST_HTML_TAG = $ts
$venv = '.\.venv\Scripts\Activate.ps1'
. $venv
pytest -m "ui or e2e" --html "reports/report_$ts.html" --self-contained-html -q
