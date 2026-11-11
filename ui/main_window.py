# ui/main_window.py
import random

import cv2
import numpy as np
from PySide6.QtCore import QRectF, Qt, QThread, QTimer, Signal
from PySide6.QtGui import (
    QColor,
    QFont,
    QIcon,
    QImage,
    QKeySequence,
    QPainter,
    QPen,
    QPixmap,
    QShortcut,
)
from PySide6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QRadioButton,
    QScrollArea,
    QSlider,
    QStatusBar,
    QVBoxLayout,
    QWidget,
)

from core.clean import build_clean_masks, extract_ink, smart_fill
from core.extract import extract_region
from core.image_io import Document, save_pdf, save_png
from core.inpaint import (
    LamaInpainter,
    blend_result,
    build_frame_mask,
    find_lama_model,
    opencv_inpaint,
)
from core.paper import paper_patch
from stamp_builder import BuilderWindow
from ui.canvas_view import CanvasView, bgr_to_pixmap

VERSION = "0.5"

LANG = {
    "RU": {
        "open": "📂 Открыть", "fit": "Вписать", "undo": "↶ Отменить",
        "hold": "👁 До/После", "save_png": "💾 PNG", "save_pdf": "💾 PDF",
        "area": "ОБЛАСТЬ", "shape_rect": "Прямоугольник",
        "shape_ellipse": "Эллипс (круглая печать)", "feather": "Мягкость края",
        "render": "РЕНДЕР PDF", "engine": "ДВИЖОК ВОССТАНОВЛЕНИЯ",
        "eng_paper": "Бумага (идеальный фон)",
        "eng_paper_sub": "замер бумаги вокруг → без границ",
        "eng_fast": "Быстрый (OpenCV)", "eng_ai": "Сложный фон / фото (LaMa)",
        "eng_fast_sub": "сохранит линии под печатью",
        "eng_ai_sub": "дорисовывает фон сам; фото/пёстрый фон",
        "model_ok": "● модель lama.onnx найдена",
        "model_no": "● lama.onnx не найдена — положите в папку models",
        "restore": "ВОССТАНОВИТЬ", "extract": "✂  Вырезать в PNG",
        "clean_sect": "ОЧИСТКА ПЕЧАТИ",
        "mode_sect": "ЗАДАЧА",
        "mode_fon": "ФОН", "mode_clean": "ПЕЧАТЬ",
        "mode_ins": "ВСТАВКА", "mode_all": "ВСЁ",
        "hint_mode_fon": "Режим ФОН: рамка → движок → «Восстановить». Инструменты очистки погашены.",
        "hint_mode_pechat": "Режим ПЕЧАТЬ: пипетки свой/чужое/фон → допуск → маска → «Очистить».",
        "hint_mode_ins": "Режим ВСТАВКА: создайте печать в Конструкторе или вставьте сохранённый PNG.",
        "hint_mode_all": "Инструменты всех задач включены.",
        "insert_sect": "ВСТАВКА ПЕЧАТИ",
        "btn_ctor_side": "Создать печать (Конструктор)",
        "btn_png": "Вставить из PNG…",
        "pip_bg": "🎯  Пипетка: ФОН",
        "pip_bg_tip": "Пиксели, близкие к цвету фона, очистка не тронет",
        "err_png": "Не удалось открыть PNG",
        "pip_own": "🎯  Пипетка: СВОЙ",
        "pip_own_tip": "Цвет своих чернил печати — очищать вокруг него",
        "pip_foreign": "🎯  Пипетка: ЧУЖОЙ",
        "pip_foreign_tip": "Цвет чужой записи (подписи/штамп другого цвета). До 3 кликов — несколько эталонов",
        "tol": "Допуск цвета",
        "clean_btn": "🧹  Очистить печать",
        "sw_not": "не взят",
        "clean_need_own": "Сначала возьмите СВОЙ цвет пипеткой (клик по чернилам печати).",
        "clean_no_foreign": "Чужих объектов не найдено — покрутите «Допуск цвета» или возьмите ЧУЖОЙ цвет пипеткой.",
        "clean_hint": "Порядок: рамка → пипетка СВОЙ → (опц.) пипетка ЧУЖОЙ → «Очистить печать» → «Вырезать в PNG» (вырежет по контуру чернил, без белого фона).",
        "hint_start": "Откройте PDF или изображение…",
        "hint_frame": "Зажмите ЛКМ и обведите печать. Колесо — масштаб, СКМ/Пробел — панорама, ПКМ — сброс рамки.",
        "hint_ready": "«Восстановить» — дорисовать под рамкой. «Вырезать» — сохранить область в PNG.",
        "hint_working": "Обработка…", "hint_done": "Готово. Ctrl+Z — отменить, Esc — сбросить рамку.",
        "loading": "Загрузка модели LaMa…", "fallback": "LaMa не найдена — использован OpenCV.",
        "err_open": "Не удалось открыть файл", "err_proc": "Ошибка обработки",
        "page": "Стр.", "extracted": "Вырезано: ", "saved": "Сохранено: ",
    },
    "EN": {
        "open": "📂 Open", "fit": "Fit", "undo": "↶ Undo",
        "hold": "👁 Before/After", "save_png": "💾 PNG", "save_pdf": "💾 PDF",
        "area": "REGION", "shape_rect": "Rectangle",
        "shape_ellipse": "Ellipse (round stamp)", "feather": "Edge feather",
        "render": "PDF RENDER", "engine": "RESTORATION ENGINE",
        "eng_paper": "Paper (seamless)",
        "eng_paper_sub": "samples surrounding paper → no seams",
        "eng_fast": "Fast (OpenCV)", "eng_ai": "Complex background / photo (LaMa)",
        "eng_fast_sub": "keeps lines under the stamp",
        "eng_ai_sub": "redraws background itself; photos / busy backgrounds",
        "model_ok": "● lama.onnx model found",
        "model_no": "● lama.onnx not found — put it into models/",
        "restore": "RESTORE", "extract": "✂  Extract to PNG",
        "clean_sect": "STAMP CLEANUP",
        "mode_sect": "TASK",
        "mode_fon": "BG", "mode_clean": "STAMP",
        "mode_ins": "INSERT", "mode_all": "ALL",
        "hint_mode_fon": "BACKGROUND mode: frame → engine → RESTORE. Cleanup tools are dimmed.",
        "hint_mode_pechat": "STAMP mode: own/foreign/bg pipettes → tolerance → mask → CLEAN.",
        "hint_mode_ins": "INSERT mode: build a stamp in Constructor or insert a saved PNG.",
        "hint_mode_all": "Tools of every task are enabled.",
        "insert_sect": "INSERT STAMP",
        "btn_ctor_side": "Create stamp (Constructor)",
        "btn_png": "Insert from PNG…",
        "pip_bg": "🎯  Pipette: BG",
        "pip_bg_tip": "Pixels close to the background color are never touched",
        "err_png": "Failed to open PNG",
        "pip_own": "🎯  Pipette: OWN",
        "pip_own_tip": "The stamp's own ink color — clean around it",
        "pip_foreign": "🎯  Pipette: FOREIGN",
        "pip_foreign_tip": "Foreign ink (signatures / other-color stamps). Up to 3 clicks — several references",
        "tol": "Color tolerance",
        "clean_btn": "🧹  Clean stamp",
        "sw_not": "not set",
        "clean_need_own": "First pick the OWN color with the pipette (click the stamp ink).",
        "clean_no_foreign": "No foreign objects found — adjust 'Color tolerance' or pick the FOREIGN color.",
        "clean_hint": "Order: frame → pipette OWN → (opt.) pipette FOREIGN → 'Clean stamp' → 'Extract to PNG' (cuts by ink contour, no white box).",
        "hint_start": "Open a PDF or an image…",
        "hint_frame": "Hold LMB and draw a frame around the stamp. Wheel — zoom, MMB/Space — pan, RMB — clear.",
        "hint_ready": "'Restore' — inpaint under the frame. 'Extract' — save the region as PNG.",
        "hint_working": "Processing…", "hint_done": "Done. Ctrl+Z — undo, Esc — clear frame.",
        "loading": "Loading LaMa model…", "fallback": "LaMa not found — used OpenCV.",
        "err_open": "Cannot open file", "err_proc": "Processing error",
        "page": "Page", "extracted": "Extracted: ", "saved": "Saved: ",
    },
}

