# -*- coding: utf-8 -*-
"""
Universal OCR phrase verifier for SimPad: robust, low-tuning.
- Ensemble OCR (multi-psm, multi-threshold, invert/normal)
- Weighted word-level fuzzy match (content words > stopwords)
- Fallback: contour-based word segmentation + smart split for glued words
- Debug artifacts -> artifacts/ocr_debug/<debug_name>/
"""

from __future__ import annotations
import re
import tempfile
from pathlib import Path
from typing import Tuple, List, Dict
import sys  # added for platform check

import cv2
import numpy as np

# LAZY IMPORTS: avoid breaking module import on Linux/CI
try:
    import pyautogui as _pyautogui  # may be missing on CI
except Exception:
    _pyautogui = None

try:
    import pytesseract as _pytesseract  # may be missing on CI
except Exception:
    _pytesseract = None

from difflib import SequenceMatcher


# ---------- small utils ----------

STOPWORDS = {"to", "of", "and", "in", "on", "for", "the", "a", "an", "is", "at", "by"}

def _sim(a: str, b: str) -> float:
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()

_GLYPH_SUBS = str.maketrans({
    "x": "t", "X": "t",
    "1": "l",
    "0": "o",
    "5": "s", "S": "s",
})

def _letters_only(s: str) -> str:
    return re.sub(r"[^A-Za-z ]+", " ", s)

def _norm_sentence(s: str) -> str:
    s = _letters_only(s)
    s = re.sub(r"\s+", " ", s).strip().lower()
    return s

def _norm_word(s: str) -> str:
    s = re.sub(r"[^A-Za-z]+", "", s).translate(_GLYPH_SUBS)
    return s

def _tokenize_expected(phrase: str) -> List[str]:
    return [w for w in _norm_sentence(phrase).split() if w]

def _weighted_score(matches: List[Tuple[str, str, float]]) -> float:
    """Weighted average by content vs. stopwords."""
    if not matches:
        return 0.0
    total, weight = 0.0, 0.0
    for _, exp, sc in matches:
        w = 0.35 if exp in STOPWORDS else 1.0
        total += w * sc
        weight += w
    return total / max(1e-9, weight)


# ---------- lazy deps helpers (so import won't fail on CI) ----------

def _use_pyautogui():
    """Return pyautogui or raise if unavailable (e.g., non-Windows CI)."""
    if _pyautogui is None:
        raise RuntimeError("pyautogui is not available on this environment (likely non-Windows CI).")
    return _pyautogui

def _use_pytesseract():
    """Return pytesseract or raise if unavailable."""
    if _pytesseract is None:
        raise RuntimeError("pytesseract is not available in this environment.")
    return _pytesseract


# ---------- screenshot helpers ----------

def _grab_roi_bgr(hwnd, roi_xywh_rel: Tuple[float, float, float, float],
                  client_rect: Dict[str, int]) -> np.ndarray:
    rx, ry, rw, rh = roi_xywh_rel
    x = int(client_rect["left"] + client_rect["width"] * rx)
    y = int(client_rect["top"]  + client_rect["height"] * ry)
    w = max(1, int(client_rect["width"]  * rw))
    h = max(1, int(client_rect["height"] * rh))
    # ✅ use lazy import
    img_rgb = np.array(_use_pyautogui().screenshot(region=(x, y, w, h)))
    return cv2.cvtColor(img_rgb, cv2.COLOR_RGB2BGR)


# ---------- ensemble OCR (line mode) ----------

def _prep_variants(img_bgr: np.ndarray) -> List[np.ndarray]:
    """Generate several binarized variants (normal & inverted)."""
    gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
    big  = cv2.resize(gray, None, fx=3.6, fy=3.6, interpolation=cv2.INTER_CUBIC)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    g = clahe.apply(big)
    g = cv2.GaussianBlur(g, (3, 3), 0)

    variants = []
    for th in (185, 190, 200):
        _, thr = cv2.threshold(g, th, 255, cv2.THRESH_BINARY)
        variants.append(thr)
        variants.append(cv2.bitwise_not(thr))
    ada = cv2.adaptiveThreshold(g, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                cv2.THRESH_BINARY, 31, 8)
    variants.append(ada)
    variants.append(cv2.bitwise_not(ada))
    return variants

def _ocr_text_psm(bin_img: np.ndarray, psm: int) -> str:
    # use lazy import for pytesseract
    pytesseract = _use_pytesseract()
    cfg = f"--oem 3 --psm {psm} -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz "
    txt = pytesseract.image_to_string(bin_img, config=cfg, lang="eng")
    return re.sub(r"\s+", " ", txt).strip()

