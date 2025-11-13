# SimPad Automation Tests

UI automation & OCR-based verification for Laerdal **SimPad**.  
Runs on Windows with client-area screenshots, step-by-step HTML reports, and clean separation of UI/E2E vs unit tests.

>  **Important:** Before running UI tests, switch your system **keyboard layout to English (EN-US) / (EN-UK)**.  
> Text input relies on English layout — incorrect layout will break tests.

---

## 1. Requirements

1. **OS**
   - Windows 10 (x64) or Windows 11 (x64)

2. **Python**
   - Version 3.11 or 3.12
   - Must be added to `PATH`

3. **Tesseract OCR**
   - Installed and available in `PATH`
   - Typical installation path:
     - `C:\Program Files\Tesseract-OCR\`
   - `tesseract.exe` should be callable from the terminal:
     ```powershell
     tesseract --version
     ```

4. **SimPad application**
   - Installed and runnable on the machine
   - If the path differs from the default, adjust it in:
     ```text
     src/simpad_automation/core/app.py
     ```

5. **Git**
   - Used to clone the repository:
     ```powershell
     git --version
     ```

6. **Keyboard layout**
   - Must be set to **English (EN-US)** before running UI tests:
     - Use `Win + Space` until you see `ENG`.
---

## 2. Quick Start (Recommended, via Scripts)

### 2.1 Clone the repository
```powershell
git clone https://github.com/zlipknot/Simpad_automation.git
cd Simpad_automation
```

### 2.2 Run bootstrap script (one-time setup)
```powershell
powershell -ExecutionPolicy Bypass -File scripts\bootstrap.ps1
```

### 2.3 Run UI/E2E tests (HTML report)
```powershell
powershell -ExecutionPolicy Bypass -File scripts\run_ui.ps1
```
### 2.4 Run unit tests only
```powershell
powershell -ExecutionPolicy Bypass -File scripts\run_unit.ps1
```

## 2. Manual Installation and Running (Without Scripts)

### 3.1 Create and activate virtual environment
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### 3.2 Install dependencies
```powershell
pip install --upgrade pip
pip install -r requirements.txt
```

### 3.3 Verify Tesseract is available
```powershell
tesseract --version
```

### 3.4 Run UI/E2E tests manually with HTML report
```powershell
pytest -s -v tests
```