THEME = """
QMainWindow, QWidget { background:#14171d; color:#d7dde6;
    font-family:"Segoe UI"; font-size:13px; }
QFrame#toolbar { background:#191d24; border-bottom:1px solid #262c36; }
QFrame#sidebar { background:qlineargradient(x1:0,y1:0,x2:0,y2:1,
    stop:0 #1a1f27, stop:1 #14171d); border-right:1px solid #262c36; }
QScrollArea#side_scroll { background:transparent; border:none; }
QWidget#side_body { background:transparent; }
QScrollBar:vertical { background:transparent; width:9px; margin:2px; }
QScrollBar::handle:vertical { background:#39424f; border-radius:4px; min-height:30px; }
QScrollBar::handle:vertical:hover { background:#4a5566; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height:0; }
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background:transparent; }
QPushButton { background:#232a35; border:1px solid #313a48; border-radius:7px;
    padding:7px 13px; font-weight:600; }
QPushButton:hover { background:#2c3543; border-color:#41506a; }
QPushButton:pressed { background:#1c222c; }
QPushButton:disabled { background:#1a1f28; color:#57606e; border-color:#262c36; }
QPushButton#primary { background:qlineargradient(x1:0,y1:0,x2:0,y2:1,
    stop:0 #f2a31c, stop:1 #d9880a); color:#221503; border:none;
    font-family:Bahnschrift; font-size:14px; font-weight:700; letter-spacing:1px; }
QPushButton#primary:hover { background:qlineargradient(x1:0,y1:0,x2:0,y2:1,
    stop:0 #ffb62e, stop:1 #e8960f); }
QPushButton#primary:disabled { background:#3a3325; color:#6e6350; }
QPushButton#teal { background:#17343a; color:#7fdbe4; border:1px solid #2a6d78; }
QPushButton#teal:hover { background:#1d454d; }
QPushButton#teal:disabled { background:#1a2226; color:#4d5e62; border-color:#26333a; }
QPushButton#clean { background:qlineargradient(x1:0,y1:0,x2:0,y2:1,
    stop:0 #8b5cf6, stop:1 #6d28d9); color:#fff; border:none;
    font-family:Bahnschrift; font-size:13px; font-weight:700; letter-spacing:1px; }
QPushButton#clean:hover { background:qlineargradient(x1:0,y1:0,x2:0,y2:1,
    stop:0 #9d6bff, stop:1 #7c3aed); }
QPushButton#clean:disabled { background:#1d222c; color:#4f4a5e; border-color:#2c3543; }
QPushButton#pip { background:#241d33; color:#c4b5fd; border:1px solid #4c3a78;
    text-align:left; }
QPushButton#pip:hover { background:#2e2442; }
QPushButton#pip[active="true"] { background:#4c3a78; color:#fff; border-color:#8b5cf6; }
QLabel#sect { font-family:Bahnschrift; font-size:11px; font-weight:700;
    letter-spacing:2px; color:#8b95a5; padding-top:10px; }
QLabel#logo { font-family:Bahnschrift; font-size:19px; font-weight:700;
    color:#f5a524; letter-spacing:3px; }
QLabel#sub { font-size:10px; color:#6d7787; }
QFrame#hint { background:#1c212b; border-left:3px solid #f5a524; border-radius:4px; }
QRadioButton { spacing:7px; padding:3px 0; }
QPushButton#mode { padding:7px 2px; font-size:11px; font-weight:700; letter-spacing:1px;
    background:#161b23; color:#57606e; border:1px solid #2c3543; border-radius:5px; }
QPushButton#mode[active="true"] { background:#3f2e10; color:#ffb62e;
    border:1px solid #f5a524; }
QPushButton#mode:hover { color:#9aa5b5; }
QLabel:disabled { color:#454e5c; }
QRadioButton:disabled { color:#525b68; }
QPushButton#pip:disabled { background:#141922; color:#454e5c; border:1px solid #232a35; }
QSlider::groove:horizontal:disabled { background:#1c222c; }
QSlider::handle:horizontal:disabled { background:#39424f; }
QRadioButton::indicator { width:14px; height:14px; border-radius:7px;
    border:2px solid #4a5568; background:#10141a; }
QRadioButton::indicator:checked { border-color:#f5a524; background:#f5a524; }
QRadioButton::indicator:checked:disabled { border-color:#5a6270; background:#5a6270; }
QCheckBox { spacing:7px; padding:3px 0; }
QCheckBox::indicator { width:14px; height:14px; border:2px solid #5b687c; border-radius:4px;
    background:#10141a; }
QCheckBox::indicator:checked { border-color:#f5a524; background:#f5a524; }
QCheckBox::indicator:disabled { border-color:#39424f; background:#171c24; }
QSlider::groove:horizontal { height:4px; background:#2a3140; border-radius:2px; }
QSlider::handle:horizontal { width:14px; margin:-5px 0; border-radius:7px;
    background:#f5a524; }
QSlider::handle:horizontal:hover { background:#ffb62e; }
QComboBox { background:#232a35; border:1px solid #313a48; border-radius:6px;
    padding:5px 9px; }
QComboBox:hover { border-color:#41506a; }
QComboBox QAbstractItemView { background:#1d232d; selection-background-color:#2c3543; }
QStatusBar { background:#101318; border-top:1px solid #262c36; }
"""


