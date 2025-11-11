import time
import pyautogui

# Базовые настройки pyautogui для стабильности
pyautogui.FAILSAFE = False          # не выкидывать исключение от резкого движения в угол
pyautogui.PAUSE = 0.02              # маленькая пауза между командами

def type_text(text: str, interval: float = 0.03):
    """
    Печатает заданный текст «как человек».
    interval — задержка между символами (подбирается под чувствительность поля ввода).
    """
    pyautogui.typewrite(text, interval=interval)

def press_enter():
    pyautogui.press('enter')

def press_backspace(n: int = 1, interval: float = 0.02):
    """Нажать Backspace n раз (на случай, если очистка через кнопку не сработает)."""
    for _ in range(max(0, n)):
        pyautogui.press('backspace')
        time.sleep(interval)