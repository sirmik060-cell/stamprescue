# tools/shot_main_modes.py — скриншоты боковой панели в каждом режиме задач
import os
os.environ["QT_QPA_PLATFORM"] = "offscreen"
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
OUT = os.path.join(ROOT, "result", "tests")
os.makedirs(OUT, exist_ok=True)

from PySide6.QtWidgets import QApplication, QFrame, QScrollArea  # noqa: E402
from PySide6.QtGui import QFontDatabase  # noqa: E402

app = QApplication([])
_FDB = QFontDatabase()
for _f in ("segoeui.ttf", "segoeuib.ttf", "seguiemj.ttf", "seguisym.ttf"):
    _p = os.path.join("C:\\Windows\\Fonts", _f)
    if os.path.exists(_p):
        _FDB.addApplicationFont(_p)
print("families:", len(_FDB.families()))

from ui.main_window import MainWindow, THEME  # noqa: E402

app.setStyleSheet(THEME)
w = MainWindow()
w.resize(1250, 1500)
w.show()
app.processEvents()

side = w.findChild(QFrame, "sidebar")
assert side is not None, "sidebar не найден"
_scr = w.findChild(QScrollArea, "side_scroll")
body = _scr.widget()  # полный контент панели (grab рендерит и скрытую скроллом часть)
for mode, tag in [("fon", "fon"), ("pechat", "clean"), ("ins", "insert"), ("all", "all")]:
    w._set_mode(mode)
    app.processEvents()
    body.grab().save(os.path.join(OUT, f"35_mode_{tag}.png"))
    print("saved", f"35_mode_{tag}.png", body.size())

# v3.8.2: низкое окно — панель скроллится, кнопки НЕ сжимаются
w._set_mode("all")
w.resize(1250, 620)
app.processEvents()
side.grab().save(os.path.join(OUT, "37_sidebar_short.png"))
_h = w.btn_restore.height()
print("saved 37_sidebar_short.png  short-window btn_restore h:", _h)
assert _h >= 28, f"кнопка сжата в низком окне: {_h}"
