# diag_times2.py — C в Times New Roman: dpi 300 vs 150, noise 0 vs 15
import os
import numpy as np
from PIL import Image, ImageDraw
import stamp_builder as sb

def render_C(font, size_mm, dpi, noise, path):
    spec = {"form": "rect", "width_mm": 40, "height_mm": 30, "dpi": dpi,
            "rotation_deg": 0, "noise": noise, "corner_mm": 0, "noise_pct": noise,
            "layers": [
                {"type": "band", "inset_mm": 1.0, "thickness_mm": 0.5, "color": (35, 60, 170)},
                {"type": "center_text", "text": ["C"], "size_mm": size_mm,
                 "font": font, "bold": False, "align": "center", "dx_mm": 0, "dy_mm": 0,
                 "spacing_mm": 1.0, "color": (35, 60, 170)},
            ]}
    img = sb.render_stamp(spec)
    big = img.resize((img.width * 3, img.height * 3), Image.LANCZOS)
    big.save(path)

render_C("Times New Roman", 6.4, 300, 0, "result/tests/diag_C_dpi300_n0.png")
render_C("Times New Roman", 6.4, 300, 15, "result/tests/diag_C_dpi300_n15.png")
render_C("Times New Roman", 6.4, 150, 0, "result/tests/diag_C_dpi150_n0.png")
print("saved 3 diag_C renders")
