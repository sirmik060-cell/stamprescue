# tools/test_gui.py — смоук-тест GUI без экрана: окно + конструктор, скриншоты
import os
os.environ["QT_QPA_PLATFORM"] = "offscreen"
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
OUT = os.path.join(ROOT, "result", "tests")
os.makedirs(OUT, exist_ok=True)

from PySide6.QtWidgets import QApplication  # noqa: E402

app = QApplication([])
from ui.main_window import MainWindow, THEME  # noqa: E402
app.setStyleSheet(THEME)

w = MainWindow()
w.resize(1250, 800)
w.show()
app.processEvents()
w.grab().save(os.path.join(OUT, "10_main_window.png"))
print("main window OK")

# открыть конструктор из главного окна
w.open_builder()
app.processEvents()
from stamp_builder import BuilderWindow  # noqa: E402

bwin = None
for c in w.findChildren(BuilderWindow):
    bwin = c
if bwin is None:
    bwin = BuilderWindow(w)
    bwin.show()
bwin.resize(1250, 800)
bwin.show()
app.processEvents()
bwin.grab().save(os.path.join(OUT, "11_builder.png"))
print("builder OK; layers:", len(bwin.spec["layers"]))
from PySide6.QtWidgets import QPushButton as _PB, QComboBox as _CB
_bt = [x.text() for x in bwin.findChildren(_PB)]
assert "🔤 Шрифт из Скана" in _bt, [t for t in _bt if "скана" in t.lower()]
print("rename 'Шрифт из Скана' OK")

# демо-кнопка
bwin._reset_demo()
app.processEvents()
bwin.grab().save(os.path.join(OUT, "12_builder_demo.png"))
print("demo reset OK")

# построчный редактор центрального блока
idx = next(i for i, L in enumerate(bwin.spec["layers"]) if L["type"] == "center_text")
bwin.lst.setCurrentRow(idx)
app.processEvents()
bwin._line_add()
app.processEvents()
bwin._line_set(0, size=5.0, color=(200, 0, 0), bold=True)
bwin._line_set(1, size=2.0, font="Arial Black")
bwin._line_set(0, w=130, h=90, dx=4.0, dy=-1.5)
bwin._line_set(1, dx=-3.0, dy=1.0, h=140)
print("line dx/dy/w/h fields OK")
# построчное удаление
_n_before = len(bwin.spec["layers"][idx]["lines"])
bwin._line_del_at(1)
assert len(bwin.spec["layers"][idx]["lines"]) == _n_before - 1, "🗑 строки не работает"
bwin._line_add()
print("per-line delete OK")
# копирование стиля строки
bwin._line_copy_style(0, 1)
_ls2 = bwin.spec["layers"][idx]["line_styles"]
for _k in ("w_pct", "h_pct", "dx_mm", "dy_mm"):
    assert _ls2[1].get(_k) == _ls2[0].get(_k), f"copy style failed for {_k}"
print("copy line style OK")
app.processEvents()
bwin.grab().save(os.path.join(OUT, "14_lines_editor.png"))
_cbs = bwin.ed_widget.findChildren(_CB)
assert any(c.itemText(0) == "Шрифт" and "Times New Roman" in [c.itemText(m) for m in range(c.count())] for c in _cbs), "нет комбобокса 'Шрифт'"
assert any(c.itemText(0) == "Жирность" and c.count() == 3 for c in _cbs), "нет комбобокса 'Жирность'"
print("line combos renamed OK")
print("lines editor OK")

# сплиттер панели: нет горизонтальной подрезки редактора + перетаскивание делит
hbar = bwin.ed_scroll.horizontalScrollBar()
print("editor h-scroll max (must be 0):", hbar.maximum())
assert hbar.maximum() == 0, "параметры обрезаются по горизонтали"
bwin.split.setSizes([860, 380])
app.processEvents()
bwin.grab().save(os.path.join(OUT, "15_splitter_wide.png"))
lw = bwin.split.sizes()[0]
print("splitter dragged, left width:", lw)
assert lw > 700, "сплиттер не двигается"
bwin.split.setSizes([640, 600])
app.processEvents()

# загрузка примера jenti
import json  # noqa: E402
bwin.spec = json.load(open(os.path.join(ROOT, "presets", "jenti_example.json"), encoding="utf-8"))
bwin._refresh_list()
bwin._render()
app.processEvents()
print("jenti preset load OK")

# сохранение PNG из конструктора напрямую
from stamp_builder import render_stamp  # noqa: E402
render_stamp(bwin.spec).save(os.path.join(OUT, "13_jenti_stamp.png"))

