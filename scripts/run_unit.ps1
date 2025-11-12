$venv = '.\.venv\Scripts\Activate.ps1'
. $venv
pytest -m "not ui and not e2e" -q