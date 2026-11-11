# tools/probe_lama.py — живая проверка фикса «белого поля» LaMa (модель ONNX 512 fixed)
# Синтетический «CMR»: синяя бумага + тёмно-синие строки текста + НАСТОЯЩАЯ
# красно-пурпурная печать (как фиолетовые чернила на синей бумаге).
# Метрики в зоне маски: доля белых пикселей, краснота (R-B), доля похожей на бумагу.
import os
import sys
import time

import cv2
import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from core.inpaint import LamaInpainter, find_lama_model  # noqa: E402

H, W = 3000, 2400
PAPER = np.array((205, 165, 105), np.uint8)  # BGR «синяя бумага» CMR
rng = np.random.default_rng(1)
base = np.empty((H, W, 3), np.uint8)
base[:] = PAPER
n = rng.normal(0, 5, (H, W, 1))
base = np.clip(base.astype(np.int16) + n.astype(np.int16), 0, 255).astype(np.uint8)
for y in range(100, H - 100, 90):  # «текст документа» тёмно-синий, рваные строки
    x0 = int(rng.integers(120, W - 700))
    base[y:y + 10, x0:W - 120:2] = (95, 80, 60)

# «печать» — чернильный цвет (BGR): тёмный пурпурно-красный, как реальный штамп на синей бумаге
INK = np.array((70, 35, 195), np.uint8)
yy, xx = np.ogrid[:H, :W]
cx, cy, rx, ry = 1200, 1500, 300, 240
ell = ((xx - cx) / rx) ** 2 + ((yy - cy) / ry) ** 2
ring = (ell > 0.72) & (ell < 1.0)
ring2 = (ell > 0.55) & (ell < 0.60)
bar = (np.abs(yy - cy) < 16) & (ell < 0.9)
arc = (np.abs(((xx - cx) / rx) * 0.5 + (yy - cy - 80) / ry) < 0.05) & (ell < 0.95)
ink = ring | ring2 | bar | arc
img = base.copy()
img[ink] = INK

mask = cv2.dilate(ink.astype(np.uint8) * 255, np.ones((5, 5), np.uint8))
mbool = mask > 0


def stats(a, tag):
    a = a.astype(np.float64)
    red = float((a[..., 2] - (a[..., 0] + a[..., 1]) / 2.0).mean())  # R против B,G
    white = float(((a > 235).all(axis=-1)).mean())
    paper = float((np.abs(a - PAPER.astype(np.float64)).mean(axis=-1) < 45).mean())
    print("%-14s red=%+7.1f  white_frac=%.3f  paper_like_frac=%.3f" % (tag, red, white, paper))
    return red, white, paper


model = find_lama_model()
print("model:", model)
t = time.time()
lam = LamaInpainter(model)
print("load %.1fs" % (time.time() - t))
t = time.time()
out = lam(img, mask)
print("inpaint %.1fs" % (time.time() - t))

r_in, _, p_in = stats(img[mbool], "вход(с печатью)")
r_out, w_out, p_out = stats(out[mbool], "выход LaMa")

crop = (slice(cy - 380, cy + 380), slice(cx - 460, cx + 460))
cv2.imwrite(os.path.join(ROOT, "result", "tests", "36_lama_input.png"), img[crop])
cv2.imwrite(os.path.join(ROOT, "result", "tests", "36_lama_new.png"), out[crop])
cv2.imwrite(os.path.join(ROOT, "result", "tests", "36_lama_truth.png"), base[crop])

assert w_out < 0.05, f"осталось белое поле: white_frac={w_out:.3f}"
assert r_out < r_in * 0.3, f"краснота не убрана: {r_out:.1f} vs {r_in:.1f}"
assert p_out > p_in + 0.3, f"заполнение непохоже на бумагу: {p_in:.3f} -> {p_out:.3f}"
print("PROBE OK: белое поле убрано, краснота %.0f→%.0f, paper_like %.2f→%.2f"
      % (r_in, r_out, p_in, p_out))