# чекбоксы: стиль индикатора задан в теме (рамка видна на тёмном фоне)
assert "QCheckBox::indicator" in app.styleSheet(), "нет стиля чекбоксов в теме"
aidx = next(i for i, L in enumerate(bwin.spec["layers"]) if L["type"] == "arc_text")
bwin.lst.setCurrentRow(aidx)
app.processEvents()
bwin.grab().save(os.path.join(OUT, "26_checkboxes.png"))
print("checkbox style OK; arc editor screenshot saved")

# pic_frame: расширенный набор глифов в комбобоксе
bwin.spec["layers"].append({"type": "pic_frame", "glyph": "ring", "count": 30,
                            "inset_mm": 1.0, "size_mm": 1.5, "color": (35, 60, 170)})
bwin._refresh_list()
bwin.lst.setCurrentRow(len(bwin.spec["layers"]) - 1)
app.processEvents()
combos = [c for c in bwin.ed_widget.findChildren(__import__("PySide6.QtWidgets", fromlist=["QComboBox"]).QComboBox) if c.count() >= 9]
assert combos and "кольцо" in combos[0].itemText(5), "нет новых глифов в комбобоксе"
bwin.grab().save(os.path.join(OUT, "27_glyph_combo.png"))
print("pic_frame glyph combo OK, items:", combos[0].count())

# FontMatchDialog: визуальные кандидаты на синтетическом «скане»
import numpy as np  # noqa: E402
from PIL import Image, ImageDraw  # noqa: E402
from PySide6.QtCore import QRect  # noqa: E402
from font_matcher import FontMatchDialog  # noqa: E402
im = Image.new("RGB", (220, 220), (240, 240, 240))
d = ImageDraw.Draw(im)
from font_matcher import get_font  # noqa: E402
d.text((110, 110), "Б", font=get_font("Times New Roman", 150), fill=(20, 20, 20), anchor="mm")
page = np.array(im)[:, :, ::-1].copy()  # BGR
applied = []
dlg = FontMatchDialog(page, lambda fam, bold: applied.append((fam, bold)))
dlg.show()
app.processEvents()
dlg._set_rect(QRect(20, 10, 180, 200))
dlg.ed_char.setText("Б")
dlg._compare()
app.processEvents()
assert dlg.lst.count() > 0, "FontMatchDialog: пустой список кандидатов"
top = dlg.results[0]
print("font-match top candidate:", top)
dlg.grab().save(os.path.join(OUT, "28_fontmatch.png"))
dlg.lst.setCurrentRow(0)
dlg._apply()
assert applied and applied[0][0] == top[0], "применение не вернуло выбранный шрифт"
print("font-match visual list OK; applied:", applied[0])
dlg.deleteLater()
bwin.spec["layers"].pop()
bwin._refresh_list()

# ------ PlacementDialog: окно не должно раздуваться от X/Y/масштаба ------
import numpy as np
from PIL import Image as _PILImage
from stamp_builder import PlacementDialog
from PySide6.QtWidgets import QWidget as _QW
class _FakeMW(_QW):
    current_page = 0; edited = {}; undo_stack = []
    class btn_undo:
        @staticmethod
        def setEnabled(x): pass
    def _reload_page(self): pass
    def current_image(self):
        return np.full((1754, 1240, 3), 235, dtype=np.uint8)  # «скан» CMR portrait
_pd = PlacementDialog(_FakeMW(), _PILImage.new("RGBA", (600, 600), (200, 30, 30, 255)))
_pd.show(); app.processEvents()
_h0 = _pd.height()
for _i in range(8):
    _pd.s_sc.setValue(50 + _i * 15); _pd.s_x.setValue(300 + _i * 60); _pd.s_y.setValue(400 + _i * 100)
    app.processEvents()
assert _pd.height() == _h0 and _pd.width() == 1100, "PlacementDialog раздувается: %dx%d -> %dx%d" % (1100, _h0, _pd.width(), _pd.height())

# превью честно показывает размер штампа: footprint(превью)/footprint(применённый) == k_prev^2
_pd.s_x.setValue(620); _pd.s_y.setValue(877); _pd.s_sc.setValue(100); _pd.s_rt.setValue(0)
app.processEvents()
def _red_px(img):
    return int(((img[..., 2] > 150) & (img[..., 1] < 100) & (img[..., 0] < 100)).sum())
