# tools/test_clean.py — регрессия классификатора свой/чужое (цвет пипетки)
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import cv2
import numpy as np

from core.clean import build_clean_masks, smart_fill

OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "result", "tests")
os.makedirs(OUT, exist_ok=True)

BLUE = (160, 90, 50)     # BGR (настоящий синий: B=160)
BLACK = (35, 35, 35)
RED = (40, 40, 180)
RECT = (140, 90, 560, 410)


def make_scan(stamp_col, sign_cols):
    H, W = 500, 700
    rng = np.random.default_rng(7)
    img = np.full((H, W, 3), 232, np.uint8)
    img = np.clip(img.astype(np.int16) + rng.integers(-3, 4, (H, W, 3)), 0, 255).astype(np.uint8)
    cv2.ellipse(img, (350, 250), (170, 120), 0, 0, 360, stamp_col, 6)
    cv2.putText(img, "STAMP", (265, 265), cv2.FONT_HERSHEY_SIMPLEX, 1.6, stamp_col, 5)
    pts = np.array([[160 + 34 * t, 250 + int(55 * np.sin(t * 1.1))] for t in range(12)], np.int32)
    cv2.polylines(img, [pts], False, sign_cols[0], 4)
    if len(sign_cols) > 1:
        cv2.rectangle(img, (430, 300), (510, 360), sign_cols[1], 3)
    return img


def near(img, col, rad=45):
    return (np.abs(img.astype(np.int16) - np.array(col, np.int16)).sum(axis=2) < rad)


def frac(mask_a, mask_b):
    """доля пикселей mask_b, попавших в mask_a"""
    return (mask_a & mask_b).sum() / max(1, mask_b.sum())


def check(name, cond):
    print(f"  {'OK ' if cond else 'FAIL'} {name}")
    if not cond:
        raise SystemExit(f"FAILED: {name}")


# 1. синяя печать + чёрная подпись: пипетка взяла синий
img = make_scan(BLUE, [BLACK])
m = build_clean_masks(img, RECT, own_bgr=BLUE, foreign_bgr=None, tol=35)
own, foreign = m["own"] > 0, m["foreign"] > 0
check("own blue>=0.8", frac(own, near(img, BLUE)) >= 0.8)
check("foreign black>=0.7", frac(foreign, near(img, BLACK)) >= 0.7)
check("blue not foreign<=0.10", frac(foreign, near(img, BLUE)) <= 0.10)

# 2. КРАСНАЯ печать + синие метки: пипетка взяла красный (старая «синева» тут врала)
img2 = make_scan(RED, [BLUE, BLACK])
m2 = build_clean_masks(img2, RECT, own_bgr=RED, tol=35)
own2, foreign2 = m2["own"] > 0, m2["foreign"] > 0
check("own red>=0.8", frac(own2, near(img2, RED)) >= 0.8)
check("blue marks foreign>=0.7", frac(foreign2, near(img2, BLUE)) >= 0.7)
check("red not foreign<=0.10", frac(foreign2, near(img2, RED)) <= 0.10)

# 3. ахроматная (чёрная) печать + синяя подпись
img3 = make_scan(BLACK, [BLUE])
m3 = build_clean_masks(img3, RECT, own_bgr=BLACK, tol=35)
own3, foreign3 = m3["own"] > 0, m3["foreign"] > 0
check("own black>=0.8", frac(own3, near(img3, BLACK)) >= 0.8)
check("blue foreign>=0.7", frac(foreign3, near(img3, BLUE)) >= 0.7)

# 4. кисть = приказ: регион поверх СВОЕЙ печати тоже станет чужим
region = np.zeros(img.shape[:2], np.uint8)
region[300:340, 300:400] = 255  # кусок синего эллипса/текста
m4 = build_clean_masks(img, RECT, own_bgr=BLUE, tol=35, region=region)
check("region forces foreign",
      ((m4["foreign"] > 0) & (region > 0)).sum() == (region > 0).sum())

# 5. легаси-режим без пипетки (own_bgr=None) работает как раньше
m5 = build_clean_masks(img, RECT, own_bgr=None, tol=35)
check("legacy blueness", frac(m5["own"] > 0, near(img, BLUE)) >= 0.8)

# 6. smart_fill: чужое стёрто, своё цело
filled = smart_fill(img, m["own"], m["foreign"])
before_black = near(img, BLACK).sum()
after_black = (near(filled, BLACK) & (filled.astype(np.int16).sum(axis=2) < 400)).sum()
check("signature removed", after_black <= 0.15 * before_black)
check("stamp kept", near(filled, BLUE).sum() >= 0.8 * near(img, BLUE).sum())

# визуальные артефакты
cv2.imwrite(os.path.join(OUT, "31_clean_before.png"), img)
vis = img.copy()
vis[m["foreign"] > 0] = (40, 40, 220)    # красным — чужое
vis[m["own"] > 0] = (60, 180, 60)        # зелёным — своё
cv2.imwrite(os.path.join(OUT, "31_clean_masks.png"), vis)
cv2.imwrite(os.path.join(OUT, "31_clean_after.png"), filled)
print("PASS test_clean")
