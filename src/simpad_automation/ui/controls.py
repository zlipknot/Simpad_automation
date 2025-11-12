# -*- coding: utf-8 -*-
"""
UI Controls Map (relative coordinates for clicks / drags).
All values are fractions of the SimPad client area (≈480x640).
"""

# ----- Main navigation (from your first scenario) -----
MANUAL_MODE = (0.208, 0.331)
STANDARDIZED_PATIENT = (0.500, 0.281)
HEALTHY = (0.521, 0.811)

# Input screens
NAME_SESSION_FIELD = (0.525, 0.355)
CLEAR_BUTTON      = (0.406, 0.613)
OVERLAY_FOCUS     = (0.094, 0.500)
OK_BUTTON_SMALL   = (0.865, 0.606)
OK_BUTTON_LARGE   = (0.504, 0.888)

INSTRUCTOR_FIELD    = (0.406, 0.411)
PARTICIPANT1_FIELD  = (0.423, 0.467)

# Main screen
START_BUTTON = (0.646, 0.766)
HR_VALUE     = (0.667, 0.217)

# HR screen
HR_SLIDER_START  = (0.792, 0.584)
HR_SLIDER_END    = (0.792, 0.519)
ACTIVATE_BUTTON  = (0.694, 0.891)

# ---------- HR display ROI (relative to client rect) ----------
# Center/size picked to avoid truncating the 3rd digit (extra width/height margin)
HR_CX, HR_CY = 0.667, 0.217
HR_RW, HR_RH = 0.18, 0.14  # increased vs old 0.14/0.12
HR_RX = HR_CX - HR_RW / 2.0
HR_RY = HR_CY - HR_RH / 2.0

# Single source of truth for OCR/readers/overlays
HR_ROI = (HR_RX, HR_RY, HR_RW, HR_RH)

# Volume screen
VOLUME_BUTTON = (0.765, 0.933)

VOLUME_TOGGLES = {
    1: ((0.890, 0.377), (0.890, 0.298)),
    2: ((0.760, 0.377), (0.760, 0.298)),
    3: ((0.627, 0.377), (0.627, 0.298)),
    4: ((0.498, 0.377), (0.498, 0.298)),
    5: ((0.365, 0.377), (0.365, 0.298)),
    6: ((0.233, 0.377), (0.233, 0.298)),
    7: ((0.102, 0.377), (0.102, 0.298)),
    8: ((0.235, 0.748), (0.235, 0.677)),
    9: ((0.102, 0.748), (0.102, 0.673)),
}

# Message screen
BACK_BUTTON     = (0.121, 0.023)
MESSAGE_BUTTON  = (0.581, 0.939)
COUGHING_BUTTON = (0.263, 0.270)
END_BUTTON      = (0.821, 0.813)
QUIT_BUTTON     = (0.479, 0.922)

# ----- Device information / error flow -----
BATTERY_INDICATOR = (0.919, 0.033)
INFO_ICON         = (0.875, 0.152)

POPUP_OK_TOPRIGHT = (0.719, 0.483)
POPUP_OK_CENTER   = (0.500, 0.511)

# Заголовок без строки "Error: -1" (подняли вверх и сузили)
ERROR_HEAD_ROI = (0.060, 0.295, 0.880, 0.085)  # rx, ry, rw, rh  ← было ниже и выше по высоте

# Отдельный компактный ROI для "Error: -1" (если решим проверять код тоже)
ERROR_CODE_ROI = (0.420, 0.420, 0.220, 0.070)

ERROR_TEXT_EXPECTED = "Unable to retrieve technical information"
ERROR_CODE_EXPECTED = "Error: -1"