_prev_arr = _pd._composite(1200)
_full_arr = _pd._composite()
k_prev = 1200 / 1754.0
r_prev, r_full = _red_px(_prev_arr), _red_px(_full_arr)
exp = r_full * k_prev * k_prev
assert abs(r_prev - exp) / exp < 0.06, "превью врёт о размере: prev=%d full=%d exp=%.0f" % (r_prev, r_full, exp)
print("placement preview scale-honest OK (prev=%d full=%d k2=%.3f)" % (r_prev, r_full, r_prev / r_full))
_pd.grab().save(os.path.join(OUT, "34_placement_fixed.png"))
_pd.close()
print("placement dialog size-stable OK")

# ---------- v3.8: режимы задач (активируются только инструменты задачи) ----------
assert set(w.mode_btns) == {"fon", "pechat", "ins", "all"}
w._set_mode("fon")
assert w.rb_ai.isEnabled() and w.btn_tool_frame.isEnabled()
assert not w.btn_pip_own.isEnabled() and not w.btn_clean.isEnabled() \
    and not w.btn_insert_png.isEnabled()
w._set_mode("pechat")
assert w.btn_pip_own.isEnabled() and w.btn_pip_bg.isEnabled() and w.btn_tool_brush.isEnabled()
assert not w.rb_paper.isEnabled() and not w.btn_restore.isEnabled()
w._set_mode("ins")
assert w.btn_insert_png.isEnabled() and w.btn_ctor_side.isEnabled()
assert not w.rb_rect.isEnabled() and not w.btn_tool_brush.isEnabled()
w._set_mode("all")
assert w.rb_paper.isEnabled() and w.btn_pip_bg.isEnabled() \
    and w.btn_insert_png.isEnabled() and w.rb_rect.isEnabled()
print("task modes OK")

# v3.8.2: в низком окне панель скроллится, а НЕ сжимает кнопки (баг полноэкранного
# режима у пользователя: текст кнопок обрезан, «кнопок не видно»)
from PySide6.QtWidgets import QScrollArea as _QSA  # noqa: E402
_scr = w.findChild(_QSA, "side_scroll")
assert _scr is not None and _scr.widget() is not None, "у сайдбара нет скролла"
w.resize(1250, 620)
app.processEvents()
for _b in (w.btn_restore, w.btn_extract, w.btn_clean, w.btn_insert_png):
    _mh = _b.minimumSizeHint().height()
    assert _b.height() >= max(28, _mh), \
        f"кнопка сжата в низком окне: {_b.objectName()} h={_b.height()} < {_mh}"
w.resize(1250, 800)
app.processEvents()
print("sidebar scrollable in short window OK")

# пипетка ФОНА + мульти-ЧУЖОЕ: состояние UI и проброс в core
import cv2  # noqa: E402
from core.clean import build_clean_masks as _bcm  # noqa: E402
w.foreign_colors = [(20, 30, 160), (180, 40, 40)]
w.bg_color = (120, 120, 130)
_img = np.full((120, 120, 3), (120, 120, 130), np.uint8)  # «синяя бумага» CMR
_m = _bcm(_img, (0, 0, 120, 120), (40, 30, 170), w.foreign_colors, 35, "rect",
          bg_bgr=w.bg_color)
assert cv2.countNonZero(_m["foreign"]) == 0, "фон не исключился из чужого"
w._reset_foreign()
assert w.foreign_colors == [] and w.foreign_color is None
print("bg-pipette + multi-foreign OK")

# вставка ранее вырезанного PNG через диалог размещения
import PIL.Image as _PIL  # noqa: E402
from stamp_builder import PlacementDialog as _PDlg2  # noqa: E402
_png = os.path.join(OUT, "_insert_probe.png")
_PIL.new("RGBA", (140, 140), (200, 40, 40, 255)).save(_png)
w.doc = True
w.current_image = lambda: np.full((900, 700, 3), 235, np.uint8)

# v3.8.5: предпросмотр маски работает БЕЗ рамки — по пометкам кисти
# (баг пользователя: «при выделении кистью превью маски неактивно»)
_mask_stub = np.zeros((900, 700), np.uint8)
_mask_stub[150:220, 150:320] = 255
w.view.get_mask = lambda: _mask_stub.copy()
w._set_mode("pechat")
w.own_color = (150, 60, 110)
w.foreign_colors = []
w._on_mask_changed(500)   # эмуляция сигнала mask_changed от кисти
assert w.btn_preview_mask.isEnabled(), "кнопка предпросмотра не активна для кисти"
w._preview_masks()
app.processEvents()
assert getattr(w, "_mask_dlg", None) is not None and w._mask_dlg.isVisible(),     "предпросмотр не открылся по кисти"
w._mask_dlg.close()
w._set_mode("all")
print("brush mask preview (no frame) OK")
_x = _PDlg2.exec
_PDlg2.exec = lambda self: None
w._open_placement_png(_png)
_PDlg2.exec = _x
os.remove(_png)
print("insert-from-png OK")