def make_stamp_icon(size=128):
    """Рисуем печать программно — иконка без внешних файлов."""
    img = QImage(size, size, QImage.Format_ARGB32)
    img.fill(Qt.transparent)
    p = QPainter(img)
    p.setRenderHint(QPainter.Antialiasing)
    amber = QColor("#f5a524")
    p.setPen(QPen(amber, 9))
    p.drawEllipse(9, 9, size - 18, size - 18)
    p.setPen(QPen(amber, 4))
    p.drawEllipse(24, 24, size - 48, size - 48)
    p.setPen(QPen(amber, 8, Qt.SolidLine, Qt.RoundCap))
    p.drawLine(44, 68, 60, 84)
    p.drawLine(60, 84, 90, 46)
    p.end()
    return QIcon(QPixmap.fromImage(img))


class OpenCVEngine:
    def __call__(self, bgr, mask):
        return opencv_inpaint(bgr, mask, radius=6)


class InpaintWorker(QThread):
    done = Signal(object)
    failed = Signal(str)

    def __init__(self, engine, image, mask):
        super().__init__()
        self.engine, self.image, self.mask = engine, image, mask

    def run(self):
        try:
            self.done.emit(self.engine(self.image, self.mask))
        except Exception as e:
            self.failed.emit(str(e))


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.lang_code = "RU"
        self._tr_tip = {}
        self.doc = None
        self.current_page = 0
        self.dpi = 300
        self.edited = {}          # idx -> bgr (только правленые страницы)
        self.undo_stack = []      # [(idx, prev_bgr|None)]
        self.shape_kind = "rect"
        self.feather = 6
        self._worker = None
        self._lama = None
        self._pending = None
        self._last_rect = None
        self._tr = {}
        self.own_color = None
        self.foreign_color = None
        self.foreign_colors = []      # до 3 эталонов ЧУЖОГО (мульти-пипетка)
        self.bg_color = None          # пипетка ФОНА: близко к фону — не трогать
        self._pip_mode = None
        self.tol = 35
        # --- режим задач: включаем только инструменты выбранной задачи ---
        self._mode = "all"
        self._sect_lbl = {}           # секция -> её заголовки/подсказки (для подсветки)
        self._cur_sect = None
        self._groups = {}
        self._mode_groups = {"fon": {"area", "frame", "engine"},
                             "pechat": {"area", "frame", "clean"},
                             "ins": {"insert"},
                             "all": {"area", "frame", "engine", "clean", "insert"}}

        self.setWindowTitle(f"StampRescue v{VERSION} — Sirmik Edition")
        self.setWindowIcon(make_stamp_icon())
        self.resize(1380, 900)
        self._build_ui()
        self.retranslate()
        self._status("hint_start")
        self._mask_debounce = QTimer(self)
        self._mask_debounce.setSingleShot(True)
        self._mask_debounce.setInterval(150)
        self._mask_debounce.timeout.connect(self._preview_masks)
        self._set_mode("fon")

    def t(self, key):
        return LANG[self.lang_code][key]

    # ================= UI =================
    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        root.addWidget(self._build_toolbar())

        body = QHBoxLayout()
        body.setSpacing(0)
        body.addWidget(self._build_sidebar())

        self.view = CanvasView()
        self.view.frame_changed.connect(self._on_frame)
        self.view.pipette_clicked.connect(self._on_pip_click)
        self.view.mask_changed.connect(self._on_mask_changed)
        self.view.zoom_changed.connect(lambda z: self.lbl_zoom.setText(f"{z*100:.0f}%"))
        body.addWidget(self.view, 1)

        wrap = QWidget()
        wrap.setLayout(body)
        root.addWidget(wrap, 1)

        sb = QStatusBar()
        self.setStatusBar(sb)
        self.lbl_status = QLabel()
        sb.addWidget(self.lbl_status, 1)
        self.progress = QProgressBar()
        self.progress.setRange(0, 0)
        self.progress.setFixedWidth(130)
        self.progress.setVisible(False)
        sb.addPermanentWidget(self.progress)
        self.lbl_info = QLabel("—")
        sb.addPermanentWidget(self.lbl_info)

        QShortcut(QKeySequence("Ctrl+Z"), self, activated=self.undo)
        QShortcut(QKeySequence("Esc"), self, activated=self.view.clear_frame)

    def _tb(self, key, slot, obj=None, w=None):
        b = QPushButton()
        if obj:
            b.setObjectName(obj)
        if w:
            b.setFixedWidth(w)
        b.clicked.connect(slot)
        self._tr[b] = key
        return b
    def _add_sub(self, layout, key):
        l = QLabel()
        l.setObjectName("sub")
        l.setStyleSheet("color:#6d7787; font-size:10px; padding:0 0 4px 22px;")
        self._tr[l] = key
        layout.addWidget(l)


    def _build_toolbar(self):
        bar = QFrame()
        bar.setObjectName("toolbar")
        bar.setFixedHeight(56)
        h = QHBoxLayout(bar)
        h.setContentsMargins(12, 8, 12, 8)
        h.setSpacing(6)

        self.btn_open = self._tb("open", self.open_file)
        h.addWidget(self.btn_open)
        h.addSpacing(10)

        self.btn_prev = QPushButton("◀")
        self.btn_prev.setFixedWidth(36)
        self.btn_prev.clicked.connect(lambda: self._nav(-1))
        self.btn_prev.setEnabled(False)
        h.addWidget(self.btn_prev)
        self.lbl_page = QLabel("—")
        self.lbl_page.setFixedWidth(80)
        self.lbl_page.setAlignment(Qt.AlignCenter)
        h.addWidget(self.lbl_page)
        self.btn_next = QPushButton("▶")
        self.btn_next.setFixedWidth(36)
        self.btn_next.clicked.connect(lambda: self._nav(1))
        self.btn_next.setEnabled(False)
        h.addWidget(self.btn_next)
        h.addSpacing(10)

        b = QPushButton("−")
        b.setFixedWidth(36)
        b.clicked.connect(lambda: self.view.zoom(0.8))
        h.addWidget(b)
        self.lbl_zoom = QLabel("100%")
        self.lbl_zoom.setFixedWidth(52)
        self.lbl_zoom.setAlignment(Qt.AlignCenter)
        h.addWidget(self.lbl_zoom)
        b = QPushButton("+")
        b.setFixedWidth(36)
        b.clicked.connect(lambda: self.view.zoom(1.25))
        h.addWidget(b)
        self.btn_fit = self._tb("fit", lambda: self.view.fit_view())
        h.addWidget(self.btn_fit)
        h.addSpacing(10)

        self.btn_undo = self._tb("undo", self.undo)
        self.btn_undo.setEnabled(False)
        h.addWidget(self.btn_undo)

        self.btn_hold = self._tb("hold", lambda: None)
        self.btn_hold.pressed.connect(self._show_original)
        self.btn_hold.released.connect(self._show_current)
        h.addWidget(self.btn_hold)

        h.addStretch(1)

        self.btn_png = self._tb("save_png", self.save_png_page)
        h.addWidget(self.btn_png)
        self.btn_pdf = self._tb("save_pdf", self.save_pdf_doc)
        h.addWidget(self.btn_pdf)

        self.btn_builder = QPushButton("🏗 Конструктор")
        self.btn_builder.clicked.connect(self.open_builder)
        h.addWidget(self.btn_builder)

        self.lang_choice = QComboBox()
        self.lang_choice.addItems(["RU", "EN"])
        self.lang_choice.setFixedWidth(64)
        self.lang_choice.activated.connect(self._on_lang)
        h.addWidget(self.lang_choice)
        return bar

    def _build_sidebar(self):
        side = QFrame()
        side.setObjectName("sidebar")
        side.setFixedWidth(272)
        # контент панели выше любого экрана (режимы+пипетки+вставка) — только скролл,
        # иначе Qt сжимает кнопки ниже высоты шрифта (текст обрезан, «кнопок не видно»)
        outer = QVBoxLayout(side)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)
        scr = QScrollArea()
        scr.setObjectName("side_scroll")
        scr.setWidgetResizable(True)
        scr.setFrameShape(QFrame.NoFrame)
        scr.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        body = QWidget()
        body.setObjectName("side_body")
        scr.setWidget(body)
        outer.addWidget(scr)
        v = QVBoxLayout(body)
        v.setContentsMargins(16, 14, 16, 14)
        v.setSpacing(4)

        def sect(key):
            l = QLabel()
            l.setObjectName("sect")
            self._tr[l] = key
            self._cur_sect = key
            self._sect_lbl.setdefault(key, []).append(l)
            v.addWidget(l)

        def sub(key):
            l = QLabel()
            l.setObjectName("sub")
            l.setStyleSheet("color:#6d7787; font-size:10px; padding:0 0 4px 22px;")
            try:
                l.setText(self.t(key))
                self._tr[l] = key
                self._sect_lbl.setdefault(self._cur_sect, []).append(l)
            except Exception:
                l.setText("")
            v.addWidget(l)

        # --- лого ---
        logo_row = QHBoxLayout()
        ic = QLabel()
        ic.setPixmap(make_stamp_icon().pixmap(42, 42))
        logo_row.addWidget(ic)
        lt = QVBoxLayout()
        lbl = QLabel("STAMP RESCUE")
        lbl.setObjectName("logo")
        f = lbl.font(); f.setLetterSpacing(QFont.AbsoluteSpacing, 2.5)
        lbl.setFont(f)
        lt.addWidget(lbl)
        sub_l = QLabel(f"v{VERSION} · Sirmik Edition")
        sub_l.setObjectName("sub")
        lt.addWidget(sub_l)
        logo_row.addLayout(lt)
        logo_row.addStretch(1)
        v.addLayout(logo_row)
        v.addSpacing(8)

        # --- выбор задачи: подсвечиваем инструменты только активной задачи ---
        sect("mode_sect")
        mrow = QHBoxLayout()
        mrow.setSpacing(5)
        self.mode_btns = {}
        for _mk, _key in (("fon", "mode_fon"), ("pechat", "mode_clean"),
                          ("ins", "mode_ins"), ("all", "mode_all")):
            b = QPushButton()
            b.setObjectName("mode")
            b.setCheckable(True)
            b.setProperty("active", False)
            self._tr[b] = _key
            b.clicked.connect(lambda _=False, mm=_mk: self._set_mode(mm))
            mrow.addWidget(b)
            self.mode_btns[_mk] = b
        v.addLayout(mrow)
        v.addSpacing(6)

        # --- область ---
        sect("area")
        self.rb_rect = QRadioButton()
        self.rb_rect.setChecked(True)
        self.rb_rect.toggled.connect(self._on_shape)
        self._tr[self.rb_rect] = "shape_rect"
        v.addWidget(self.rb_rect)
        self.rb_ell = QRadioButton()
        self._tr[self.rb_ell] = "shape_ellipse"
        v.addWidget(self.rb_ell)

        row = QHBoxLayout()
        fl = QLabel()
        self._tr[fl] = "feather"
        row.addWidget(fl)
        self.lbl_feather = QLabel("6 px")
        row.addWidget(self.lbl_feather)
        v.addLayout(row)
        self.sl_feather = QSlider(Qt.Horizontal)
        self.sl_feather.setRange(0, 30)
        self.sl_feather.setValue(6)
        self.sl_feather.valueChanged.connect(self._on_feather)
        v.addWidget(self.sl_feather)

        # --- рендер pdf ---
        sect("render")
        self.dpi_choice = QComboBox()
        self.dpi_choice.addItems(["150", "200", "300", "400 dpi"])
        self.dpi_choice.setCurrentIndex(2)
        self.dpi_choice.activated.connect(self._on_dpi)
        v.addWidget(self.dpi_choice)

        # --- движок ---
        sect("engine")
        self.rb_paper = QRadioButton()
        self.rb_paper.setChecked(True)
        self._tr[self.rb_paper] = "eng_paper"
        v.addWidget(self.rb_paper)
        sub("eng_paper_sub")
        self.rb_fast = QRadioButton()
        self._tr[self.rb_fast] = "eng_fast"
        v.addWidget(self.rb_fast)
        sub("eng_fast_sub")
        self.rb_ai = QRadioButton()
        self._tr[self.rb_ai] = "eng_ai"
        v.addWidget(self.rb_ai)
        sub("eng_ai_sub")
        self.lbl_model = QLabel()
        self.lbl_model.setWordWrap(True)
        v.addWidget(self.lbl_model)
        self._refresh_model_label()

        v.addSpacing(12)
        self.btn_restore = self._tb("restore", self.restore, obj="primary")
        self.btn_restore.setFixedHeight(46)
        self.btn_restore.setEnabled(False)
        v.addWidget(self.btn_restore)
        self.btn_extract = self._tb("extract", self.extract, obj="teal")
        self.btn_extract.setFixedHeight(38)
        self.btn_extract.setEnabled(False)
        v.addWidget(self.btn_extract)

        # --- очистка печати ---
        sect("clean_sect")
        tools_row = QHBoxLayout()
        self.btn_tool_frame = QPushButton("🖱 Рамка")
        self.btn_tool_frame.setObjectName("pip")
        self.btn_tool_frame.clicked.connect(lambda: self._set_tool("frame"))
        tools_row.addWidget(self.btn_tool_frame)
        self.btn_tool_rect = QPushButton("⬛ Рамка: стереть")
        self.btn_tool_rect.setObjectName("pip")
        self.btn_tool_rect.clicked.connect(lambda: self._set_tool("rect"))
        self.btn_tool_rect.setToolTip(
            "Инструмент: обведите прямоугольником лишнее — область будет стёрта "
            "без цветовой проверки (приказ, как кисть, но сразу рамкой)")
        tools_row.addWidget(self.btn_tool_rect)
        v.addLayout(tools_row)
        tools_row2 = QHBoxLayout()
        self.btn_tool_brush = QPushButton("✏️ Кисть")
        self.btn_tool_brush.setObjectName("pip")
        self.btn_tool_brush.clicked.connect(lambda: self._set_tool("brush"))
        tools_row2.addWidget(self.btn_tool_brush)
        self.btn_tool_erase = QPushButton("🧽 Ластик")
        self.btn_tool_erase.setObjectName("pip")
        self.btn_tool_erase.clicked.connect(lambda: self._set_tool("erase"))
        tools_row2.addWidget(self.btn_tool_erase)
        v.addLayout(tools_row2)

        row_br = QHBoxLayout()
        row_br.addWidget(QLabel("Кисть, px"))
        self.lbl_brush = QLabel("12")
        row_br.addWidget(self.lbl_brush)
        v.addLayout(row_br)
        self.sl_brush = QSlider(Qt.Horizontal)
        self.sl_brush.setRange(3, 60)
        self.sl_brush.setValue(12)
        self.sl_brush.valueChanged.connect(self._on_brush)
        v.addWidget(self.sl_brush)

        self.btn_clear_mask = QPushButton("🗑  Сбросить пометки")
        self.btn_clear_mask.setObjectName("teal")
        self.btn_clear_mask.setFixedHeight(30)
        self.btn_clear_mask.clicked.connect(self._clear_mask)
        v.addWidget(self.btn_clear_mask)
        self.lbl_mask_count = QLabel("помечено: 0 px")
        self.lbl_mask_count.setStyleSheet("color:#9aa5b5; font-size:10px;")
        v.addWidget(self.lbl_mask_count)
        row_own = QHBoxLayout()
        self.btn_pip_own = QPushButton()
        self.btn_pip_own.setObjectName("pip")
        self.btn_pip_own.setProperty("active", False)
        self._tr[self.btn_pip_own] = "pip_own"
        self._tr_tip[self.btn_pip_own] = "pip_own_tip"
        self.btn_pip_own.clicked.connect(lambda: self._set_pip_mode(
            None if self._pip_mode == "own" else "own"))
        row_own.addWidget(self.btn_pip_own, 1)
        self.sw_own = QLabel()
        self.sw_own.setFixedSize(22, 22)
        self._paint_swatch(self.sw_own, None)
        row_own.addWidget(self.sw_own)
        v.addLayout(row_own)

        row_for = QHBoxLayout()
        self.btn_pip_foreign = QPushButton()
        self.btn_pip_foreign.setObjectName("pip")
        self.btn_pip_foreign.setProperty("active", False)
        self._tr[self.btn_pip_foreign] = "pip_foreign"
        self._tr_tip[self.btn_pip_foreign] = "pip_foreign_tip"
        self.btn_pip_foreign.clicked.connect(lambda: self._set_pip_mode(
            None if self._pip_mode == "foreign" else "foreign"))
        row_for.addWidget(self.btn_pip_foreign, 1)
        self.sw_foreign = QLabel()
        self.sw_foreign.setFixedSize(22, 22)
        self._paint_swatch(self.sw_foreign, None)
        row_for.addWidget(self.sw_foreign)
        self.btn_for_reset = QPushButton("✕")
        self.btn_for_reset.setFixedWidth(26)
        self.btn_for_reset.setToolTip("Сбросить эталоны ЧУЖОГО цвета")
        self.btn_for_reset.clicked.connect(self._reset_foreign)
        row_for.addWidget(self.btn_for_reset)
        v.addLayout(row_for)
        row_bg = QHBoxLayout()
        self.btn_pip_bg = QPushButton()
        self.btn_pip_bg.setObjectName("pip")
        self.btn_pip_bg.setProperty("active", False)
        self._tr[self.btn_pip_bg] = "pip_bg"
        self._tr_tip[self.btn_pip_bg] = "pip_bg_tip"
        self.btn_pip_bg.clicked.connect(lambda: self._set_pip_mode(
            None if self._pip_mode == "bg" else "bg"))
        row_bg.addWidget(self.btn_pip_bg, 1)
        self.sw_bg = QLabel()
        self.sw_bg.setFixedSize(22, 22)
        self._paint_swatch(self.sw_bg, None)
        row_bg.addWidget(self.sw_bg)
        v.addLayout(row_bg)

        row_tol = QHBoxLayout()
        tl = QLabel()
        self._tr[tl] = "tol"
        row_tol.addWidget(tl)
        self.lbl_tol = QLabel("35")
        row_tol.addWidget(self.lbl_tol)
        v.addLayout(row_tol)
        self.sl_tol = QSlider(Qt.Horizontal)
        self.sl_tol.setRange(5, 90)
        self.sl_tol.setValue(35)
        self.sl_tol.valueChanged.connect(self._on_tol)
        v.addWidget(self.sl_tol)

        self.btn_clean = QPushButton()
        self.btn_clean.setObjectName("clean")
        self.btn_clean.setFixedHeight(40)
        self._tr[self.btn_clean] = "clean_btn"
        self.btn_clean.setEnabled(False)
        self.btn_clean.clicked.connect(self.clean_stamp)
        v.addWidget(self.btn_clean)

        self.btn_preview_mask = QPushButton("👁  Показать маску / Mask")
        self.btn_preview_mask.setObjectName("teal")
        self.btn_preview_mask.setFixedHeight(32)
        self.btn_preview_mask.setEnabled(False)
        self.btn_preview_mask.clicked.connect(self._preview_masks)
        v.addWidget(self.btn_preview_mask)

        # --- вставка печати: конструктор или ранее вырезанный PNG ---
        sect("insert_sect")
        self.btn_ctor_side = QPushButton()
        self._tr[self.btn_ctor_side] = "btn_ctor_side"
        self.btn_ctor_side.clicked.connect(self.open_builder)
        v.addWidget(self.btn_ctor_side)
        self.btn_insert_png = QPushButton()
        self.btn_insert_png.setObjectName("teal")
        self._tr[self.btn_insert_png] = "btn_png"
        self.btn_insert_png.clicked.connect(self.insert_from_png)
        v.addWidget(self.btn_insert_png)

        self._collect_groups()

        v.addStretch(1)

        hint_box = QFrame()
        hint_box.setObjectName("hint")
        hv = QVBoxLayout(hint_box)
        hv.setContentsMargins(10, 8, 10, 8)
        self.lbl_hint = QLabel()
        self.lbl_hint.setWordWrap(True)
        hv.addWidget(self.lbl_hint)
        v.addWidget(hint_box)
        return side

    # ================= состояние =================
    def current_image(self):
        if self.current_page in self.edited:
            return self.edited[self.current_page]
        return self.doc.render_page(self.current_page, self.dpi)

    def _reload_page(self, restore_rect=None):
        if not self.doc:
            return
        self.view.set_image(self.current_image(), restore_rect)
        n = self.doc.page_count
        self.lbl_page.setText(f"{self.current_page + 1} / {n}")
        self.btn_prev.setEnabled(self.current_page > 0)
        self.btn_next.setEnabled(self.current_page < n - 1)
        self.lbl_info.setText(f"{self.doc.kind.upper()} · {self.dpi} dpi")

    def _nav(self, d):
        if not self.doc:
            return
        np_ = self.current_page + d
        if 0 <= np_ < self.doc.page_count:
            self.current_page = np_
            self._reload_page()

    def _set_hint(self, key):
        self._hint_key = key
        self.lbl_hint.setText(self.t(key))

    def _status(self, key):
        self.lbl_status.setText(self.t(key))

    def _set_busy(self, on):
        self.progress.setVisible(on)
        self.btn_restore.setEnabled(not on)
        self.btn_extract.setEnabled(not on)
        self.btn_open.setEnabled(not on)

    # ================= действия =================
    def open_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "StampRescue",
            "", "PDF / Images (*.pdf *.png *.jpg *.jpeg *.bmp *.tif *.tiff);;All (*.*)")
        if not path:
            return
        try:
            if self.doc:
                self.doc.close()
            self.doc = Document(path)
            self.current_page = 0
            self.edited.clear()
            self.undo_stack.clear()
            self.btn_undo.setEnabled(False)
            self._reload_page()
            self._set_hint("hint_frame")
        except Exception as e:
            QMessageBox.critical(self, "StampRescue", f"{self.t('err_open')}:\n{e}")

    def _rect_tuple(self, rect):
        return (rect.x(), rect.y(), rect.x() + rect.width(), rect.y() + rect.height())

    def _get_engine(self):
        if self.rb_ai.isChecked():
            model = find_lama_model()
            if model:
                if self._lama is None:
                    self._status("loading")
                    self._lama = LamaInpainter(model)
                return self._lama
            QMessageBox.warning(self, "StampRescue", self.t("fallback"))
        return OpenCVEngine()

    def restore(self):
        rect = self.view.frame_rect()
        if rect is None or not self.doc:
            return
        img = self.current_image().copy()
        mask = build_frame_mask(img.shape[:2], self._rect_tuple(rect),
                                self.shape_kind, self.feather)
        if mask is None:
            return

        if self.rb_paper.isChecked():
            self.undo_stack.append((self.current_page,
                                    self.edited.get(self.current_page)))
            if len(self.undo_stack) > 10:
                self.undo_stack.pop(0)
            self.btn_undo.setEnabled(True)
            seed = random.randint(0, 2_147_483_647)
            result = paper_patch(img, self._rect_tuple(rect),
                                 self.shape_kind, band=6, seed=seed)
            self.edited[self.current_page] = result
            self._last_rect = QRectF(rect)
            self._reload_page(restore_rect=self._last_rect)
            self._status("hint_done")
            self._set_hint("hint_ready")
            return

        self.undo_stack.append((self.current_page,
                                self.edited.get(self.current_page)))
        if len(self.undo_stack) > 10:
            self.undo_stack.pop(0)
        self.btn_undo.setEnabled(True)

        self._pending = (self.current_page, img, mask)
        self._last_rect = QRectF(rect)
        self._set_busy(True)
        self._status("hint_working")

        self._worker = InpaintWorker(self._get_engine(), img, mask)
        self._worker.done.connect(self._on_done)
        self._worker.failed.connect(self._on_failed)
        self._worker.start()

    def _on_done(self, result):
        page, img, mask = self._pending
        self._pending = None
        self._worker = None
        self.edited[page] = blend_result(img, result, mask)
        self._set_busy(False)
        self._reload_page(restore_rect=self._last_rect)
        self._status("hint_done")
        self._set_hint("hint_ready")

    def _on_failed(self, msg):
        self._pending = None
        self._worker = None
        self._set_busy(False)
        QMessageBox.critical(self, "StampRescue", f"{self.t('err_proc')}:\n{msg}")

    def extract(self):
        rect = self.view.frame_rect()
        if rect is None or not self.doc:
            return
        img = self.current_image()
        if self.own_color is not None:
            masks = build_clean_masks(img, self._rect_tuple(rect), self.own_color,
                                      self.foreign_colors, self.tol, self.shape_kind,
                                      bg_bgr=self.bg_color)
            bgra = extract_ink(img, masks["own"],
                               feather=max(1, self.feather // 2), padding=8)
        else:
            bgra = extract_region(img, self._rect_tuple(rect), self.shape_kind,
                                  feather=max(1, self.feather // 2))
        if bgra is None:
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "StampRescue", "stamp.png", "PNG (*.png)")
        if path:
            save_png(bgra, path)
            self.lbl_status.setText(self.t("extracted") + path)

    # ---------- пипетки / очистка ----------
    def open_builder(self):
        try:
            w = BuilderWindow(self)
            w.show()
        except Exception as e:
            QMessageBox.critical(self, "StampRescue", f"Конструктор: {e}")

    # ---------- режим задач ----------
    def _collect_groups(self):
        """Списки виджетов по группам: режим включает только нужную группу."""
        def w(*names):
            out = []
            for n in names:
                wd = getattr(self, n, None)
                if wd is not None:
                    out.append(wd)
            return out

        def labels(*keys):
            out = []
            for k in keys:
                out.extend(self._sect_lbl.get(k, []))
            return out

        self._groups = {
            "area": w("rb_rect", "rb_ell", "sl_feather", "btn_extract") + labels("area"),
            "frame": w("btn_tool_frame", "btn_tool_rect"),
            "engine": w("rb_paper", "rb_fast", "rb_ai", "lbl_model", "btn_restore") + labels("engine"),
            "clean": (w("btn_tool_brush", "btn_tool_erase", "btn_clear_mask", "sl_brush",
                        "btn_pip_own", "sw_own", "btn_pip_foreign", "sw_foreign",
                        "btn_for_reset", "btn_pip_bg", "sw_bg", "sl_tol", "lbl_tol",
                        "btn_clean", "btn_preview_mask", "lbl_mask_count")
                      + labels("clean_sect")),
            "insert": w("btn_ctor_side", "btn_insert_png") + labels("insert_sect"),
        }

    def _mode_allow(self, gname):
        return self._mode == "all" or gname in self._mode_groups.get(self._mode, set())

    def _set_mode(self, m):
        if m not in self._mode_groups:
            return
        self._mode = m
        for mk, b in self.mode_btns.items():
            b.setChecked(mk == m)
            b.setProperty("active", mk == m)
            b.style().unpolish(b)
            b.style().polish(b)
        for gname, widgets in self._groups.items():
            on = self._mode_allow(gname)
            for wd in widgets:
                wd.setEnabled(on)
        self._on_frame(self.view.frame_rect())
        self._status("hint_mode_" + m)

    def insert_from_png(self):
        if not self.doc:
            self._status("hint_start")
            return
        path, _ = QFileDialog.getOpenFileName(self, self.t("btn_png"), "",
                                              "PNG (*.png);;Все файлы (*)")
        if not path:
            return
        self._open_placement_png(path)

    def _open_placement_png(self, path):
        try:
            from PIL import Image as PILImage
            from stamp_builder import PlacementDialog
            im = PILImage.open(path).convert("RGBA")
            PlacementDialog(self, im).exec()
        except Exception as e:
            QMessageBox.warning(self, "StampRescue", f"{self.t('err_png')}: {e}")

    def _reset_foreign(self):
        self.foreign_colors = []
        self.foreign_color = None
        self._paint_swatch(self.sw_foreign, None)
        if getattr(self, "_mask_dlg", None) is not None and self._mask_dlg.isVisible():
            self._preview_masks()

    def _paint_swatch(self, lbl, bgr):
        if bgr is None:
            lbl.setStyleSheet("background:#2a3140; border:1px solid #41506a; "
                              "border-radius:3px;")
        else:
            b, g, r = int(bgr[0]), int(bgr[1]), int(bgr[2])
            lbl.setStyleSheet(f"background:#{r:02x}{g:02x}{b:02x}; "
                              f"border:1px solid #888; border-radius:3px;")

    def _set_pip_mode(self, mode):
        self._pip_mode = mode
        self.view.set_pipette_mode(mode is not None)
        self.btn_pip_own.setProperty("active", mode == "own")
        self.btn_pip_foreign.setProperty("active", mode == "foreign")
        self.btn_pip_bg.setProperty("active", mode == "bg")
        self.btn_pip_own.style().unpolish(self.btn_pip_own)
        self.btn_pip_own.style().polish(self.btn_pip_own)
        self.btn_pip_foreign.style().unpolish(self.btn_pip_foreign)
        self.btn_pip_foreign.style().polish(self.btn_pip_foreign)
        self.btn_pip_bg.setProperty("active", self.btn_pip_bg.property("active"))
        self.btn_pip_bg.style().unpolish(self.btn_pip_bg)
        self.btn_pip_bg.style().polish(self.btn_pip_bg)

    def _on_tol(self, v):
        self.tol = v
        self.lbl_tol.setText(str(v))
        # живая маска: двигая «допуск», сразу видно, что попадёт в стирание
        if (self.own_color is not None and self.view.frame_rect() is not None
                and getattr(self, "_mask_dlg", None) is not None
                and self._mask_dlg.isVisible()):
            self._mask_debounce.start()

    def _on_pip_click(self, x, y):
        if not self.doc or self._pip_mode is None:
            return
        img = self.current_image()
        H, W = img.shape[:2]
        xi = min(max(int(round(x)), 0), W - 1)
        yi = min(max(int(round(y)), 0), H - 1)
        # медиана окна 5x5 вместо одного пикселя: шум скана и полутоновые края не врут
        y0, y1 = max(0, yi - 2), min(H, yi + 3)
        x0, x1 = max(0, xi - 2), min(W, xi + 3)
        col = tuple(int(c) for c in
                    np.median(img[y0:y1, x0:x1].reshape(-1, 3), axis=0))
        if self._pip_mode == "own":
            self.own_color = col
            self._paint_swatch(self.sw_own, col)
            self.btn_clean.setEnabled(self._mode_allow("clean")
                                     and self.view.frame_rect() is not None)
        elif self._pip_mode == "bg":
            self.bg_color = col
            self._paint_swatch(self.sw_bg, col)
        else:
            # мульти-пипетка: каждый новый клик добавляет эталон ЧУЖОГО (до 3)
            if not any(tuple(c) == col for c in self.foreign_colors):
                if len(self.foreign_colors) >= 3:
                    self.foreign_colors = [col]   # четвёртый начинает заново
                else:
                    self.foreign_colors.append(col)
            self.foreign_color = col
            self._paint_swatch(self.sw_foreign, col)
        self._set_pip_mode(None)
        if getattr(self, "_mask_dlg", None) is not None and self._mask_dlg.isVisible():
            self._preview_masks()

    def _on_frame(self, rect):
        ok = (rect is not None and isinstance(rect, QRectF)
              and rect.width() > 4 and rect.height() > 4)
        self.btn_restore.setEnabled(ok and self._worker is None and self._mode_allow("engine"))
        self.btn_extract.setEnabled(ok and self._worker is None and self._mode_allow("area"))
        self.btn_clean.setEnabled(ok and self._worker is None
                                  and self.own_color is not None
                                  and self._mode_allow("clean"))
        self.btn_preview_mask.setEnabled(ok and self.own_color is not None
                                         and self._mode_allow("clean"))
        if ok:
            self._set_hint("hint_ready")
        elif self.doc:
            self._set_hint("hint_frame")
    def _preview_masks(self):
        """Рентген: КРАСНЫМ — что сотрётся, ЗЕЛЁНЫМ — своя печать.
        Показывает область рамки, а без рамки — область пометок кисти/«Рамки:
        стереть» (крупно); окно подвижное и немодальное; повторный клик
        по кнопке обновляет картинку."""
        rect = self.view.frame_rect()
        manual = self.view.get_mask()
        have_manual = manual is not None and cv2.countNonZero(manual) > 0
        if not self.doc or self.own_color is None:
            return
        if rect is None and not have_manual:
            return
        img = self.current_image()
        masks = build_clean_masks(img, self._rect_tuple(rect) if rect is not None else None,
                                  self.own_color,
                                  self.foreign_colors, self.tol, self.shape_kind,
                                  region=manual, bg_bgr=self.bg_color)
        own = masks["own"] > 0
        foreign = masks["foreign"] > 0

        overlay = img.copy().astype(np.float32)
        red = np.zeros_like(overlay); red[..., 2] = 255
        green = np.zeros_like(overlay); green[..., 1] = 255
        overlay[foreign] = overlay[foreign] * 0.35 + red[foreign] * 0.65
        only_own = own & ~foreign
        overlay[only_own] = overlay[only_own] * 0.5 + green[only_own] * 0.5
        overlay = np.clip(overlay, 0, 255).astype(np.uint8)

        H, W = overlay.shape[:2]
        if rect is not None:
            x0 = max(0, int(rect.x()) - 40)
            y0 = max(0, int(rect.y()) - 40)
            x1 = min(W, int(rect.x() + rect.width()) + 40)
            y1 = min(H, int(rect.y() + rect.height()) + 40)
        else:
            ys, xs = np.where(manual > 0)
            x0 = max(0, int(xs.min()) - 40)
            y0 = max(0, int(ys.min()) - 40)
            x1 = min(W, int(xs.max()) + 41)
            y1 = min(H, int(ys.max()) + 41)
        crop = overlay[y0:y1, x0:x1]

        ch, cw = crop.shape[:2]
        max_side = 1100
        if max(ch, cw) > max_side:
            k = max_side / float(max(ch, cw))
            crop = cv2.resize(crop, (max(1, int(cw * k)), max(1, int(ch * k))),
                              interpolation=cv2.INTER_AREA)

        from PySide6.QtWidgets import QDialog, QScrollArea
        dlg = getattr(self, "_mask_dlg", None)
        if dlg is None or not dlg.isVisible():
            dlg = QDialog(self)
            dlg.setWindowTitle("Маска очистки  (КРАСНЫЙ = сотрётся, ЗЕЛЁНЫЙ = печать)")
            lay = QVBoxLayout(dlg)
            lay.setContentsMargins(6, 6, 6, 6)
            scroll = QScrollArea(dlg)
            scroll.setWidgetResizable(True)
            inner = QLabel()
            scroll.setWidget(inner)
            lay.addWidget(scroll)
            info = QLabel()
            info.setStyleSheet("color:#9aa5b5; font-size:11px;")
            lay.addWidget(info)
            dlg._inner = inner
            dlg._info = info
            self._mask_dlg = dlg
            dlg.show()

        dlg._inner.setPixmap(bgr_to_pixmap(crop))
        dlg._info.setText(f"foreign px = {int(foreign.sum())}   |   own px = {int(own.sum())}")
        dlg.raise_()
        dlg.activateWindow()


    def _set_tool(self, t):
        self.view.set_tool(t)
        for b, name in ((self.btn_tool_frame, "frame"), (self.btn_tool_rect, "rect"),
                        (self.btn_tool_brush, "brush"), (self.btn_tool_erase, "erase")):
            b.setProperty("active", name == t)
            b.style().unpolish(b)
            b.style().polish(b)

    def _on_brush(self, v):
        self.lbl_brush.setText(str(v))
        self.view.set_brush(v)

    def _clear_mask(self):
        self.view.clear_mask()

    def _on_mask_changed(self, n):
        if hasattr(self, "lbl_mask_count"):
            self.lbl_mask_count.setText(f"помечено: {n} px")
        rect = self.view.frame_rect()
        ok_frame = rect is not None and rect.width() > 4 and rect.height() > 4
        self.btn_clean.setEnabled(((n > 0) or (ok_frame and self.own_color is not None))
                                  and self._mode_allow("clean"))
        # предпросмотр маски активен и без рамки — по пометкам кисти
        self.btn_preview_mask.setEnabled(self.own_color is not None
                                        and ((n > 0) or ok_frame)
                                        and self._mode_allow("clean"))
        if n > 0 and getattr(self, "_mask_dlg", None) is not None \
                and self._mask_dlg.isVisible():
            self._mask_debounce.start()   # живой отклик: рисование обновляет маску

    def clean_stamp(self):
        rect = self.view.frame_rect()
        manual = self.view.get_mask()
        have_manual = manual is not None and cv2.countNonZero(manual) > 0
        if not have_manual and rect is None:
            QMessageBox.warning(self, "StampRescue",
                "Сначала пометьте лишнее («Рамка: стереть»/«Кисть») "
                "или обведите печать рамкой.")
            return
        if self.own_color is None:
            QMessageBox.warning(self, "StampRescue", self.t("clean_need_own"))
            return

        img = self.current_image().copy()
        H, W = img.shape[:2]
        r = self._rect_tuple(rect) if rect else None  # None = рамки нет: в деле
                                                       # только пометки (core ограничит
                                                       # автоклассификацию ими)

        masks = build_clean_masks(img, r, self.own_color, self.foreign_colors,
                                  self.tol, self.shape_kind,
                                  region=manual if have_manual else None,
                                  bg_bgr=self.bg_color)
        foreign_u8 = masks["foreign"]
        if cv2.countNonZero(foreign_u8) == 0:
            QMessageBox.warning(self, "StampRescue", self.t("clean_no_foreign"))
            return

        self.undo_stack.append((self.current_page,
                                self.edited.get(self.current_page)))
        if len(self.undo_stack) > 10:
            self.undo_stack.pop(0)
        self.btn_undo.setEnabled(True)

        # Разделение слоёв: чужое замещается чернилами печати / бумагой.
        result = smart_fill(img, masks["own"], foreign_u8)

        self.edited[self.current_page] = result
        self._reload_page(restore_rect=rect)
        self._status("hint_done")
        self._set_hint("hint_ready")

    def _get_lama_or_cv(self):
        model = find_lama_model()
        if model:
            if self._lama is None:
                self._lama = LamaInpainter(model)
            return self._lama
        return OpenCVEngine()

    def _on_clean_done(self, result):
        page, img, foreign, rect = self._pending_clean
        self._pending_clean = None
        self._worker = None
        dil = cv2.dilate(foreign, np.ones((3, 3), np.uint8), iterations=1)
        dil = cv2.GaussianBlur(dil, (3, 3), 0)
        self.edited[page] = blend_result(img, result, dil)
        self._set_busy(False)
        self._reload_page(restore_rect=rect)
        self._status("hint_done")
        self._set_hint("hint_ready")


    def undo(self):
        if not self.undo_stack:
            return
        page, prev = self.undo_stack.pop()
        if prev is None:
            self.edited.pop(page, None)
        else:
            self.edited[page] = prev
        self.current_page = page
        self.btn_undo.setEnabled(bool(self.undo_stack))
        self._reload_page()
        self._status("hint_undo" if "hint_undo" in LANG[self.lang_code] else "hint_done")

    def _show_original(self):
        if not self.doc:
            return
        orig = self.doc.render_page(self.current_page, self.dpi)
        self.view.set_image(orig, self.view.frame_rect())

    def _show_current(self):
        if self.doc:
            self._reload_page(restore_rect=self.view.frame_rect())

    def save_png_page(self):
        if not self.doc:
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "StampRescue", "page.png", "PNG (*.png)")
        if path:
            save_png(self.current_image(), path)
            self.lbl_status.setText(self.t("saved") + path)

    def save_pdf_doc(self):
        if not self.doc:
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "StampRescue", "result.pdf", "PDF (*.pdf)")
        if not path:
            return
        try:
            if self.doc.kind == "image":
                save_pdf(None, {0: self.current_image()}, path, self.dpi)
            else:
                save_pdf(self.doc.path, self.edited, path, self.dpi)
            self.lbl_status.setText(self.t("saved") + path)
        except Exception as e:
            QMessageBox.critical(self, "StampRescue", f"{self.t('err_proc')}:\n{e}")

    # ================= настройки =================
    def _on_shape(self):
        self.shape_kind = "ellipse" if self.rb_ell.isChecked() else "rect"
        self.view.set_frame_kind(self.shape_kind)

    def _on_feather(self, v):
        self.feather = v
        self.lbl_feather.setText(f"{v} px")

    def _on_dpi(self, index):
        new = int(self.dpi_choice.itemText(index).split()[0])
        if self.doc and self.doc.kind == "pdf" and self.edited:
            k = new / self.dpi
            for key, img in list(self.edited.items()):
                h, w = img.shape[:2]
                self.edited[key] = cv2.resize(img, (max(1, int(w * k)), max(1, int(h * k))),
                                              interpolation=cv2.INTER_LANCZOS4)
        self.dpi = new
        if self.doc:
            self._reload_page(restore_rect=self.view.frame_rect())

    def _on_lang(self, index):
        self.lang_code = self.lang_choice.itemText(index)
        self.retranslate()

    def _refresh_model_label(self):
        if find_lama_model():
            self.lbl_model.setText(self.t("model_ok"))
            self.lbl_model.setStyleSheet("color:#4ade80; font-size:11px;")
        else:
            self.lbl_model.setText(self.t("model_no"))
            self.lbl_model.setStyleSheet("color:#f87171; font-size:11px;")

    def retranslate(self):
        for w, key in self._tr.items():
            w.setText(self.t(key))
        for w, key in getattr(self, "_tr_tip", {}).items():
            w.setToolTip(self.t(key))
        self._refresh_model_label()
        self._set_hint(getattr(self, "_hint_key", "hint_start"))
        self._status(getattr(self, "_hint_key", "hint_start"))