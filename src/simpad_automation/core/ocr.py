# -*- coding: utf-8 -*-
"""
OCR HR-значений по ROI:
- Снимок ROI по долям окна
- Несколько проходов предобработки
- Fallback: посимвольное распознавание по компонентам (psm 10)
"""

import time
import re
from typing import Optional, List

import numpy as np
import cv2
import pyautogui
import pytesseract

from .window import get_client_rect

pyautogui.FAILSAFE = False
pyautogui.PAUSE = 0.02

# ---------- базовые утилиты ----------

def _grab_roi_bgr(hwnd, rx: float, ry: float, rw: float, rh: float) -> np.ndarray:
    rect = get_client_rect(hwnd)
    if not rect:
        raise RuntimeError("get_client_rect failed in _grab_roi_bgr")
    x = int(rect["left"] + rect["width"]  * rx)
    y = int(rect["top"]  + rect["height"] * ry)
    w = max(1, int(rect["width"]  * rw))
    h = max(1, int(rect["height"] * rh))
    img_rgb = np.array(pyautogui.screenshot(region=(x, y, w, h)))
    return cv2.cvtColor(img_rgb, cv2.COLOR_RGB2BGR)

def _scale_and_binarize(gray: np.ndarray) -> np.ndarray:
    # Увеличиваем сильнее, чтобы нули были толще
    big = cv2.resize(gray, None, fx=3, fy=3, interpolation=cv2.INTER_CUBIC)
    # Мягкое выравнивание контраста
    big = cv2.GaussianBlur(big, (3, 3), 0)
    _, thr = cv2.threshold(big, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    return thr

def _tess_digits(img_bin: np.ndarray, psm: int = 7) -> Optional[int]:
    cfg = f"--psm {psm} -c tessedit_char_whitelist=0123456789"
    txt = pytesseract.image_to_string(img_bin, config=cfg)
    m = re.search(r"(\d+)", txt)
    if not m:
        return None
    try:
        return int(m.group(1))
    except Exception:
        return None

# ---------- основная стратегия ----------

def _ocr_passes(img_bgr: np.ndarray) -> Optional[int]:
    """Несколько разных предобработок для целого числа."""
    # 1) По маске зелёного (HR у тебя зелёные)
    hsv = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2HSV)
    lower = np.array([35, 60, 60], dtype=np.uint8)
    upper = np.array([90, 255, 255], dtype=np.uint8)
    mask = cv2.inRange(hsv, lower, upper)
    mask = cv2.morphologyEx(mask, cv2.MORPH_DILATE, np.ones((2,2), np.uint8))
    val = _tess_digits(_scale_and_binarize(mask), psm=7)
    if val is not None:
        return val

    # 2) Стандартная бинаризация по яркости
    gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
    val = _tess_digits(_scale_and_binarize(gray), psm=7)
    if val is not None:
        return val

    # 3) Инвертированная бинаризация — бывает полезно
    gray_inv = 255 - gray
    val = _tess_digits(_scale_and_binarize(gray_inv), psm=7)
    return val

def _segments_left_to_right(bin_img: np.ndarray) -> List[np.ndarray]:
    """Готовим вырезки по отдельным символам слева направо."""
    # Немного расширим штрихи, чтобы контуры были цельными
    k = np.ones((3,3), np.uint8)
    proc = cv2.morphologyEx(bin_img, cv2.MORPH_CLOSE, k, iterations=1)
    # Находим контуры
    cnts, _ = cv2.findContours(proc, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    boxes = [cv2.boundingRect(c) for c in cnts]
    # отфильтруем шум очень маленькой площади
    boxes = [b for b in boxes if b[2] * b[3] >= 20]
    # сортировка слева направо
    boxes.sort(key=lambda b: b[0])
    # вырезаем символы
    crops = []
    for (x, y, w, h) in boxes:
        pad = 2
        x0 = max(0, x - pad); y0 = max(0, y - pad)
        x1 = min(bin_img.shape[1], x + w + pad)
        y1 = min(bin_img.shape[0], y + h + pad)
        crops.append(bin_img[y0:y1, x0:x1])
    return crops

def _ocr_by_components(img_bgr: np.ndarray) -> Optional[int]:
    """Посимвольное распознавание: psm=10, затем склейка."""
    gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
    bin_img = _scale_and_binarize(gray)

    crops = _segments_left_to_right(bin_img)
    if not crops:
        return None

    digits = []
    for crop in crops:
        # PSM 10 — один символ, whitelist только цифры
        cfg = "--psm 10 -c tessedit_char_whitelist=0123456789"
        txt = pytesseract.image_to_string(crop, config=cfg)
        d = re.sub(r"\D", "", txt)
        if not d:
            continue
        digits.append(d[-1])  # берём последнюю цифру, если вдруг вернулось больше

    if not digits:
        return None
    try:
        return int("".join(digits))
    except Exception:
        return None

def read_digits_from_roi(hwnd, rx: float, ry: float, rw: float, rh: float,
                         retries: int = 3, sleep: float = 0.08) -> Optional[int]:
    """
    Мультипроходное распознавание числа в ROI:
    - пробуем 3 предобработки целиком;
    - если неуверенно/обрезало ноль → посимвольно.
    """
    val_last = None
    for _ in range(max(1, retries)):
        img = _grab_roi_bgr(hwnd, rx, ry, rw, rh)
        # Основные проходы
        val = _ocr_passes(img)
        if val is not None:
            # если подозрительно коротко (например, 10 вместо 100) — попробуем посимвольно
            if val < 30 or val in (8, 80) and rw < 0.16:
                comp_val = _ocr_by_components(img)
                if comp_val is not None:
                    return comp_val
            return val
        # fallback посимвольно
        comp_val = _ocr_by_components(img)
        if comp_val is not None:
            return comp_val

        val_last = val
        time.sleep(sleep)
    return val_last

# ---------- конкретно для HR ----------
# Чуть увеличим ROI по ширине/высоте, чтобы третий символ не обрезался
HR_CX, HR_CY = 0.667, 0.217
HR_RW, HR_RH = 0.18, 0.14  # было 0.14/0.12 — добавили запас
HR_RX = HR_CX - HR_RW / 2.0
HR_RY = HR_CY - HR_RH / 2.0

def read_hr_value(hwnd, retries: int = 3) -> Optional[int]:
    return read_digits_from_roi(hwnd, HR_RX, HR_RY, HR_RW, HR_RH, retries=retries)
