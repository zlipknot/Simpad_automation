# -*- coding: utf-8 -*-
"""
Device Information error (two popups) — test using universal OCR verifier + step-based reporting.
"""
import sys, pytest
if sys.platform != "win32":
    pytest.skip("Windows desktop required for UI tests", allow_module_level=True)

import time
from pathlib import Path

from simpad_automation.core.window import click_relative, get_client_rect
from simpad_automation.core.verify import assert_phrase_in_roi
from simpad_automation.core.reporter import step
from simpad_automation.ui import controls as ui

@pytest.mark.ui
def test_device_info_error_popup_two_steps(app_ctx, request):
    """
    FIRST popup after 'i' → OK → SECOND popup:
      - verify headline phrase in ROI (robust)
      - OK on second popup
    """
    process, hwnd = app_ctx
    artifacts = Path("artifacts") / "test_device_info_error_popup_two_steps"
    artifacts.mkdir(parents=True, exist_ok=True)

    # 1) Battery indicator
    with step(request, "Tap Battery indicator", hwnd, artifacts):
        click_relative(hwnd, *ui.BATTERY_INDICATOR)
        time.sleep(0.45)

    # 2) 'i' icon → FIRST popup
    with step(request, "Open FIRST popup via info icon", hwnd, artifacts):
        click_relative(hwnd, *ui.INFO_ICON)
        time.sleep(0.55)

    # 3) FIRST popup OK
    with step(request, "Confirm FIRST popup (OK)", hwnd, artifacts):
        click_relative(hwnd, *ui.POPUP_OK_TOPRIGHT)
        time.sleep(1.0)

    # 4) Verify SECOND popup headline via OCR
    with step(request, "Verify SECOND popup headline via OCR", hwnd, artifacts):
        rect = get_client_rect(hwnd)
        ok, details = assert_phrase_in_roi(
            hwnd,
            rect,
            ui.ERROR_HEAD_ROI,  # убедись, что актуально: (0.060, 0.295, 0.880, 0.085)
            "Unable to retrieve technical information",
            debug_name="device_info_headline",
            min_ratio=0.62,
            avg_threshold=0.80,
        )
        print("[OCR]", details)
        assert ok, f"OCR phrase check failed: {details}"

    # 5) SECOND popup OK
    with step(request, "Confirm SECOND popup (OK)", hwnd, artifacts):
        click_relative(hwnd, *ui.POPUP_OK_CENTER)
        time.sleep(0.4)
