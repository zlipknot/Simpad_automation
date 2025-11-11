# -*- coding: utf-8 -*-
"""
Full SimPad E2E test (steps 1–48) using relative UI-map controls and client-only
failure screenshots captured before window closes (via app_ctx fixture).
Requires EN-US keyboard layout.
"""

import time
import win32gui

from simpad_automation.core.window import click_relative, drag_relative, ensure_focus
from simpad_automation.core.input import type_text
from simpad_automation.core.ocr import read_hr_value
from simpad_automation.ui import controls as ui


def test_full_simpad_e2e_with_verification(app_ctx):
    """
    Runs full SimPad scenario 1–48 with HR verification and smooth drags.
    The 'app_ctx' fixture launches/closes the app; screenshots are taken on failure
    BEFORE the window is closed (client-only region).
    """
    process, hwnd = app_ctx  # launched by fixture
    print("[DEBUG] HWND:", hwnd, "| Title:", win32gui.GetWindowText(hwnd))

    # ---------------------- BASIC NAVIGATION ----------------------
    click_relative(hwnd, *ui.MANUAL_MODE);             time.sleep(0.3)
    click_relative(hwnd, *ui.STANDARDIZED_PATIENT);    time.sleep(3.0)
    click_relative(hwnd, *ui.HEALTHY);                 time.sleep(0.3)

    # ---------------------- NAME SESSION --------------------------
    click_relative(hwnd, *ui.NAME_SESSION_FIELD); time.sleep(0.2)
    click_relative(hwnd, *ui.CLEAR_BUTTON);       time.sleep(0.25)
    ensure_focus(hwnd, *ui.OVERLAY_FOCUS);        time.sleep(0.15)
    type_text("Test Automation session", interval=0.03); time.sleep(0.25)
    click_relative(hwnd, *ui.OK_BUTTON_SMALL);    time.sleep(0.5)

    # ---------------------- INSTRUCTOR ----------------------------
    click_relative(hwnd, *ui.INSTRUCTOR_FIELD); time.sleep(0.2)
    click_relative(hwnd, *ui.CLEAR_BUTTON);     time.sleep(0.25)
    ensure_focus(hwnd, *ui.OVERLAY_FOCUS);      time.sleep(0.15)
    type_text("test_instructor", interval=0.03); time.sleep(0.25)
    click_relative(hwnd, *ui.OK_BUTTON_SMALL);  time.sleep(0.4)

    # ---------------------- PARTICIPANT ---------------------------
    click_relative(hwnd, *ui.PARTICIPANT1_FIELD); time.sleep(0.2)
    click_relative(hwnd, *ui.CLEAR_BUTTON);       time.sleep(0.25)
    ensure_focus(hwnd, *ui.OVERLAY_FOCUS);        time.sleep(0.15)
    type_text("test_participant", interval=0.03); time.sleep(0.25)
    click_relative(hwnd, *ui.OK_BUTTON_SMALL);    time.sleep(0.6)

    # ---------------------- SESSION OK ----------------------------
    click_relative(hwnd, *ui.OK_BUTTON_LARGE); time.sleep(0.4)
    click_relative(hwnd, *ui.START_BUTTON);    time.sleep(0.4)

    # ---------------------- HR VERIFY BEFORE ----------------------
    hr_before = read_hr_value(hwnd, retries=4)
    print(f"[ASSERT] HR before = {hr_before}")
    assert hr_before == 80, f"Expected HR before == 80, got {hr_before}"

    # ---------------------- HR SCREEN -----------------------------
    click_relative(hwnd, *ui.HR_VALUE); time.sleep(0.3)
    drag_relative(hwnd, *ui.HR_SLIDER_START, *ui.HR_SLIDER_END, steps=10, duration=0.7)
    time.sleep(0.2)
    click_relative(hwnd, *ui.ACTIVATE_BUTTON); time.sleep(0.6)

    # ---------------------- HR VERIFY AFTER -----------------------
    hr_after = read_hr_value(hwnd, retries=4)
    print(f"[ASSERT] HR after = {hr_after}")
    assert hr_after == 100, f"Expected HR after == 100, got {hr_after}"

    # ---------------------- VOLUME SCREEN -------------------------
    click_relative(hwnd, *ui.VOLUME_BUTTON); time.sleep(0.5)

    for i in range(1, 10):
        start, end = ui.VOLUME_TOGGLES[i]
        print(f"[INFO] Drag volume toggle {i} {start} -> {end}")
        drag_relative(hwnd, *start, *end, steps=8, duration=0.5)
        time.sleep(0.2)

    # ---------------------- MESSAGE SCREEN ------------------------
    click_relative(hwnd, *ui.BACK_BUTTON);     time.sleep(0.3)
    click_relative(hwnd, *ui.MESSAGE_BUTTON);  time.sleep(0.5)
    click_relative(hwnd, *ui.COUGHING_BUTTON); time.sleep(0.3)
    click_relative(hwnd, *ui.BACK_BUTTON);     time.sleep(0.3)

    # ---------------------- END / QUIT ----------------------------
    click_relative(hwnd, *ui.END_BUTTON);  time.sleep(0.4)
    click_relative(hwnd, *ui.QUIT_BUTTON); time.sleep(0.4)

    print("[TEST DONE] SimPad full E2E scenario completed successfully.")
