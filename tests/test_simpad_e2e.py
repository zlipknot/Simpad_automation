# -*- coding: utf-8 -*-
"""
Full SimPad E2E test (granular steps) using relative UI-map controls and client-only
failure screenshots captured before window closes (via app_ctx fixture).
Requires EN-US keyboard layout.
"""
import sys, pytest
if sys.platform != "win32":
    pytest.skip("Windows desktop required for UI tests", allow_module_level=True)

import time
from pathlib import Path
import win32gui

from simpad_automation.core.window import click_relative, drag_relative, ensure_focus, get_client_rect
from simpad_automation.core.input import type_text
from simpad_automation.core.ocr import read_hr_value
from simpad_automation.core.reporter import step
from simpad_automation.ui import controls as ui


@pytest.mark.ui
def test_full_simpad_e2e_with_verification(app_ctx, request):
    """
    Runs full SimPad scenario with HR verification and smooth drags.
    The 'app_ctx' fixture launches/closes the app; screenshots are taken on failure
    BEFORE the window is closed (client-only region).
    """
    process, hwnd = app_ctx  # launched by fixture
    print("[DEBUG] HWND:", hwnd, "| Title:", win32gui.GetWindowText(hwnd))

    artifacts = Path("artifacts") / "test_full_simpad_e2e_with_verification"
    artifacts.mkdir(parents=True, exist_ok=True)
    rect = get_client_rect(hwnd)

    # ---------------------- BASIC NAVIGATION ----------------------
    with step(request, "Open Manual Mode", hwnd, artifacts):
        click_relative(hwnd, *ui.MANUAL_MODE); time.sleep(0.3)

    with step(request, "Open Standardized Patient", hwnd, artifacts):
        click_relative(hwnd, *ui.STANDARDIZED_PATIENT); time.sleep(3.0)

    with step(request, "Select Healthy", hwnd, artifacts):
        click_relative(hwnd, *ui.HEALTHY); time.sleep(0.3)

    # ---------------------- NAME SESSION --------------------------
    with step(request, "Focus 'Name session' field", hwnd, artifacts):
        click_relative(hwnd, *ui.NAME_SESSION_FIELD); time.sleep(0.2)

    with step(request, "Clear 'Name session' field", hwnd, artifacts):
        click_relative(hwnd, *ui.CLEAR_BUTTON); time.sleep(0.25)

    with step(request, "Ensure overlay focus (name)", hwnd, artifacts):
        ensure_focus(hwnd, *ui.OVERLAY_FOCUS); time.sleep(0.15)

    with step(request, "Type session name", hwnd, artifacts):
        type_text("Test Automation session", interval=0.03); time.sleep(0.25)

    with step(request, "Confirm name (OK small)", hwnd, artifacts):
        click_relative(hwnd, *ui.OK_BUTTON_SMALL); time.sleep(0.5)

    # ---------------------- INSTRUCTOR ----------------------------
    with step(request, "Focus 'Instructor' field", hwnd, artifacts):
        click_relative(hwnd, *ui.INSTRUCTOR_FIELD); time.sleep(0.2)

    with step(request, "Clear 'Instructor' field", hwnd, artifacts):
        click_relative(hwnd, *ui.CLEAR_BUTTON); time.sleep(0.25)

    with step(request, "Ensure overlay focus (instructor)", hwnd, artifacts):
        ensure_focus(hwnd, *ui.OVERLAY_FOCUS); time.sleep(0.15)

    with step(request, "Type instructor", hwnd, artifacts):
        type_text("test_instructor", interval=0.03); time.sleep(0.25)

    with step(request, "Confirm instructor (OK small)", hwnd, artifacts):
        click_relative(hwnd, *ui.OK_BUTTON_SMALL); time.sleep(0.4)

    # ---------------------- PARTICIPANT ---------------------------
    with step(request, "Focus 'Participant #1' field", hwnd, artifacts):
        click_relative(hwnd, *ui.PARTICIPANT1_FIELD); time.sleep(0.2)

    with step(request, "Clear 'Participant #1' field", hwnd, artifacts):
        click_relative(hwnd, *ui.CLEAR_BUTTON); time.sleep(0.25)

    with step(request, "Ensure overlay focus (participant)", hwnd, artifacts):
        ensure_focus(hwnd, *ui.OVERLAY_FOCUS); time.sleep(0.15)

    with step(request, "Type participant #1", hwnd, artifacts):
        type_text("test_participant", interval=0.03); time.sleep(0.25)

    with step(request, "Confirm participant (OK small)", hwnd, artifacts):
        click_relative(hwnd, *ui.OK_BUTTON_SMALL); time.sleep(0.6)

    # ---------------------- SESSION OK / START --------------------
    with step(request, "Confirm Session (OK large)", hwnd, artifacts):
        click_relative(hwnd, *ui.OK_BUTTON_LARGE); time.sleep(0.4)

    with step(request, "Press START", hwnd, artifacts):
        click_relative(hwnd, *ui.START_BUTTON); time.sleep(0.4)

    # ---------------------- HR VERIFY BEFORE ----------------------
    with step(request, "Verify HR baseline == 80", hwnd, artifacts):
        hr_before = read_hr_value(hwnd, retries=4)
        print(f"[ASSERT] HR before = {hr_before}")
        assert hr_before == 80, f"Expected HR before == 80, got {hr_before}"

    # ---------------------- HR SCREEN (ADJUST) --------------------
    with step(request, "Open HR slider", hwnd, artifacts):
        click_relative(hwnd, *ui.HR_VALUE); time.sleep(0.3)

    with step(request, "Drag HR slider", hwnd, artifacts):
        drag_relative(hwnd, *ui.HR_SLIDER_START, *ui.HR_SLIDER_END, steps=10, duration=0.7)
        time.sleep(0.2)

    with step(request, "Activate HR change", hwnd, artifacts):
        click_relative(hwnd, *ui.ACTIVATE_BUTTON); time.sleep(0.6)

    # ---------------------- HR VERIFY AFTER -----------------------
    with step(request, "Verify HR after == 100", hwnd, artifacts):
        hr_after = read_hr_value(hwnd, retries=4)
        print(f"[ASSERT] HR after = {hr_after}")
        assert hr_after == 100, f"Expected HR after == 100, got {hr_after}"

    # ---------------------- VOLUME SCREEN -------------------------
    with step(request, "Open Volume screen", hwnd, artifacts):
        click_relative(hwnd, *ui.VOLUME_BUTTON); time.sleep(0.5)

    for i in range(1, 10):
        start, end = ui.VOLUME_TOGGLES[i]
        with step(request, f"Adjust volume toggle {i}", hwnd, artifacts):
            print(f"[INFO] Drag volume toggle {i} {start} -> {end}")
            drag_relative(hwnd, *start, *end, steps=8, duration=0.5)
            time.sleep(0.2)

    # ---------------------- MESSAGE SCREEN ------------------------
    with step(request, "Go back from Volume", hwnd, artifacts):
        click_relative(hwnd, *ui.BACK_BUTTON); time.sleep(0.3)

    with step(request, "Open Message screen", hwnd, artifacts):
        click_relative(hwnd, *ui.MESSAGE_BUTTON); time.sleep(0.5)

    with step(request, "Select 'Coughing' message", hwnd, artifacts):
        click_relative(hwnd, *ui.COUGHING_BUTTON); time.sleep(0.3)

    with step(request, "Back from Message screen", hwnd, artifacts):
        click_relative(hwnd, *ui.BACK_BUTTON); time.sleep(0.3)

    # ---------------------- END / QUIT ----------------------------
    with step(request, "Open End menu", hwnd, artifacts):
        click_relative(hwnd, *ui.END_BUTTON); time.sleep(0.4)

    with step(request, "Quit session", hwnd, artifacts):
        click_relative(hwnd, *ui.QUIT_BUTTON); time.sleep(0.4)

    print("[TEST DONE] SimPad full E2E scenario completed successfully.")