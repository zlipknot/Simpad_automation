# -*- coding: utf-8 -*-
import pathlib
from typing import Optional, Tuple
import base64
import pyautogui
import win32gui
from contextlib import contextmanager
import html
import re
from datetime import datetime
from pathlib import Path

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


def attach_image_to_pytest_html(rep, path):
    """Прикрепляет изображение к pytest-html (self-contained)."""
    try:
        from pytest_html import extras
        if not hasattr(rep, "extras"):
            rep.extras = []
        abs_path = str(Path(path).resolve())
        rep.extras.append(extras.image(abs_path))
    except Exception as e:
        print(f"[WARN] attach_image_to_pytest_html failed: {e}")

def _slug(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", s.strip().lower()).strip("-")

def _ensure_node_state(request):
    node = request.node
    if not hasattr(node, "_steps"):
        node._steps = []            # list of dict {idx,name,status,started,ended,screenshot,dir}
    if not hasattr(node, "_step_idx"):
        node._step_idx = 0
    if not hasattr(node, "_reporter_extras"):
        node._reporter_extras = []  # will be appended to rep in makereport
    return node

import base64

def _append_step_card(node, step):
    status = step["status"]
    name = html.escape(step["name"])
    times = f'{step["started"]} → {step.get("ended","")}'
    color = {"passed":"#16a34a","failed":"#dc2626","skipped":"#a3a3a3"}.get(status,"#2563eb")

    shot_html = ""
    if step.get("screenshot"):
        p = Path(step["screenshot"]).resolve()
        # относительный путь для красоты
        try:
            rel = p.relative_to(Path.cwd())
            rel_txt = rel.as_posix()
        except Exception:
            rel_txt = str(p)

        # встроим миниатюру прямо в карточку (base64)
        try:
            data = base64.b64encode(p.read_bytes()).decode("ascii")
            thumb = f'<img src="data:image/png;base64,{data}" style="max-width:420px;display:block;margin-top:4px;" />'
        except Exception:
            thumb = ""

        shot_html = f'<div>Screenshot: <code>{html.escape(rel_txt)}</code>{thumb}</div>'

    card = f"""
    <div style="border:1px solid #e5e7eb;border-left:6px solid {color};padding:8px;margin:6px 0;">
      <div><b>Step {step['idx']}:</b> {name} <span style="color:{color};">[{status}]</span></div>
      <div style="font-size:12px;color:#6b7280;">{times}</div>
      {shot_html}
    </div>
    """

    try:
        from pytest_html import extras
        node._reporter_extras.append(extras.html(card))     # html карточка
        if step.get("screenshot"):
            # и полноценный attachment (кроме превью) — тоже встраивается
            node._reporter_extras.append(extras.image(str(Path(step["screenshot"]).resolve())))
    except Exception:
        pass


@contextmanager
def step(request, name: str, hwnd=None, artifacts_dir: Path | None = None, draw_hr_roi: bool = True):
    """
    Контекст-менеджер шага.
    Пример:
        with step(request, "Open Device Info", hwnd, artifacts_dir):
            click(...)
    На исключении сохранит скриншот и отметит шаг как failed.
    """
    node = _ensure_node_state(request)
    node._step_idx += 1
    idx = node._step_idx
    started = datetime.now().strftime("%H:%M:%S")
    entry = {
        "idx": idx,
        "name": name,
        "status": "passed",
        "started": started,
        "ended": None,
        "screenshot": None,
        "dir": None,
    }
    node._steps.append(entry)

    # подготовим папку для артефактов шага
    step_dir = None
    if artifacts_dir:
        step_dir = Path(artifacts_dir) / f"step_{idx}_{_slug(name)}"
        step_dir.mkdir(parents=True, exist_ok=True)
        entry["dir"] = step_dir

    try:
        yield
    except Exception:
        entry["status"] = "failed"
        entry["ended"] = datetime.now().strftime("%H:%M:%S")
        # Сохранить скриншот, если есть hwnd
        try:
            if hwnd is not None and artifacts_dir is not None:
                from .reporter import save_client_screenshot  # локальный импорт, чтобы не ломать импорты
                shot_path = (step_dir or Path(artifacts_dir)) / "failed.png"
                save_client_screenshot(hwnd, shot_path, draw_hr_roi=draw_hr_roi)
                entry["screenshot"] = shot_path
        finally:
            pass
        # карточка шага попадёт в отчёт из makereport (см. conftest.py)
        raise
    else:
        entry["status"] = "passed"
        entry["ended"] = datetime.now().strftime("%H:%M:%S")
    # карточка добавится в makereport