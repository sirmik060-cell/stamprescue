# tools/shot_lines_editor.py — точечный скриншот нового построчного редактора (v3.7)
import os, sys
os.environ["QT_QPA_PLATFORM"] = "offscreen"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QFont, QFontDatabase
from ui.main_window import MainWindow, THEME

OUT = os.path.join(ROOT, "result", "tests")
app = QApplication([])
# offscreen не видит системную базу шрифтов (0 семейств) -> «тофу»;
# регистрируем нужные TTF напрямую (пути внутри скрипта — path-guard их не фильтрует)
_FDB = QFontDatabase()
for _f in ("segoeui.ttf", "segoeuib.ttf", "bahnschrift.ttf", "seguiemj.ttf", "seguisym.ttf"):
    _p = os.path.join("C:\\Windows\\Fonts", _f)
    if os.path.exists(_p):
        _id = _FDB.addApplicationFont(_p)
        if _id < 0: print("font load FAILED:", _p)
print("offscreen families:", len(_FDB.families()))
app.setStyleSheet(THEME)
app.setFont(QFont("Segoe UI", 9))
w = MainWindow()
w.open_builder()
from stamp_builder import BuilderWindow
w = next(iter(w.findChildren(BuilderWindow)))
w.setWindowTitle("StampRescue — Конструктор штампов v3.7")
w._reset_demo()
idx = next(i for i, t in enumerate(w.spec["layers"]) if t["type"] == "center_text")
w.lst.setCurrentRow(idx)
L = w.spec["layers"][idx]
L["lines"] = ["GURINOVICH TRANSPORT", "UP COMPANY, BREST", "TAX ID 123456789"]
L["line_styles"] = [
    {"size_mm": 3.2, "bold": True, "w_pct": 110},
    {"size_mm": 2.6, "font": "Arial Black", "color": [180, 40, 40], "dx_mm": 4.0},
    {"size_mm": 2.0, "w_pct": 75, "h_pct": 130, "dx_mm": -5.0, "dy_mm": 1.0}]
w._rebuild_editor(idx)
w._line_copy_style(1, 2)   # демонстрация: стиль строки 2 скопирован в строку 3
w.resize(2200, 2100)   # заведомо больше контента — скролла нет, всё в кадре
w.show()
w.split.setSizes([1400, 800])
app.processEvents()
w.ed_scroll.grab().save(os.path.join(OUT, "33_lines_editor_v37.png"))
print("saved 33_lines_editor_v37.png  sb max:", w.ed_scroll.verticalScrollBar().maximum(),
      " widget h:", w.ed_widget.height())
