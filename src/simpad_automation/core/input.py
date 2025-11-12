import time
import pyautogui

# Base settings of pyautogui for stability
pyautogui.FAILSAFE = False          # fix exeption with position in the corner of the window
pyautogui.PAUSE = 0.02              # small pause betwenn commands

def type_text(text: str, interval: float = 0.03):
    """
    Print text like a human
    interval — delay between symbols
    """
    pyautogui.typewrite(text, interval=interval)

def press_enter():
    pyautogui.press('enter')

def press_backspace(n: int = 1, interval: float = 0.02):
    """Press Backspace n times."""
    for _ in range(max(0, n)):
        pyautogui.press('backspace')
        time.sleep(interval)