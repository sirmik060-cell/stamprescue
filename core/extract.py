# core/extract.py
import cv2

from core.inpaint import build_frame_mask


def extract_region(bgr, rect, kind="rect", feather=1, padding=8):
    """Вырезает область рамки в BGRA: вне фигуры — прозрачность."""
    h, w = bgr.shape[:2]
    x0, y0, x1, y1 = [int(v) for v in rect]
    xp0, yp0 = max(0, x0 - padding), max(0, y0 - padding)
    xp1, yp1 = min(w, x1 + padding), min(h, y1 + padding)

    crop = bgr[yp0:yp1, xp0:xp1]
    crop = cv2.cvtColor(crop, cv2.COLOR_BGR2BGRA)

    local = (x0 - xp0, y0 - yp0, x1 - xp0, y1 - yp0)
    alpha = build_frame_mask(crop.shape[:2], local, kind, feather)
    if alpha is None:
        return None
    crop[..., 3] = alpha
    return crop