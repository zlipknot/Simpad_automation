# SimPad Automation Tests

## Project Overview

This project contains automated UI tests for the **Laerdal SimPad (rcgui.exe)** application.  
The automation framework is written in Python (Pytest) and interacts with the application window
using pixel-relative coordinates and OCR-free deterministic actions.

Each step is based on fixed ratios (`rx`, `ry`) relative to the SimPad window client area
(480×640 px). This allows tests to run reliably on any monitor resolution or scaling setting.

---

## Test Environment Setup

### 1. Prerequisites
- **Windows 11**
- **Python 3.12+**
- **Visual Studio Code** (recommended editor)
- Installed dependencies:
  ```powershell
  pip install -r requirements.txt