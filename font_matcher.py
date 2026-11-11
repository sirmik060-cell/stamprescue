# font_matcher.py — подбор шрифта по букве (детерминированный)
import os
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from PySide6.QtCore import Qt, QRect
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLabel, QLineEdit, QPushButton, QListWidget, QListWidgetItem, QScrollArea,
    QRubberBand, QWidget)

FONT_DIR = "C:\\Windows\\Fonts"
FONT_MAP = {
 "Arial": ("arial.ttf","arialbd.ttf"), "Arial Black": ("ariblk.ttf","ariblk.ttf"),
 "Times New Roman": ("times.ttf","timesbd.ttf"), "Calibri": ("calibri.ttf","calibrib.ttf"),
 "Calibri Light": ("calibril.ttf","calibril.ttf"), "Cambria": ("cambria.ttc","cambriab.ttc"),
 "Candara": ("candara.ttf","candarab.ttf"), "Corbel": ("corbel.ttf","corbelb.ttf"),
 "Consolas": ("consola.ttf","consolab.ttf"), "Courier New": ("cour.ttf","courbd.ttf"),
 "Comic Sans MS": ("comic.ttf","comicbd.ttf"), "Georgia": ("georgia.ttf","georgiab.ttf"),
 "Impact": ("impact.ttf","impact.ttf"), "Lucida Console": ("lucon.ttf","lucon.ttf"),
 "Segoe UI": ("segoeui.ttf","segoeuib.ttf"), "Segoe Print": ("segoepr.ttf","segoepr.ttf"),
 "Tahoma": ("tahoma.ttf","tahoma.ttf"), "Trebuchet MS": ("trebuc.ttf","trebucbd.ttf"),
 "Verdana": ("verdana.ttf","verdanab.ttf"), "Bahnschrift": ("bahnschrift.ttf","bahnschrift.ttf"),
}
FONT_NAMES = list(FONT_MAP.keys())

def get_font(family, size_px, bold=False):
    f, b = FONT_MAP.get(family, ("arial.ttf","arialbd.ttf"))
    path = os.path.join(FONT_DIR, b if bold else f)
    if not os.path.exists(path): path = os.path.join(FONT_DIR, f)
    try: return ImageFont.truetype(path, max(6, int(size_px)))
    except Exception: return ImageFont.load_default()

def _bgr_qimage(bgr):
    rgb = np.ascontiguousarray(bgr[..., ::-1])
    h, w = rgb.shape[:2]
    return QImage(rgb.data, w, h, 3*w, QImage.Format_RGB888).copy()

def _otsu(g):
    hist,_ = np.histogram(g, bins=256, range=(0,256))
    total = g.size; sumAll = np.dot(np.arange(256), hist)
    sumB=0; wB=0; best=0; thr=128
    for i in range(256):
        wB += hist[i]
        if wB==0: continue
        wF = total-wB
        if wF==0: break
        sumB += i*hist[i]
        mB = sumB/wB; mF = (sumAll-sumB)/wF
        var = wB*wF*(mB-mF)**2
        if var>best: best=var; thr=i
    return thr

def _norm64(mask):
    ys,xs = np.where(mask)
    if len(xs)<4: return None, 0
    sub = mask[ys.min():ys.max()+1, xs.min():xs.max()+1]
    h,w = sub.shape
    aspect = w/max(1,h)
    im = Image.fromarray((sub*255).astype(np.uint8)).resize((64,64), Image.LANCZOS)
    return (np.array(im)>127), aspect

def _letter_mask(crop_bgr):
    rgb = np.ascontiguousarray(crop_bgr[..., ::-1])
    g = np.array(Image.fromarray(rgb).convert("L"))
    return _norm64(g < _otsu(g))

def _glyph_mask(fam, bold, char):
    f = get_font(fam, 96, bold)
    im = Image.new("L",(160,160),0)
    ImageDraw.Draw(im).text((80,80), char, font=f, fill=255, anchor="mm")
    return _norm64(np.array(im)>127)

def match_fonts(crop_bgr, char, top=8):
    target, aspT = _letter_mask(crop_bgr)
    if target is None: return []
    return _score_all(target, aspT, char, top)

def _score_all(target, aspT, char, top=8):
    out=[]
    for fam in FONT_NAMES:
        for bold in (False, True):
            m, asp = _glyph_mask(fam, bold, char)
            if m is None: continue
            inter = np.logical_and(target, m).sum()
            union = np.logical_or(target, m).sum()
            iou = inter/union if union else 0
            out.append((fam, bold, iou*100 - 12*abs(asp-aspT)))
    out.sort(key=lambda t: -t[2])
    return out[:top]

