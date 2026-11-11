# core/image_io.py
import io
from pathlib import Path

import cv2
import fitz
import numpy as np
from PIL import Image


class Document:
    """Единая обёртка: PDF или одиночное изображение."""

    def __init__(self, path):
        self.path = str(path)
        self.kind = "pdf" if Path(path).suffix.lower() == ".pdf" else "image"
        self._doc = fitz.open(self.path) if self.kind == "pdf" else None
        self._img = self._read_image(self.path) if self.kind == "image" else None

    @staticmethod
    def _read_image(path):
        data = np.fromfile(path, dtype=np.uint8)   # безопасно для кириллицы в пути
        img = cv2.imdecode(data, cv2.IMREAD_COLOR)
        if img is None:
            raise ValueError(f"Не удалось прочитать изображение: {path}")
        return img

    @property
    def page_count(self):
        return len(self._doc) if self.kind == "pdf" else 1

    def render_page(self, index, dpi=300):
        """Всегда возвращает ИСХОДНУЮ (нетронутую) страницу."""
        if self.kind == "image":
            return self._img.copy()
        page = self._doc.load_page(index)
        zoom = dpi / 72.0
        pix = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom), alpha=False)
        arr = np.frombuffer(pix.samples, np.uint8).reshape(pix.h, pix.w, pix.n)
        if pix.n == 3:
            return cv2.cvtColor(arr, cv2.COLOR_RGB2BGR).copy()
        return cv2.cvtColor(arr, cv2.COLOR_RGBA2BGR).copy()

    def close(self):
        if self._doc:
            self._doc.close()


def save_png(bgr_or_bgra, path):
    ok, buf = cv2.imencode(".png", bgr_or_bgra)
    if not ok:
        raise OSError("PNG encode failed")
    buf.tofile(str(path))


def save_pdf(original_path, edited_pages, out_path, dpi):
    """
    edited_pages: {page_index: bgr}.
    Правленые страницы заменяются растром, остальные копируются без изменений.
    original_path=None — источник был изображением.
    """
    src = fitz.open(original_path) if original_path else None
    out = fitz.open()
    n = src.page_count if src else 1

    for i in range(n):
        if src and i not in edited_pages:
            out.insert_pdf(src, from_page=i, to_page=i)
            continue

        if src:
            rect = src.load_page(i).rect
        else:
            h, w = edited_pages[0].shape[:2]
            rect = fitz.Rect(0, 0, w * 72.0 / dpi, h * 72.0 / dpi)

        page = out.new_page(width=rect.width, height=rect.height)
        rgb = cv2.cvtColor(edited_pages[i], cv2.COLOR_BGR2RGB)
        buf = io.BytesIO()
        Image.fromarray(rgb).save(buf, "PNG")
        page.insert_image(rect, stream=buf.getvalue())

    out.save(str(out_path), garbage=4, deflate=True)
    out.close()
    if src:
        src.close()