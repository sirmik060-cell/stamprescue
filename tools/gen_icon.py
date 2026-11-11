# tools/gen_icon.py — иконка приложения из логотипа заставки (красная печать SR)
import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE)

from PySide6.QtWidgets import QApplication  # noqa: E402

app = QApplication([])
from ui.splash import _make_stamp_layer  # noqa: E402

os.makedirs(os.path.join(BASE, "assets"), exist_ok=True)
png = os.path.join(BASE, "assets", "app.png")
ico = os.path.join(BASE, "assets", "app.ico")
pm = _make_stamp_layer(512)
if not pm.toImage().save(png):
    raise SystemExit("png save failed")
from PIL import Image  # noqa: E402

im = Image.open(png).convert("RGBA")
im = im.resize((256, 256), Image.LANCZOS)
im.save(ico, sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
print("OK", ico)
