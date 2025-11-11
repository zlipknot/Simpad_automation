# -*- coding: utf-8 -*-
"""
Device Information error (two popups) — test using universal OCR verifier.
"""
import sys, pytest
if sys.platform != "win32":
    pytest.skip("Windows desktop required for UI tests", allow_module_level=True)
    
import time

from simpad_automation.core.window import click_relative, get_client_rect
from simpad_automation.core.verify import assert_phrase_in_roi
from simpad_automation.ui import controls as ui


def test_device_info_error_popup_two_steps(app_ctx):
    """
    FIRST popup after 'i' → OK → SECOND popup:
      - verify headline phrase in ROI (robust)
      - OK on second popup
    """
    process, hwnd = app_ctx

    # 2) Battery indicator
    click_relative(hwnd, *ui.BATTERY_INDICATOR); time.sleep(0.45)

    # 3) 'i' icon → FIRST popup
    click_relative(hwnd, *ui.INFO_ICON); time.sleep(0.55)

    # 4) FIRST popup OK
    click_relative(hwnd, *ui.POPUP_OK_TOPRIGHT); time.sleep(1.0)

    # 5) verify headline of SECOND popup
    rect = get_client_rect(hwnd)
    ok, details = assert_phrase_in_roi(
        hwnd,
        rect,
        ui.ERROR_HEAD_ROI,  # убедись, что обновлён: (0.060, 0.295, 0.880, 0.085)
        "Unable to retrieve technical information",
        debug_name="device_info_headline",
        min_ratio=0.62,
        avg_threshold=0.80,
    )
    print("[OCR]", details)
    assert ok, f"OCR phrase check failed: {details}"

    # 6) SECOND popup OK
    click_relative(hwnd, *ui.POPUP_OK_CENTER); time.sleep(0.4)
