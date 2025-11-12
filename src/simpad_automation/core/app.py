import os, time, ctypes
import win32gui, win32con

APP_DIR  = r"C:\Program Files (x86)\Laerdal Medical\SimPad"
APP_PATH = APP_DIR + r"\rcgui.exe"

def _shell_execute_open(path, cwd):
    # SW_SHOWNORMAL = 1
    hinst = ctypes.windll.shell32.ShellExecuteW(None, "open", path, None, cwd, 1)
    if hinst <= 32:
        raise RuntimeError(f"ShellExecuteW failed: {hinst}")

def launch_app(timeout: float = 20.0):
    # 1) Launch app (double click simulation)
    _shell_execute_open(APP_PATH, APP_DIR)

    # 2) Waiting for app window
    hwnd = None
    t0 = time.time()
    while time.time() - t0 < timeout:
        def enum_cb(h, _):
            nonlocal hwnd
            if not win32gui.IsWindowVisible(h):
                return
            title = win32gui.GetWindowText(h) or ""
            if "SimPad rcgui" in title:
                hwnd = h
        win32gui.EnumWindows(enum_cb, None)
        if hwnd:
            break
        time.sleep(0.2)
    if not hwnd:
        raise RuntimeError("Окно SimPad не найдено после ShellExecute.")

    # 3) Bring it to the foreground and wait for the actual focus
    try:
        win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
        win32gui.SetForegroundWindow(hwnd)
    except Exception:
        pass

    t_focus = time.time()
    while time.time() - t_focus < 10:
        if win32gui.GetForegroundWindow() == hwnd:
            break
        time.sleep(0.1)

    # 4) Waiter to give app full loading before the first click
    time.sleep(3.0)
    return None, hwnd  # close by hwnd

def close_app(_process, hwnd):
    """Close window with WM_CLOSE (because launch with ShellExecute)."""
    try:
        win32gui.PostMessage(hwnd, win32con.WM_CLOSE, 0, 0)
    except Exception:
        pass

