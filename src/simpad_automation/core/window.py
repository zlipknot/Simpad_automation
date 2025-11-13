# -*- coding: utf-8 -*-
import time
import ctypes
from ctypes import wintypes

import pyautogui
import win32gui
import win32api
import win32con

# Setup pyautogui for stability
pyautogui.FAILSAFE = False
pyautogui.PAUSE = 0.02

# Compatibility: On some Python/Windows builds, wintypes does not have ULONG_PTR
if not hasattr(wintypes, "ULONG_PTR"):
    wintypes.ULONG_PTR = ctypes.c_uint64 if ctypes.sizeof(ctypes.c_void_p) == 8 else ctypes.c_ulong

# ---------- Base windows helpers ----------

def get_client_rect(hwnd):
    """
    Returns the coordinates of the window's client area (in screen coordinates) + diagnostics.
    {
      left, top, right, bottom, width, height
    }
    """
    try:
        if not win32gui.IsWindow(hwnd):
            print(f"[ERROR] HWND {hwnd} is not a valid window handle.")
            return None

        title = win32gui.GetWindowText(hwnd)
        l, t, r, b = win32gui.GetClientRect(hwnd)
        (left, top) = win32gui.ClientToScreen(hwnd, (l, t))
        (right, bottom) = win32gui.ClientToScreen(hwnd, (r, b))
        rect = {
            "left": left,
            "top": top,
            "right": right,
            "bottom": bottom,
            "width": right - left,
            "height": bottom - top,
        }
        print(f"[INFO] get_client_rect('{title}') -> {rect}")
        return rect
    except Exception as e:
        print(f"[ERROR] get_client_rect failed for hwnd={hwnd}: {e}")
        return None


def rel_to_abs(hwnd, rx: float, ry: float):
    """Convert client area fractions (rx, ry) to absolute screen coordinates (x, y)."""
    rect = get_client_rect(hwnd)
    if not rect:
        raise RuntimeError("rel_to_abs: client rect is not available")
    x = int(rect["left"] + rect["width"] * rx)
    y = int(rect["top"] + rect["height"] * ry)
    return x, y


def wait_foreground(hwnd, timeout=3.0):
    """Actively waits for the window to become foreground (we raise it to the background and focus it)."""
    t0 = time.time()
    while time.time() - t0 < timeout:
        try:
            if win32gui.GetForegroundWindow() == hwnd:
                return True
            win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
            win32gui.SetForegroundWindow(hwnd)
        except Exception:
            pass
        time.sleep(0.05)
    return False


# ---------- Clicks (with SendInput) ----------

user32 = ctypes.WinDLL("user32", use_last_error=True)

class MOUSEINPUT(ctypes.Structure):
    _fields_ = [
        ("dx", wintypes.LONG),
        ("dy", wintypes.LONG),
        ("mouseData", wintypes.DWORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", wintypes.ULONG_PTR),
    ]

class INPUT(ctypes.Structure):
    _fields_ = [("type", wintypes.DWORD), ("mi", MOUSEINPUT)]

INPUT_MOUSE = 0
MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP   = 0x0004

def _sendinput_click_left():
    """Reliable left-click via SendInput (good for touch/unusual UI)."""
    down = INPUT(type=INPUT_MOUSE, mi=MOUSEINPUT(0, 0, 0, MOUSEEVENTF_LEFTDOWN, 0, 0))
    up   = INPUT(type=INPUT_MOUSE, mi=MOUSEINPUT(0, 0, 0, MOUSEEVENTF_LEFTUP,   0, 0))
    user32.SendInput(1, ctypes.byref(down), ctypes.sizeof(INPUT))
    time.sleep(0.03)
    user32.SendInput(1, ctypes.byref(up), ctypes.sizeof(INPUT))


def click_relative(hwnd, rx: float, ry: float, delay: float = 0.1):
    """A single click on the relative coordinates of the client area.
        Returns the (x, y) coordinates of the actual click location.
    """
    wait_foreground(hwnd, timeout=1.0)
    x, y = rel_to_abs(hwnd, rx, ry)
    win32api.SetCursorPos((x, y))
    time.sleep(0.12)        
    _sendinput_click_left()
    time.sleep(delay)
    return x, y


def ensure_focus(hwnd, rx: float, ry: float):
    """Return focus to the window: double-click on the point (rx, ry) of the client area."""
    wait_foreground(hwnd, timeout=1.0)
    x, y = rel_to_abs(hwnd, rx, ry)
    win32api.SetCursorPos((x, y))
    time.sleep(0.12)
    _sendinput_click_left()
    time.sleep(0.06)
    _sendinput_click_left()
    time.sleep(0.2)


# ---------- Smooth dragging (drag) ----------

def drag_relative(hwnd,
                  rx_start: float, ry_start: float,
                  rx_end: float,   ry_end: float,
                  steps: int = 10, duration: float = 0.6):
    """ 
    Smooth dragging based on relative client area coordinates.
    - steps: number of intermediate points (10–15 is usually sufficient)
    - duration: total drag time (sec)
    """
    rect = get_client_rect(hwnd)
    if not rect:
        raise RuntimeError("drag_relative: client rect is not available")

    x0 = rect["left"] + rect["width"]  * rx_start
    y0 = rect["top"]  + rect["height"] * ry_start
    x1 = rect["left"] + rect["width"]  * rx_end
    y1 = rect["top"]  + rect["height"] * ry_end

    # Just in case, let's bring the window to the front before dragging.
    wait_foreground(hwnd, timeout=1.0)

    # Smooth movement
    pyautogui.moveTo(x0, y0)
    time.sleep(0.05)
    pyautogui.mouseDown()
    try:
        for i in range(1, steps + 1):
            t = i / steps
            x = x0 + (x1 - x0) * t
            y = y0 + (y1 - y0) * t
            pyautogui.moveTo(x, y)
            time.sleep(max(0.0, duration / steps))
    finally:
        pyautogui.mouseUp()
    time.sleep(0.1)