# -*- coding: utf-8 -*-
import pathlib
from typing import Optional, Tuple

import pyautogui
import win32gui

# pyautogui базовые настройки оставим тут, чтобы снимки были быстрыми и без failsafe-стопов
pyautogui.FAILSAFE = False
pyautogui.PAUSE = 0.02


def _client_region(hwnd) -> Optional[Tuple[int, int, int, int]]:
    """
    Возвращает клиентский прямоугольник hwnd в экранных координатах как (x, y, w, h),
    либо None, если окно недоступно.
    """
    if not hwnd or not win32gui.IsWindow(hwnd):
        return None
    try:
        l, t, r, b = win32gui.GetClientRect(hwnd)
        (sx, sy) = win32gui.ClientToScreen(hwnd, (l, t))
        (ex, ey) = win32gui.ClientToScreen(hwnd, (r, b))
        w = max(0, ex - sx)
        h = max(0, ey - sy)
        if w <= 0 or h <= 0:
            return None
        return (sx, sy, w, h)
    except Exception:
        return None


def _draw_hr_roi_overlay(img, client_w: int, client_h: int) -> None:
    """
    Рисует ROI H/R (если в ocr.py объявлены HR_RX/RY/RW/RH).
    Безопасно молчит при любой ошибке.
    """
    try:
        from PIL import ImageDraw
        from simpad_automation.core.ocr import HR_RX, HR_RY, HR_RW, HR_RH

        draw = ImageDraw.Draw(img)
        x0 = int(client_w * HR_RX)
        y0 = int(client_h * HR_RY)
        x1 = int(client_w * (HR_RX + HR_RW))
        y1 = int(client_h * (HR_RY + HR_RH))

        for off in (0, 1):
            draw.rectangle([x0 - off, y0 - off, x1 + off, y1 + off], outline=(0, 255, 0))

        label = "HR ROI"
        # простая плашка под подпись
        # (без ImageFont — чтобы не тащить шрифты)
        tw = max(36, len(label) * 6)
        th = 12
        draw.rectangle([x0, max(0, y0 - th - 4), x0 + tw + 6, y0], fill=(0, 255, 0))
        draw.text((x0 + 3, max(0, y0 - th - 3)), label, fill=(0, 0, 0))
    except Exception as e:
        print(f"[INFO] HR ROI overlay skipped: {e}")


def save_client_screenshot(hwnd, dest_path: pathlib.Path, draw_hr_roi: bool = True) -> pathlib.Path:
    """
    Делает скриншот клиентской области окна (если доступна) или всего экрана,
    по желанию рисует HR ROI, сохраняет на диск и возвращает путь.
    """
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    region = _client_region(hwnd)

    # Снимок
    if region:
        img = pyautogui.screenshot(region=region)  # PIL.Image
        client_w, client_h = region[2], region[3]
    else:
        img = pyautogui.screenshot()
        client_w, client_h = img.size

    if draw_hr_roi:
        _draw_hr_roi_overlay(img, client_w, client_h)

    img.save(dest_path)
    return dest_path


def attach_image_to_pytest_html(rep, path: pathlib.Path) -> None:
    """
    Пытается прикрепить изображение в pytest-html (если плагин активен),
    а также добавить путь в user_properties.
    """
    try:
        if hasattr(rep, "extra"):
            from pytest_html import extras
            rep.extra.append(extras.image(str(path)))
    except Exception:
        pass
    try:
        rep.user_properties.append(("screenshot", str(path)))
    except Exception:
        pass
