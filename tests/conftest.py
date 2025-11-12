# -*- coding: utf-8 -*-
"""
Root-level pytest bootstrap:
- adds src/ to sys.path
- adds timestamp to pytest-html filename
- Windows: real UI bootstrap + screenshots + step cards
- Non-Windows: safe stubs so headless unit tests can run
- Excludes non-UI tests from HTML report on Windows
- Keeps only a single report per run (same SESSION_TAG), but does not touch old runs
"""
import os
import sys
import pathlib
from datetime import datetime
import pytest

SESSION_TAG = os.environ.get("PYTEST_HTML_TAG")
if not SESSION_TAG:
    SESSION_TAG = datetime.now().strftime("%Y%m%d_%H%M%S")
    os.environ["PYTEST_HTML_TAG"] = SESSION_TAG

# ---- 0) Make 'src' importable everywhere ----
ROOT_DIR = os.path.dirname(__file__)
SRC_DIR = os.path.join(ROOT_DIR, "src")
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)


# ---- 0.5) Pytest 9: strip HTML flags on --collect-only (VS Code save) ----
def pytest_load_initial_conftests(early_config, parser, args):
    """
    VS Code часто запускает pytest --collect-only на сохранение.
    Если оставить --html из pytest.ini, генерится пустой report.html.
    Здесь безболезненно вырезаем HTML-флаги для таких запусков.
    """
    if "--collect-only" not in args:
        return
    i = 0
    while i < len(args):
        a = args[i]
        if a.startswith("--html=") or a == "--self-contained-html":
            del args[i]
            continue
        if a == "--html":
            del args[i]
            if i < len(args) and not args[i].startswith("-"):
                del args[i]  # убрать путь после --html
            continue
        i += 1


# ---- 1) Add timestamp to pytest-html file name ----
def pytest_configure(config):
    """Фиксируем имя HTML-отчёта один раз на весь запуск (по SESSION_TAG)."""
    htmlpath = getattr(config.option, "htmlpath", None)
    if not htmlpath:
        return

    from pathlib import Path
    p = Path(htmlpath)
    p.parent.mkdir(parents=True, exist_ok=True)

    tag = os.environ.get("PYTEST_HTML_TAG", SESSION_TAG)
    # если имя уже содержит тег — не дублируем
    if not p.stem.endswith(tag):
        p = p.parent / f"{p.stem}_{tag}{p.suffix}"

    # запомним, чтобы другие хуки знали итоговый путь
    config.option.htmlpath = str(p)
    config._html_fixed_path = str(p)
    print(f"[INFO] HTML report path: {config.option.htmlpath}")


# ---- 2) On Windows + HTML: include only UI/E2E in report (exclude unit tests) ----
def pytest_collection_modifyitems(config, items):
    """
    If HTML report is requested on Windows, only keep tests marked as @pytest.mark.ui or @pytest.mark.e2e.
    Others (like unit tests) are deselected => won't run and won't appear in the report.
    """
    if sys.platform != "win32":
        return
    htmlpath = getattr(config.option, "htmlpath", None)
    if not htmlpath:
        return  # no HTML -> don't filter
    keep, deselect = [], []
    for it in items:
        if it.get_closest_marker("ui") or it.get_closest_marker("e2e"):
            keep.append(it)
        else:
            deselect.append(it)
    if deselect:
        config.hook.pytest_deselected(items=deselect)
        items[:] = keep


# ---- 3) Keep only one report for this run (same SESSION_TAG); keep history ----
def pytest_sessionfinish(session, exitstatus):
    """
    В конце оставляем ровно один отчёт текущего запуска (по SESSION_TAG),
    удаляя дубликаты *только* с тем же тегом. Старые отчёты предыдущих запусков не трогаем.
    """
    from pathlib import Path

    html_fixed = getattr(session.config, "_html_fixed_path", None)
    if not html_fixed:
        return

    p = Path(html_fixed)
    if not p.exists():
        return

    tag = os.environ.get("PYTEST_HTML_TAG", SESSION_TAG)
    report_dir = p.parent
    base_stem = "_".join(p.stem.split("_")[:-1]) if tag in p.stem else p.stem

    # все файлы вида report_<tag>*.html в текущем запуске
    candidates = sorted(report_dir.glob(f"{base_stem}_{tag}*.html"))
    for f in candidates:
        if f != p:
            try:
                f.unlink()
                print(f"[CLEAN] Removed duplicate report: {f.name}")
            except Exception:
                pass

    print(f"[INFO] Kept single HTML report for this run: {p.name}")


# ======================================================================
# Non-Windows: stubs (UI fixtures skipped; headless unit tests still run)
# ======================================================================
if sys.platform != "win32":

    @pytest.fixture()
    def app_ctx():
        """UI fixture is Windows-only."""
        pytest.skip("Windows desktop required for UI tests")

    @pytest.hookimpl(hookwrapper=True)
    def pytest_runtest_makereport(item, call):
        outcome = yield
        return

# ======================================================================
# Windows: real UI bootstrap and screenshots on failure + step cards
# ======================================================================
else:
    import pyautogui
    from simpad_automation.core.app import launch_app, close_app
    from simpad_automation.core.reporter import (
        save_client_screenshot,
        attach_image_to_pytest_html,   # оставим, если используешь
        _append_step_card,
    )

    pyautogui.FAILSAFE = False
    pyautogui.PAUSE = 0.02

    @pytest.fixture()
    def app_ctx(request):
        """
        Launch SimPad app once per test and close it in teardown.
        Stores hwnd on test node so makereport can screenshot before closing.
        """
        process, hwnd = launch_app()
        request.node._simpad_hwnd = hwnd
        request.node._simpad_process = process
        try:
            yield (process, hwnd)
        finally:
            try:
                close_app(process, hwnd)
            except Exception as e:
                print(f"[WARN] close_app failed: {e}")

    @pytest.hookimpl(hookwrapper=True)
    def pytest_runtest_makereport(item, call):
        """
        On test failure (call phase), capture client-only screenshot BEFORE window closes,
        overlay HR ROI if available, and render step cards.
        """
        outcome = yield
        rep = outcome.get_result()

        # --- failure screenshot ---
        if rep.when == "call" and rep.failed:
            shots_dir = pathlib.Path(ROOT_DIR) / "artifacts" / "screenshots"
            ts = datetime.now().strftime("%Y%m%d-%H%M%S")
            fname = f"{item.name}_{ts}.png"
            path = shots_dir / fname
            hwnd = getattr(item, "_simpad_hwnd", None)
            try:
                save_client_screenshot(hwnd, path, draw_hr_roi=True)
                # pytest-html >=4.1
                if not hasattr(rep, "extras"):
                    rep.extras = []
                attach_image_to_pytest_html(rep, path)  # если у тебя внутри уже использует 'extras'
                print(f"[SNAP] Saved failure screenshot with HR ROI: {path}")
            except Exception as e:
                print(f"[WARN] Could not capture client screenshot: {e}")

        # --- step cards ---
        if rep.when == "call" and hasattr(item, "_steps"):
            try:
                if not hasattr(rep, "extras"):
                    rep.extras = []
                for st in getattr(item, "_steps", []):
                    _append_step_card(item, st)                 # формируем html и images в item._reporter_extras
                for ex in getattr(item, "_reporter_extras", []):
                    rep.extras.append(ex)                       # кладём в новый API
            except Exception as e:
                print(f"[WARN] Could not render step cards: {e}")
