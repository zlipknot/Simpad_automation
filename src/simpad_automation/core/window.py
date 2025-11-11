# -*- coding: utf-8 -*-
import time
import ctypes
from ctypes import wintypes

import pyautogui
import win32gui
import win32api
import win32con

# Настройки pyautogui для стабильности
pyautogui.FAILSAFE = False
pyautogui.PAUSE = 0.02

# Совместимость: на некоторых сборках Python/Windows в wintypes нет ULONG_PTR
if not hasattr(wintypes, "ULONG_PTR"):
    wintypes.ULONG_PTR = ctypes.c_uint64 if ctypes.sizeof(ctypes.c_void_p) == 8 else ctypes.c_ulong

# ---------- БАЗОВЫЕ ХЕЛПЕРЫ ОКНА ----------

def get_client_rect(hwnd):
    """
    Возвращает координаты клиентской области окна (в screen-координатах) + диагностику.
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
    """Перевод долей (rx, ry) клиентской области → абсолютные экранные координаты (x, y)."""
    rect = get_client_rect(hwnd)
    if not rect:
        raise RuntimeError("rel_to_abs: client rect is not available")
    x = int(rect["left"] + rect["width"] * rx)
    y = int(rect["top"] + rect["height"] * ry)
    return x, y


def wait_foreground(hwnd, timeout=3.0):
    """Активно ждёт, пока окно станет foreground (фоном поднимаем и фокусируем)."""
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


# ---------- КЛИКИ (через SendInput) ----------

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
    """Надёжный клик ЛКМ через SendInput (хорошо для touch/необычных UI)."""
    down = INPUT(type=INPUT_MOUSE, mi=MOUSEINPUT(0, 0, 0, MOUSEEVENTF_LEFTDOWN, 0, 0))
    up   = INPUT(type=INPUT_MOUSE, mi=MOUSEINPUT(0, 0, 0, MOUSEEVENTF_LEFTUP,   0, 0))
    user32.SendInput(1, ctypes.byref(down), ctypes.sizeof(INPUT))
    time.sleep(0.03)
    user32.SendInput(1, ctypes.byref(up), ctypes.sizeof(INPUT))


def click_relative(hwnd, rx: float, ry: float, delay: float = 0.1):
    """
    Одиночный клик по относительным координатам клиентской области.
    Возвращает (x, y) фактической точки клика.
    """
    wait_foreground(hwnd, timeout=1.0)
    x, y = rel_to_abs(hwnd, rx, ry)
    win32api.SetCursorPos((x, y))
    time.sleep(0.12)          # даём UI «осесть» (hit-test)
    _sendinput_click_left()
    time.sleep(delay)
    return x, y


def ensure_focus(hwnd, rx: float, ry: float):
    """Вернуть фокус окну: двойной клик в точку (rx, ry) клиентской области."""
    wait_foreground(hwnd, timeout=1.0)
    x, y = rel_to_abs(hwnd, rx, ry)
    win32api.SetCursorPos((x, y))
    time.sleep(0.12)
    _sendinput_click_left()
    time.sleep(0.06)
    _sendinput_click_left()
    time.sleep(0.2)


# ---------- ПЛАВНОЕ ПЕРЕТАСКИВАНИЕ (drag) ----------

def drag_relative(hwnd,
                  rx_start: float, ry_start: float,
                  rx_end: float,   ry_end: float,
                  steps: int = 10, duration: float = 0.6):
    """
    Плавное перетаскивание по относительным координатам клиентской области.
    - steps: число промежуточных точек (10–15 обычно достаточно)
    - duration: общее время drag (сек)
    """
    rect = get_client_rect(hwnd)
    if not rect:
        raise RuntimeError("drag_relative: client rect is not available")

    x0 = rect["left"] + rect["width"]  * rx_start
    y0 = rect["top"]  + rect["height"] * ry_start
    x1 = rect["left"] + rect["width"]  * rx_end
    y1 = rect["top"]  + rect["height"] * ry_end

    # На всякий случай поднимем окно на передний план перед drag
    wait_foreground(hwnd, timeout=1.0)

    # Плавное движение
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
