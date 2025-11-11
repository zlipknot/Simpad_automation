# -*- coding: utf-8 -*-
"""
Pytest bootstrap:
- adds src/ to sys.path
- provides app_ctx fixture (launch/close SimPad)
- on failure: captures client-only screenshot BEFORE window closes (with HR ROI)
"""

import os
import sys
import time
import pathlib
from datetime import datetime

if sys.platform != "win32":
    pytest.skip("Windows desktop required for UI tests", allow_module_level=True)

import pytest
import pyautogui

if sys.platform != "win32":
    # Этот conftest нужен только для UI на Windows
    pytest.skip("Windows desktop required for UI tests", allow_module_level=True)

# ---- 1) Make 'src' importable everywhere ----
ROOT_DIR = os.path.dirname(os.path.dirname(__file__))
SRC_DIR = os.path.join(ROOT_DIR, "src")
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

# ---- 2) Imports from project ----
from simpad_automation.core.app import launch_app, close_app
from simpad_automation.core.reporter import save_client_screenshot, attach_image_to_pytest_html

pyautogui.FAILSAFE = False
pyautogui.PAUSE = 0.02


@pytest.fixture()
def app_ctx(request):
    """
    Launch SimPad app once per test and close it in teardown.
    Stores hwnd on test node so makereport can screenshot before closing.
    """
    process, hwnd = launch_app()
    request.node._simpad_hwnd = hwnd
    request.node._simpad_process = process
    try:
        yield (process, hwnd)
    finally:
        try:
            close_app(process, hwnd)
        except Exception as e:
            print(f"[WARN] close_app failed: {e}")


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    """
    On test failure (call phase), capture client-only screenshot BEFORE window closes
    and overlay HR ROI if available.
    """
    outcome = yield
    rep = outcome.get_result()

    if rep.when != "call" or not rep.failed:
        return

    shots_dir = pathlib.Path(ROOT_DIR) / "artifacts" / "screenshots"
    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    fname = f"{item.name}_{ts}.png"
    path = shots_dir / fname

    hwnd = getattr(item, "_simpad_hwnd", None)
    try:
        save_client_screenshot(hwnd, path, draw_hr_roi=True)
        attach_image_to_pytest_html(rep, path)
        print(f"[SNAP] Saved failure screenshot with HR ROI: {path}")
    except Exception as e:
        print(f"[WARN] Could not capture client screenshot: {e}")