def _mask_label(mask, px=48):
    """Маска 64x64 -> QLabel с белым глифом на тёмном фоне (для списка кандидатов)."""
    arr = np.where(mask, 235, 22).astype(np.uint8)
    im = Image.fromarray(arr, "L").resize((px, px), Image.LANCZOS)
    a = np.ascontiguousarray(np.array(im))
    qimg = QImage(a.data, px, px, px, QImage.Format_Grayscale8).copy()
    lab = QLabel(); lab.setPixmap(QPixmap.fromImage(qimg))
    lab.setFixedSize(px, px)
    return lab

class _SelectLabel(QLabel):
    def __init__(self, pm, on_rect):
        super().__init__()
        self.setPixmap(pm); self.on_rect = on_rect
        self.rb = None; self._start = None
    def mousePressEvent(self, e):
        if e.button()==Qt.LeftButton:
            self._start = e.position().toPoint()
            if self.rb is None: self.rb = QRubberBand(QRubberBand.Rectangle, self)
            self.rb.setGeometry(QRect(self._start, self._start)); self.rb.show()
    def mouseMoveEvent(self, e):
        if self._start is not None and self.rb:
            self.rb.setGeometry(QRect(self._start, e.position().toPoint()).normalized())
    def mouseReleaseEvent(self, e):
        if self._start is not None and self.rb:
            self.on_rect(self.rb.geometry()); self._start = None

class FontMatchDialog(QDialog):
    def __init__(self, page, on_apply):
        super().__init__()
        self.page = page; self.on_apply = on_apply
        self.rect = None; self.results = []
        self.setWindowTitle("Подбор шрифта по букве")
        lay = QVBoxLayout(self)
        sc = QScrollArea(); sc.setWidgetResizable(False)
        self.lbl = _SelectLabel(QPixmap.fromImage(_bgr_qimage(page)), self._set_rect)
        sc.setWidget(self.lbl); lay.addWidget(sc, 1)
        f = QFormLayout()
        self.ed_char = QLineEdit("А"); f.addRow("Какая это буква:", self.ed_char)
        lay.addLayout(f)
        bb = QHBoxLayout()
        c = QPushButton("🔍 Сравнить"); c.clicked.connect(self._compare); bb.addWidget(c)
        a = QPushButton("✅ Применить"); a.clicked.connect(self._apply); bb.addWidget(a)
        n = QPushButton("Отмена"); n.clicked.connect(self.reject); bb.addWidget(n)
        lay.addLayout(bb)
        self.lst = QListWidget(); lay.addWidget(self.lst)
        hint = QLabel("Слева — буква со скана, справа — та же буква в шрифте-кандидате. "
                      "Двойной клик по строке — применить шрифт.")
        hint.setWordWrap(True); hint.setStyleSheet("color:#9aa5b5; font-size:11px;")
        lay.insertWidget(lay.count()-1, hint)
        self.lst.itemDoubleClicked.connect(lambda _it: self._apply())
        self.target_mask = None
        self.resize(1000, 750)
    def _set_rect(self, r): self.rect = r
    def _compare(self):
        if not self.rect: return
        H,W = self.page.shape[:2]
        x0=max(0,self.rect.x()); y0=max(0,self.rect.y())
        x1=min(W,self.rect.x()+self.rect.width()); y1=min(H,self.rect.y()+self.rect.height())
        ch = self.ed_char.text().strip()
        if not ch or x1<=x0 or y1<=y0: return
        self.target_mask, aspT = _letter_mask(self.page[y0:y1, x0:x1])
        if self.target_mask is None:
            self.results = []; self.lst.clear(); return
        self.results = _score_all(self.target_mask, aspT, ch)
        self.lst.clear()
        for fam, bold, sc in self.results:
            it = QListWidgetItem(); self.lst.addItem(it)
            w = QWidget(); h = QHBoxLayout(w); h.setContentsMargins(6,3,6,3); h.setSpacing(8)
            h.addWidget(_mask_label(self.target_mask))
            m, _ = _glyph_mask(fam, bold, ch)
            if m is not None: h.addWidget(_mask_label(m))
            h.addWidget(QLabel(f"{sc:5.1f}   {fam}{'  (жирный)' if bold else ''}"))
            h.addStretch(1)
            it.setSizeHint(w.sizeHint()); self.lst.setItemWidget(it, w)
        if self.results: self.lst.setCurrentRow(0)
    def _apply(self):
        i = self.lst.currentRow()
        if i is not None and 0 <= i < len(self.results):
            fam, bold, sc = self.results[i]
            self.on_apply(fam, bold)
        self.accept()