# --- v3.8.6: цикл «💾 Пресет / 📂 Пресет» реально сохраняет и вызывает пресет ---
import json as _json41, os as _os41
import stamp_builder as _sb41
_tmp41 = _os41.path.join(OUT, "_preset_roundtrip.json")
_pre41 = _sb41.QFileDialog.getSaveFileName
_after = bwin.spec  # текущий (после демо)
_sb41.QFileDialog.getSaveFileName = staticmethod(lambda *a, **k: (_tmp41, "JSON (*.json)"))
bwin._save_preset()
_sb41.QFileDialog.getSaveFileName = staticmethod(lambda *a, **k: ("", ""))
with open(_tmp41, encoding="utf-8") as _f41:
    _saved41 = _json41.load(_f41)
assert _saved41 == _after, "сохранённый пресет != то, что было в окне"
bwin._reset_demo()
assert bwin.spec != _saved41, "демо-сброс не изменил spec — тест ничего не проверяет"
_sb41.QFileDialog.getOpenFileName = staticmethod(lambda *a, **k: (_tmp41, "JSON (*.json)"))
bwin._load_preset()
assert bwin.spec == _saved41, "загрузка пресета не восстановила spec"
bwin.grab().save(os.path.join(OUT, "13_preset_loaded.png"))
# и загрузка типового пресета из presets/ (путь пользователя через 📂 Пресет)
_typ41 = os.path.join(os.path.dirname(os.path.dirname(OUT)), "presets", "ooo_38_main.json")
_sb41.QFileDialog.getOpenFileName = staticmethod(lambda *a, **k: (_typ41, "JSON (*.json)"))
bwin._load_preset()
assert bwin.spec["width_mm"] == 38 and bwin.spec["form"] == "circle", "типовой пресет не загрузился"
bwin.grab().save(os.path.join(OUT, "14_preset_ooo38.png"))
_sb41.QFileDialog.getSaveFileName = _pre41
os.remove(_tmp41)
print("preset save/load cycle OK")

# --- релиз v0.5: заставка — таймлайн, заголовок, автозакрытие, скип ---
import time as _t42
from ui.splash import Splash as _S42
_s42 = _S42(duration_ms=5000)
_s42.start()
_s42.set_t_for_test(2000)
app.processEvents()
_s42.grab().save(os.path.join(OUT, "42_splash_stamp.png"))
_s42.set_t_for_test(3900)
app.processEvents()
_s42.grab().save(os.path.join(OUT, "42_splash_title.png"))
# заголовок реально нарисован: яркие пиксели в нижней полосе
_img42 = _s42.grab().toImage()
_strip42 = _img42.copy(0, int(_img42.height() * 0.73), _img42.width(), 90)
_bright42 = 0
for _y42 in range(0, _strip42.height(), 2):
    for _x42 in range(0, _strip42.width(), 2):
        if _strip42.pixelColor(_x42, _y42).lightness() > 170:
            _bright42 += 1
assert _bright42 > 300, f"заголовок заставки не отрисован ({_bright42} px)"
# печать на промежуточном кадре тоже есть: красные пиксели в центре
_red42 = 0
_img42b = _s42.grab().toImage()
for _y42 in range(0, _img42b.height(), 3):
    for _x42 in range(int(_img42b.width() * 0.32), int(_img42b.width() * 0.68), 3):
        _c42 = _img42b.pixelColor(_x42, _y42)
        if _c42.red() > 140 and _c42.red() > _c42.green() + 50:
            _red42 += 1
assert _red42 > 200, f"печать-логотип не отрисована ({_red42} px)"
_s42._begin_close()
# автозаключение короткого сплэша
_s42b = _S42(duration_ms=250)
_s42b.start()
_dl42 = _t42.time() + 3
while _t42.time() < _dl42 and not _s42b._closed_by_timer:
    app.processEvents()
    _t42.sleep(0.02)
assert _s42b._closed_by_timer, "заставка не авто-закрылась"
assert _s42._closing, "скип не закрывает заставку"
print("splash timeline + title + autoclose OK")

print("GUI SMOKE PASSED")