def _ensemble_read_line(img_bgr: np.ndarray) -> str:
    """Try several PSMs and variants; return the longest cleaned line."""
    best = ""
    for v in _prep_variants(img_bgr):
        for psm in (7, 6, 5):  # single line -> block -> uniform
            t = _ocr_text_psm(v, psm)
            if len(_letters_only(t)) > len(_letters_only(best)):
                best = t
    return best


# ---------- word segmentation fallback ----------

def _binarize_for_words(img_bgr: np.ndarray) -> np.ndarray:
    gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
    big  = cv2.resize(gray, None, fx=3.8, fy=3.8, interpolation=cv2.INTER_CUBIC)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    big   = clahe.apply(big)
    big   = cv2.GaussianBlur(big, (3, 3), 0)
    _, thr = cv2.threshold(big, 185, 255, cv2.THRESH_BINARY)
    return thr

def _find_word_boxes(bin_img: np.ndarray) -> List[Tuple[int, int, int, int]]:
    H, W = bin_img.shape
    k_close = cv2.getStructuringElement(cv2.MORPH_RECT, (31, 3))
    closed  = cv2.morphologyEx(bin_img, cv2.MORPH_CLOSE, k_close, iterations=1)
    cnts, _ = cv2.findContours(closed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    boxes = []
    for c in cnts:
        x, y, w, h = cv2.boundingRect(c)
        area = w * h
        if area < 0.002 * W * H:   # tiny noise
            continue
        if h < 0.20 * H:
            continue
        if w > 0.98 * W:
            continue
        pad = 2
        x = max(0, x - pad); y = max(0, y - pad)
        w = min(W - x, w + 2 * pad)
        h = min(H - y, h + 2 * pad)
        boxes.append((x, y, w, h))
    boxes.sort(key=lambda b: b[0])
    # merge neighbors with tiny gap
    merged = []
    if boxes:
        cur = list(boxes[0])
        for bx in boxes[1:]:
            cx, cy, cw, ch = cur
            bx_, by_, bw_, bh_ = bx
            gap = bx_ - (cx + cw)
            gap_thresh = 0.25 * ((ch + bh_) / 2.0)
            if gap <= max(3, gap_thresh):
                x0 = min(cx, bx_)
                y0 = min(cy, by_)
                x1 = max(cx + cw, bx_ + bw_)
                y1 = max(cy + ch, by_ + bh_)
                cur = [x0, y0, x1 - x0, y1 - y0]
            else:
                merged.append(tuple(cur)); cur = list(bx)
        merged.append(tuple(cur))
    else:
        merged = boxes
    return merged

def _tess_word(bin_img: np.ndarray, user_words: Path | None = None) -> str:
    # use lazy import for pytesseract
    pytesseract = _use_pytesseract()
    cfg = "--oem 3 --psm 8 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"
    if user_words:
        cfg += f" --user-words {str(user_words)}"
    txt = pytesseract.image_to_string(bin_img, config=cfg, lang="eng")
    return _norm_word(txt)

def _best_split(merged: str, exp_left: str, exp_right: str) -> tuple[int, float, float]:
    best_k, best_s1, best_s2, best_total = -1, 0.0, 0.0, -1.0
    for k in range(1, len(merged)):
        l, r = merged[:k], merged[k:]
        s1, s2 = _sim(l, exp_left), _sim(r, exp_right)
        tot = s1 + s2
        if tot > best_total:
            best_k, best_s1, best_s2, best_total = k, s1, s2, tot
    return best_k, best_s1, best_s2

def _ocr_words(img_bgr: np.ndarray, expected_words: List[str], debug_dir: Path | None) -> List[str]:
    bin_img = _binarize_for_words(img_bgr)
    boxes = _find_word_boxes(bin_img)

    # hint dictionary
    tmp_words = None
    try:
        tmp_words = Path(tempfile.mkstemp(prefix="tess_words_", suffix=".txt")[1])
        tmp_words.write_text("\n".join(expected_words), encoding="utf-8")
    except Exception:
        tmp_words = None

    words = []
    if debug_dir:
        debug_dir.mkdir(parents=True, exist_ok=True)
        cv2.imwrite(str(debug_dir / "bin.png"), bin_img)

    for idx, (x, y, w, h) in enumerate(boxes, start=1):
        crop = bin_img[y:y+h, x:x+w]
        crop = cv2.resize(crop, None, fx=1.8, fy=1.8, interpolation=cv2.INTER_CUBIC)
        txt = _tess_word(crop, user_words=tmp_words)
        words.append(txt)
        if debug_dir:
            cv2.imwrite(str(debug_dir / f"word_{idx}.png"), crop)
            (debug_dir / f"word_{idx}.txt").write_text(txt or "<EMPTY>", encoding="utf-8")

    if tmp_words and tmp_words.exists():
        try: tmp_words.unlink()
        except Exception: pass

    return [w for w in words if w]  # drop empties


# ---------- alignment & public API ----------

def _align_words(ocr_words: List[str], expected_words: List[str],
                 min_ratio: float = 0.62, avg_threshold: float = 0.80) -> Tuple[bool, List[Tuple[str, str, float]]]:
    """
    Align OCR tokens to expected tokens:
      - glyph normalization
      - allow glued pairs via best split
      - pass if <=1 non-stopword below min_ratio and weighted-avg >= avg_threshold
    """
    ocr = [_norm_word(w) for w in ocr_words]
    exp = expected_words[:]
    pairs: List[Tuple[str, str, float]] = []

    i = j = 0
    while i < len(ocr) and j < len(exp):
        w = ocr[i]; tgt = exp[j]
        s = _sim(w, tgt)

        def should_try_split() -> bool:
            if (j + 1) >= len(exp): return False
            concat_like = _sim(w, tgt + exp[j + 1]) >= 0.80
            near_thresh = s <= (min_ratio + 0.03)
            longish = len(w) >= (len(tgt) + len(exp[j+1]) - 1)
            return concat_like or near_thresh or longish

        if should_try_split():
            k, s1, s2 = _best_split(w, tgt, exp[j + 1])
            if k > 0 and s1 >= (min_ratio - 0.03) and s2 >= (min_ratio - 0.03):
                pairs.append((w[:k], tgt, s1))
                pairs.append((w[k:], exp[j + 1], s2))
                i += 1; j += 2
                continue

        pairs.append((w, tgt, s))
        i += 1; j += 1

    # if still short, try to split the last/next into remaining expected
    while len(pairs) < len(exp) and i < len(ocr) and (j + 1) < len(exp):
        w = ocr[i]
        k, s1, s2 = _best_split(w, exp[j], exp[j + 1])
        if k > 0:
            pairs.append((w[:k], exp[j], s1))
            pairs.append((w[k:], exp[j + 1], s2))
            i += 1; j += 2
        else:
            break

    if len(pairs) < len(exp):
        return False, pairs

    scores = [s for (_, e, s) in pairs[:len(exp)]]
    below = sum(1 for (_, e, s) in pairs[:len(exp)] if s < min_ratio and e not in STOPWORDS)
    avg = _weighted_score(pairs[:len(exp)])

    ok = (below <= 1) and (avg >= avg_threshold)
    return ok, pairs


def assert_phrase_in_roi(hwnd, client_rect: Dict[str, int],
                         roi_xywh_rel: Tuple[float, float, float, float],
                         expected_phrase: str,
                         debug_name: str = "phrase_check",
                         min_ratio: float = 0.62,
                         avg_threshold: float = 0.80) -> Tuple[bool, Dict]:
    """
    Universal phrase verification (robust, low tuning).
    Returns (ok, details) where details has 'text', 'tokens', 'pairs', 'debug_dir'.
    """
    exp_tokens = _tokenize_expected(expected_phrase)
    debug_dir = Path("artifacts") / "ocr_debug" / debug_name

    img = _grab_roi_bgr(hwnd, roi_xywh_rel, client_rect)

    # Stage 1: ensemble line read, quick decision by tokens
    line = _ensemble_read_line(img)
    line_tokens = _tokenize_expected(line)
    ok_line, pairs_line = _align_words(line_tokens, exp_tokens, min_ratio, avg_threshold)

    # Stage 2 (fallback): contour word read + alignment
    if not ok_line:
        words = _ocr_words(img, exp_tokens, debug_dir=debug_dir)
        ok_words, pairs_words = _align_words(words, exp_tokens, min_ratio, avg_threshold)
        return ok_words, {
            "mode": "words",
            "text": line,
            "tokens": words,
            "pairs": pairs_words,
            "debug_dir": str(debug_dir),
        }

    return True, {
        "mode": "line",
        "text": line,
        "tokens": line_tokens,
        "pairs": pairs_line,
        "debug_dir": str(debug_dir),
    }

# ---- public wrappers for CI unit-tests (no GUI) ----

def normalize_text(s: str) -> str:
    """Public wrapper around internal _norm_sentence for unit-tests."""
    return _norm_sentence(s)

def compare_tokens(target: str, ocr_text: str, ok_ratio: float = 0.7) -> bool:
    """
    Public boolean check using existing alignment logic.
    ok_ratio → mapped to avg_threshold; the character-glue split threshold is taken from the main pipeline.
    """
    exp_tokens = _tokenize_expected(target)
    ocr_tokens = _tokenize_expected(ocr_text)
    ok, _pairs = _align_words(
        ocr_tokens,
        exp_tokens,
        min_ratio=0.62,
        avg_threshold=ok_ratio,
    )
    return ok
