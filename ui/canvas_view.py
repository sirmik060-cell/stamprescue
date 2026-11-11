# ui/canvas_view.py
import cv2
import numpy as np
from PySide6.QtCore import QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QBrush, QColor, QImage, QPainter, QPen, QPixmap
from PySide6.QtWidgets import QGraphicsScene, QGraphicsView


def bgr_to_pixmap(bgr):
    if bgr.ndim == 2:
        h, w = bgr.shape
        q = QImage(bgr.data, w, h, w, QImage.Format_Grayscale8)
    else:
        h, w, _ = bgr.shape
        rgb = np.ascontiguousarray(bgr[..., ::-1])
        q = QImage(rgb.data, w, h, 3 * w, QImage.Format_RGB888)
    return QPixmap.fromImage(q.copy())


class CanvasView(QGraphicsView):
    frame_changed = Signal(object)
    zoom_changed = Signal(float)
    pipette_clicked = Signal(float, float)
    mask_changed = Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._scene = QGraphicsScene(self)
        self.setScene(self._scene)
        self._pixmap_item = None
        self._overlay_item = None
        self._frame_item = None
        self._temp_rect = None
        self._frame_rect = None
        self._frame_kind = "rect"
        self._mask = None
        self._img_shape = (0, 0)
        self._tool = "frame"
        self._brush = 12
        self._drawing = False
        self._moving = False
        self._panning = False
        self._painting = False
        self._space = False
        self._start = QPointF()
        self._last = QPointF()
        self._move_origin = QPointF()
        self._pan_start = QPointF()
        self._h = self._v = 0
        self._pipette_active = False

        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.setRenderHint(QPainter.Antialiasing)
        self.setRenderHint(QPainter.SmoothPixmapTransform)
        self.setBackgroundBrush(QBrush(QColor("#0e1116")))
        self.setCursor(Qt.CrossCursor)

    # ---------- изображение ----------
    def set_image(self, bgr, frame_rect=None):
        self._scene.clear()
        self._pixmap_item = None
        self._overlay_item = None
        self._frame_item = None
        self._temp_rect = None
        self._frame_rect = None
        self._img_shape = bgr.shape[:2]
        self._mask = np.zeros(self._img_shape, np.uint8)

        pix = bgr_to_pixmap(bgr)
        self._pixmap_item = self._scene.addPixmap(pix)
        self._overlay_item = self._scene.addPixmap(QPixmap())
        self._overlay_item.setZValue(5)
        try:
            self._overlay_item.setAcceptedMouseButtons(Qt.NoButton)
        except Exception:
            pass
        self._scene.setSceneRect(QRectF(pix.rect()))
        self.fit_view()
        if frame_rect is not None:
            self._set_frame(frame_rect)
        else:
            self.frame_changed.emit(None)
        self.mask_changed.emit(0)

    def frame_rect(self):
        return self._frame_rect

    def set_frame_kind(self, kind):
        self._frame_kind = kind
        self._redraw_frame()

    def clear_frame(self):
        self._frame_rect = None
        self._redraw_frame()
        self.frame_changed.emit(None)

    # ---------- инструменты маски ----------
    def set_tool(self, t):
        self._tool = t

    def set_brush(self, v):
        self._brush = max(2, int(v))

    def get_mask(self):
        if self._mask is None or self._mask.max() == 0:
            return None
        return self._mask.copy()

    def clear_mask(self):
        if self._mask is not None:
            self._mask[:] = 0
            self._refresh_overlay()
            self.mask_changed.emit(0)

    def set_pipette_mode(self, on):
        self._pipette_active = bool(on)

    def _refresh_overlay(self):
        if self._overlay_item is None or self._mask is None:
            return
        if self._mask.max() == 0:
            self._overlay_item.setPixmap(QPixmap())
            return
        h, w = self._mask.shape
        rgba = np.zeros((h, w, 4), np.uint8)
        m = self._mask > 0
        rgba[m, 0] = 255
        rgba[m, 1] = 60
        rgba[m, 2] = 60
        rgba[m, 3] = 120
        q = QImage(rgba.data, w, h, 4 * w, QImage.Format_RGBA8888)
        self._overlay_item.setPixmap(QPixmap.fromImage(q.copy()))

    def _emit_mask(self):
        n = int((self._mask > 0).sum()) if self._mask is not None else 0
        self.mask_changed.emit(n)

    def _stroke(self, p0, p1):
        if self._mask is None:
            return
        h, w = self._img_shape
        a = (int(max(0, min(w - 1, p0.x()))), int(max(0, min(h - 1, p0.y()))))
        b = (int(max(0, min(w - 1, p1.x()))), int(max(0, min(h - 1, p1.y()))))
        color = 255 if self._tool == "brush" else 0
        cv2.line(self._mask, a, b, color, self._brush)

    # ---------- зум / панорама ----------
    def fit_view(self):
        if self._pixmap_item:
            self.fitInView(self._pixmap_item, Qt.KeepAspectRatio)
            self.zoom_changed.emit(float(self.transform().m11()))

    def zoom(self, factor):
        self.scale(factor, factor)
        self.zoom_changed.emit(float(self.transform().m11()))

    def wheelEvent(self, e):
        self.zoom(1.15 if e.angleDelta().y() > 0 else 1.0 / 1.15)

    def keyPressEvent(self, e):
        if e.key() == Qt.Key_Space:
            self._space = True
            self.setCursor(Qt.ClosedHandCursor)
        else:
            super().keyPressEvent(e)

    def keyReleaseEvent(self, e):
        if e.key() == Qt.Key_Space:
            self._space = False
            self.setCursor(Qt.CrossCursor)
        else:
            super().keyReleaseEvent(e)

    # ---------- мышь ----------
    def _clamp(self, p):
        r = self.sceneRect()
        return QPointF(min(max(p.x(), r.left()), r.right()),
                       min(max(p.y(), r.top()), r.bottom()))

    def mousePressEvent(self, e):
        if self._pipette_active and e.button() == Qt.LeftButton:
            pos = self.mapToScene(e.position().toPoint())
            self.pipette_clicked.emit(float(pos.x()), float(pos.y()))
            e.accept()
            return

        if e.button() == Qt.MiddleButton or (self._space and e.button() == Qt.LeftButton):
            self._panning = True
            self._pan_start = e.position()
            self._h = self.horizontalScrollBar().value()
            self._v = self.verticalScrollBar().value()
            e.accept()
            return

        if e.button() == Qt.RightButton:
            self.clear_frame()
            e.accept()
            return

        if e.button() == Qt.LeftButton and self._pixmap_item is not None:
            pos = self._clamp(self.mapToScene(e.position().toPoint()))

            if self._tool in ("brush", "erase"):
                self._painting = True
                self._last = pos
                self._stroke(pos, pos)
                self._refresh_overlay()
                e.accept()
                return

            if self._tool == "rect":
                self._start = pos
                pen = QPen(QColor("#ff4d4d"), 0)
                pen.setStyle(Qt.DashLine)
                self._temp_rect = self._scene.addRect(QRectF(pos, pos), pen)
                self._temp_rect.setZValue(9)
                e.accept()
                return

            # tool == 'frame'
            if self._frame_rect and self._frame_rect.contains(pos):
                self._moving = True
                self._move_origin = pos - self._frame_rect.topLeft()
            else:
                self._drawing = True
                self._start = pos
                self._set_frame(QRectF(pos, pos))
            e.accept()
            return

        super().mousePressEvent(e)

    def mouseMoveEvent(self, e):
        if self._panning:
            d = e.position() - self._pan_start
            self.horizontalScrollBar().setValue(self._h - int(d.x()))
            self.verticalScrollBar().setValue(self._v - int(d.y()))
            return

        if self._painting:
            pos = self._clamp(self.mapToScene(e.position().toPoint()))
            self._stroke(self._last, pos)
            self._last = pos
            self._refresh_overlay()
            return

        if self._temp_rect is not None:
            pos = self._clamp(self.mapToScene(e.position().toPoint()))
            self._temp_rect.setRect(QRectF(self._start, pos).normalized())
            return

        if self._drawing:
            pos = self._clamp(self.mapToScene(e.position().toPoint()))
            self._set_frame(QRectF(self._start, pos).normalized())
            return

        if self._moving:
            pos = self.mapToScene(e.position().toPoint())
            tl = pos - self._move_origin
            b = self.sceneRect()
            x = min(max(tl.x(), b.left()), max(b.left(), b.right() - self._frame_rect.width()))
            y = min(max(tl.y(), b.top()), max(b.top(), b.bottom() - self._frame_rect.height()))
            self._set_frame(QRectF(QPointF(x, y), self._frame_rect.size()))
            return

        super().mouseMoveEvent(e)

    def mouseReleaseEvent(self, e):
        if e.button() in (Qt.LeftButton, Qt.MiddleButton):
            if self._painting:
                self._painting = False
                self._refresh_overlay()
                self._emit_mask()
            if self._temp_rect is not None:
                r = self._temp_rect.rect()
                self._scene.removeItem(self._temp_rect)
                self._temp_rect = None
                if self._mask is not None and r.width() > 2 and r.height() > 2:
                    h, w = self._img_shape
                    x0 = int(max(0, r.x())); y0 = int(max(0, r.y()))
                    x1 = int(min(w, r.x() + r.width())); y1 = int(min(h, r.y() + r.height()))
                    self._mask[y0:y1, x0:x1] = 255
                    self._refresh_overlay()
                    self._emit_mask()
            self._drawing = False
            self._moving = False
            self._panning = False
        super().mouseReleaseEvent(e)

    # ---------- рамка ----------
    def _set_frame(self, rect):
        self._frame_rect = rect
        self._redraw_frame()
        self.frame_changed.emit(rect)

    def _redraw_frame(self):
        if self._frame_item is not None:
            self._scene.removeItem(self._frame_item)
            self._frame_item = None
        if not self._frame_rect or self._frame_rect.width() < 2 or self._frame_rect.height() < 2:
            return
        pen = QPen(QColor("#f5a524"), 0)
        pen.setStyle(Qt.DashLine)
        pen.setDashPattern([6, 4])
        if self._frame_kind == "ellipse":
            self._frame_item = self._scene.addEllipse(self._frame_rect, pen)
        else:
            self._frame_item = self._scene.addRect(self._frame_rect, pen)
        self._frame_item.setZValue(10)