# ui/splash.py — заставка ~5 c: векторная «печать» впечатывается в темноту,
# затем название и подзаголовок. Таймлайн — счётчиком тиков (33 мс), чтобы
# прогон был одинаковым независимо от скорости старта окна. Клик/Esc — скип.
import math
import os
import random
import sys

from PySide6.QtCore import Qt, QTimer, QPointF, QRectF
from PySide6.QtGui import (QColor, QFont, QLinearGradient, QPainter, QPen,
                          QPixmap, QPolygonF, QRadialGradient)
from PySide6.QtWidgets import QApplication, QWidget

W, H = 900, 560
INK = QColor(214, 62, 52)          # «штамповая» краска
ACC = QColor(232, 236, 242)        # заголовок
MUT = QColor(150, 158, 170)


def _asset(name):
    cands = []
    if getattr(sys, "frozen", False):
        cands.append(os.path.join(os.path.dirname(sys.executable), "assets", name))
        meip = getattr(sys, "_MEIPASS", None)
        if meip:
            cands.append(os.path.join(meip, "assets", name))
    cands.append(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets", name))
    for c in cands:
        if os.path.exists(c):
            return c
    return None


def play_intro_sound():
    """Однократное проигрывание assets/splash.wav через winmm (без зависимостей)."""
    if sys.platform != "win32":
        return
    try:
        if QApplication.instance() and QApplication.instance().platformName() == "offscreen":
            return
    except Exception:
        pass
    wav = _asset("splash.wav")
    if not wav:
        return
    try:
        import ctypes
        w = ctypes.windll.winmm
        w.mciSendStringW("close sr_splash", None, 0, 0)
        # ВАЖНО: при успешном open MCI кладёт в буфер номер устройства ("1") —
        # отличаем ошибку только по коду возврата, а не по содержимому буфера.
        rc = w.mciSendStringW(f'open "{wav}" type waveaudio alias sr_splash', None, 0, 0)
        if rc:
            rc = w.mciSendStringW(f'open "{wav}" alias sr_splash', None, 0, 0)
        if not rc:
            w.mciSendStringW("play sr_splash", None, 0, 0)
    except Exception:
        pass


def stop_intro_sound():
    if sys.platform != "win32":
        return
    try:
        import ctypes
        ctypes.windll.winmm.mciSendStringW("stop sr_splash", None, 0, 0)
        ctypes.windll.winmm.mciSendStringW("close sr_splash", None, 0, 0)
    except Exception:
        pass


def _ease_out(x):
    return 1.0 - (1.0 - x) ** 3


_FONT_FAM = None


def _font(px, bold=False):
    """Шрифт заставки: грузим конкретный TTF (arial*) через QFontDatabase —
    иначе в offscreen-тестах нет системных шрифтов и всё рисуется «тофу»."""
    global _FONT_FAM
    if _FONT_FAM is None:
        from PySide6.QtGui import QFontDatabase
        db = QFontDatabase()
        win = os.environ.get("WINDIR", r"C:\Windows")
        for cand in (os.path.join(win, "Fonts", "arialbd.ttf"),
                     os.path.join(win, "Fonts", "arial.ttf"),
                     _asset("arialbd.ttf") or "",
                     "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"):
            if cand and os.path.exists(cand):
                fid = db.addApplicationFont(cand)
                fams = db.applicationFontFamilies(fid)
                if fams:
                    _FONT_FAM = fams[0]
                    break
        else:
            _FONT_FAM = ""
    f = QFont(_FONT_FAM or "")
    f.setPixelSize(int(px))
    f.setBold(bool(bold))
    return f


def _clamp01(x):
    return max(0.0, min(1.0, x))


def _star_pts(cx, cy, r, rot=0.0):
    pts = []
    for k in range(10):
        rr = r if k % 2 == 0 else r * 0.42
        aa = math.radians(rot - 90 + k * 36)
        pts.append(QPointF(cx + rr * math.cos(aa), cy + rr * math.sin(aa)))
    return pts


def _make_stamp_layer(sz=420):
    """Печатный логотип-слой (красный, прозрачный фон) с зернистой краской."""
    lay = QPixmap(sz, sz)
    lay.fill(Qt.transparent)
    p = QPainter(lay)
    p.setRenderHint(QPainter.Antialiasing)
    c = sz / 2
    pen = QPen(INK)
    pen.setWidthF(8.0)
    p.setPen(pen)
    p.drawEllipse(QPointF(c, c), c - 10, c - 10)
    pen2 = QPen(INK)
    pen2.setWidthF(2.5)
    p.setPen(pen2)
    p.drawEllipse(QPointF(c, c), c - 26, c - 26)
    # дуговой текст: center_deg — верхняя (-90) или нижняя (+90) точка;
    # в Qt y вниз: угол a даёт (cx + r cos a, cy + r sin a), a растёт по часовой
    def arc_text(text, radius, center_deg, px, bottom=False):
        p.setFont(_font(px, True))
        fm_w = [max(p.fontMetrics().horizontalAdvance(ch), 2) for ch in text]
        total = sum(fm_w) / radius  # радиан
        if bottom:
            a = math.radians(center_deg) + total / 2
            step = -1
        else:
            a = math.radians(center_deg) - total / 2
            step = 1
        for ch, w in zip(text, fm_w):
            d = w / radius
            aa = a + step * d / 2
            p.save()
            p.translate(c + radius * math.cos(aa), c + radius * math.sin(aa))
            p.rotate(math.degrees(aa) + (90 if not bottom else -90))
            p.drawText(QPointF(-w / 2, 0), ch)
            p.restore()
            a += step * d
    p.setPen(QPen(INK))
    arc_text("STAMPRESCUE", c - 56, -90, 22)
    arc_text("SIRMIK EDITION", c - 56, 90, 16, bottom=True)
    # центр: монограмма + звезда сверху + год снизу
    p.setPen(QPen(INK))
    f = _font(54, True)
    p.setFont(f)
    p.drawText(QRectF(c - 110, c - 48, 220, 96), Qt.AlignCenter, "SR")
    f2 = _font(14, True)
    p.setFont(f2)
    p.drawText(QRectF(c - 110, c + 58, 220, 24), Qt.AlignCenter, "EST. 2026")
    p.setBrush(INK)
    p.setPen(Qt.NoPen)
    p.drawPolygon(QPolygonF(_star_pts(c, c - 92, 13)))
    for sx in (c - 118, c + 118):  # звёзды-разделители на кольце
        p.drawPolygon(QPolygonF(_star_pts(sx, c, 10)))
    # зернистость: «дырки» в краске
    p.setCompositionMode(QPainter.CompositionMode_DestinationOut)
    rng = random.Random(20260)
    for _ in range(2600):
        x, y = rng.uniform(0, sz), rng.uniform(0, sz)
        if (x - c) ** 2 + (y - c) ** 2 > (c - 4) ** 2:
            continue
        p.setOpacity(rng.uniform(0.05, 0.35))
        r = rng.uniform(0.5, 1.7)
        p.drawEllipse(QPointF(x, y), r, r)
    p.end()
    return lay


class Splash(QWidget):
    def __init__(self, duration_ms=5000):
        super().__init__(None, Qt.Window | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setFixedSize(W, H)
        self._dur = duration_ms
        self._t = 0
        self._closing = False
        self._closed_by_timer = False
        self._bg = self._make_bg()
        self._stamp = _make_stamp_layer()
        scr = QApplication.primaryScreen().availableGeometry()
        self.move(scr.center().x() - W // 2, scr.center().y() - H // 2)
        self._tm = QTimer(self)
        self._tm.timeout.connect(self._tick)
        self._tm.start(33)

    def _make_bg(self):
        pm = QPixmap(W, H)
        g = QRadialGradient(W / 2, H * 0.42, H * 0.9)
        g.setColorAt(0.0, QColor(28, 33, 41))
        g.setColorAt(1.0, QColor(10, 12, 16))
        p = QPainter(pm)
        p.fillRect(0, 0, W, H, g)
        p.end()
        return pm

    def start(self):
        self.show()

    def _tick(self):
        self._t += 33
        if self._t >= self._dur and not self._closing:
            self._closed_by_timer = True
            self._begin_close()
        self.update()

    def _begin_close(self):
        if self._closing:
            return
        self._closing = True
        stop_intro_sound()
        QTimer.singleShot(380, self.close)

    def mousePressEvent(self, e):
        self._begin_close()

    def keyPressEvent(self, e):
        if e.key() in (Qt.Key_Escape, Qt.Key_Space, Qt.Key_Return, Qt.Key_Enter):
            self._begin_close()
        else:
            super().keyPressEvent(e)

    # ----- отрисовка -----
    def paintEvent(self, _):
        t = self._t
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.drawPixmap(0, 0, self._bg)
        cx, cy = W / 2, H * 0.40
        # 1) печать «впечатывается»: 400..1500 мс
        a = _clamp01((t - 400) / 1100)
        if a > 0:
            e = _ease_out(a)
            scale = 1.30 - 0.30 * e
            rot = -5.0 + 5.0 * e
            alpha = int(255 * min(1.0, a * 1.4))
            sz = self._stamp.width() * scale
            p.save()
            p.setOpacity(alpha / 255.0)
            p.translate(cx, cy)
            p.rotate(rot)
            p.drawPixmap(QPointF(-sz / 2, -sz / 2), self._stamp,
                         self._stamp.rect())
            # импульс контакта
            if 1300 <= t <= 1800:
                k = (t - 1300) / 500
                p.setOpacity((1 - k) * 0.5)
                p.setPen(QPen(INK, 3))
                p.setBrush(Qt.NoBrush)
                r = self._stamp.width() / 2 * (1.0 + 0.12 * k)
                p.drawEllipse(QPointF(0, 0), r, r)
            p.restore()
        # 2) заголовок: 1700..2600
        a2 = _clamp01((t - 1700) / 900)
        if a2 > 0:
            p.save()
            p.setOpacity(a2)
            f = _font(46, True)
            p.setFont(f)
            p.setPen(QColor(ACC))
            y = H * 0.76 + 14 * (1 - _ease_out(a2))
            p.drawText(QRectF(0, y, W, 70), Qt.AlignHCenter, "StampRescue")
            p.restore()
        a3 = _clamp01((t - 2200) / 900)
        if a3 > 0:
            p.save()
            p.setOpacity(a3 * 0.9)
            f = _font(17, False)
            p.setFont(f)
            p.setPen(QColor(MUT))
            p.drawText(QRectF(0, H * 0.76 + 66, W, 40), Qt.AlignHCenter,
                       "удаление печатей и штампов со сканов документов")
            p.restore()
        # 3) искорки на звёздах печати: 3000..4500
        if 3000 <= t:
            ph = (t - 3000) / 700.0
            for k, (sx, sy) in enumerate(((cx - 118 * 1.0, cy), (cx + 118.0, cy), (cx, cy - 92))):
                tw = 0.5 + 0.5 * math.sin(2 * (ph + k * 0.7))
                p.save()
                p.setOpacity(0.25 * tw)
                p.setBrush(QColor(255, 240, 200))
                p.setPen(Qt.NoPen)
                p.drawPolygon(QPolygonF(_star_pts(sx, sy, 17, 18 * math.degrees(ph) % 30)))
                p.restore()
        # фейд всего окна вниз за последние 500 мс
        rem = self._dur - t
        if rem < 500 or self._closing:
            base = _clamp01(rem / 500) if rem >= 0 else 0.0
            self.setWindowOpacity(max(0.0, base))
        p.end()

    def set_t_for_test(self, ms):
        self._t = ms
        self.update()
