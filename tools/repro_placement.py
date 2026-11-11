# tools/repro_placement.py — воспроизведение роста окна PlacementDialog
import os, sys
os.environ["QT_QPA_PLATFORM"] = "offscreen"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import numpy as np
from PySide6.QtWidgets import QApplication, QWidget
from ui.main_window import THEME
from stamp_builder import PlacementDialog

app = QApplication([])
app.setStyleSheet(THEME)

class FakeMW(QWidget):
    current_page = 0
    edited = {}
    undo_stack = []
    class btn_undo:
        @staticmethod
        def setEnabled(x): pass
    def _reload_page(self): pass
    def current_image(self):
        # «скан» CMR: портрет A4 @150dpi ~ 1240x1754
        return np.full((1754, 1240, 3), 235, dtype=np.uint8)

from PIL import Image
stamp = Image.new("RGBA", (600, 600), (200, 30, 30, 255))

dlg = PlacementDialog(FakeMW(), stamp)
dlg.show()
app.processEvents()
print("shown size:", dlg.width(), dlg.height())
for i in range(6):
    dlg.s_sc.setValue(50 + i * 10)   # масштаб
    dlg.s_x.setValue(300 + i * 50)   # X
    dlg.s_y.setValue(400 + i * 100)  # Y
    app.processEvents()
    print("after change %d: %dx%d  prev %dx%d" % (i, dlg.width(), dlg.height(),
          dlg.prev.width(), dlg.prev.height()))
