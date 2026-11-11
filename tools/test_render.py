# tools/test_render.py — оффскрин-тесты конструктора: все формы и слои
import copy
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from stamp_builder import default_spec, render_stamp  # noqa: E402

OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "result", "tests")
os.makedirs(OUT, exist_ok=True)


def save(spec, name):
    img = render_stamp(spec)
    p = os.path.join(OUT, name)
    img.save(p)
    print("OK", name, img.size)


base = default_spec()
save(base, "01_default_ellipse.png")

rect = copy.deepcopy(base)
rect["form"] = "rect"
rect["width_mm"] = 50
rect["height_mm"] = 35
rect["layers"][0]["type"] = "ring"
for L in rect["layers"]:
    if L["type"] == "band":
        L.update({"inset_out_mm": 0, "inset_in_mm": 3})
    if L["type"] == "arc_text":
        L["attract"] = "rect"
        L["auto_band"] = False
        L["inset_mm"] = 5
save(rect, "02_rect.png")

sq = copy.deepcopy(base)
sq["form"] = "circle"
sq["width_mm"] = 40
sq["height_mm"] = 40
for L in sq["layers"]:
    if L["type"] == "arc_text":
        L["auto_band"] = False
        L["inset_mm"] = 5
save(sq, "03_circle.png")

pf = copy.deepcopy(base)
pf["layers"] = [
    {"type": "ring", "inset_mm": 0.5, "thickness_mm": 0.3, "color": (35, 60, 170)},
    {"type": "pic_frame", "glyph": "star", "count": 40, "inset_mm": 2.0, "size_mm": 2.0,
     "color": (35, 60, 170)},
    {"type": "center_text", "lines": ["ЗВЕЗДЫ"], "size_mm": 4, "spacing_mm": 1,
     "w_pct": 100, "h_pct": 100, "font": "Arial", "bold": True, "plate_on": False,
     "plate_pad_mm": 1, "plate_color": (35, 60, 170), "color": (35, 60, 170)},
]
pf["form"] = "circle"
pf["width_mm"] = 40
pf["height_mm"] = 40
save(pf, "04_picframe_circle.png")

pf2 = copy.deepcopy(pf)
pf2["form"] = "rect"
pf2["width_mm"] = 50
pf2["height_mm"] = 30
pf2["layers"][0]["thickness_mm"] = 0.4
save(pf2, "05_picframe_rect.png")

plate = copy.deepcopy(base)
for L in plate["layers"]:
    if L["type"] == "center_text":
        L["plate_on"] = True
save(plate, "06_plate.png")

em = copy.deepcopy(base)
em["layers"].append({"type": "emblem", "path": os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "models", "image.jpg"),
                     "height_mm": 10, "dx_mm": 0, "dy_mm": 0, "recolor_on": True, "recolor": (35, 60, 170)})
save(em, "07_emblem.png")

rot = copy.deepcopy(base)
rot["rotation_deg"] = 12
save(rot, "08_rot12.png")

# сохранение/загрузка пресета
p = os.path.join(OUT, "preset_roundtrip.json")
with open(p, "w", encoding="utf-8") as f:
    json.dump(base, f, ensure_ascii=False)
with open(p, encoding="utf-8") as f:
    base2 = json.load(f)
save(base2, "09_preset_roundtrip.png")

# 10: прямоугольник со скруглёнными углами
rnd = copy.deepcopy(rect)
rnd["corner_mm"] = 3
save(rnd, "10_rect_rounded.png")

# 11: дуги притянуты к rect (с углами) — текст должен идти по сторонам, не по окружности
ra = copy.deepcopy(rect)
ra["corner_mm"] = 5
for L in ra["layers"]:
    if L["type"] == "arc_text":
        L["attract"] = "rect"
        L["ashift_mm"] = -4 if L["pos"] == "top" else 4
save(ra, "11_arc_rect_ashift.png")

# 12: пофрагментные стили (размер/цвет/шрифт внутри строк и дуг)
st = copy.deepcopy(base)
for L in st["layers"]:
    if L["type"] == "center_text":
        L["lines"] = ["{size=5;color=200,0,0;bold}ООО", "обычно {font=Times;size=4}курсивом"]
    if L["type"] == "arc_text" and L["pos"] == "top":
        L["text"] = "ТЕСТ {size=3;color=200,0,0}РАЗНОГО {size=2.2;bold}РАЗМЕРА"
save(st, "12_styles.png")

# 13: без рамок вообще (ring/band с нулевой толщиной)
nf = copy.deepcopy(base)
nf["layers"] = [
    {"type": "ring", "inset_mm": 1.0, "thickness_mm": 0, "color": (35, 60, 170)},
    {"type": "band", "inset_out_mm": 0, "inset_in_mm": 0, "color": (35, 60, 170)},
    {"type": "center_text", "lines": ["БЕЗ РАМОК"], "size_mm": 4, "spacing_mm": 1,
     "w_pct": 100, "h_pct": 100, "font": "Arial", "bold": True, "plate_on": False,
     "plate_pad_mm": 1, "plate_color": (35, 60, 170), "color": (35, 60, 170)},
]
save(nf, "13_no_frame.png")

# 14: построчные стили через line_styles + отрицательный интервал (строки внахлёст)
lsl = copy.deepcopy(base)
for L in lsl["layers"]:
    if L["type"] == "center_text":
        L["lines"] = ["ВЕРХНЯЯ", "СРЕДНЯЯ", "НИЖНЯЯ"]
        L["line_styles"] = [
            {"size_mm": 4.0, "color": [200, 0, 0], "font": "Arial"},
            {"size_mm": 2.0, "color": [0, 120, 0], "font": "Arial Black"},
            {"size_mm": 3.0, "color": [0, 0, 200], "bold": True}]
        L["spacing_mm"] = -1.0
save(lsl, "14_line_styles.png")

# 22: дуги ellipse/circle — буквы идут по дуге слева направо, с корректным поворотом
ae = copy.deepcopy(base)
ae["layers"] = [L for L in ae["layers"] if L["type"] in ("ring", "band", "center_text")]
ae["layers"] += [
    {"type": "arc_text", "text": "ПРОВЕРКА ДУГИ ВВЕРХУ", "pos": "top", "attract": "ellipse",
     "auto_band": False, "inset_mm": 2.0, "vshift_mm": 0, "ashift_mm": 0, "size_mm": 2.5,
     "w_pct": 100, "h_pct": 100, "spacing_mm": 0.3, "font": "Times", "bold": False,
     "flip": False, "color": (35, 60, 170)},
    {"type": "arc_text", "text": "ГОРОД · СТРАНА", "pos": "bottom", "attract": "ellipse",
     "auto_band": False, "inset_mm": 2.0, "vshift_mm": 0, "ashift_mm": 0, "size_mm": 2.2,
     "w_pct": 100, "h_pct": 100, "spacing_mm": 0.3, "font": "Times", "bold": False,
     "flip": False, "color": (35, 60, 170)},
    {"type": "arc_text", "text": "КРУГ ПО КРУГУ", "pos": "bottom", "attract": "circle",
     "auto_band": False, "inset_mm": 5.5, "vshift_mm": 0, "ashift_mm": 0, "size_mm": 2.0,
     "w_pct": 100, "h_pct": 100, "spacing_mm": 0.3, "font": "Times", "bold": False,
     "flip": False, "color": (35, 60, 170)},
]
ac_img = save(ae, "22_arcs_along_path.png")

# программная проверка: в каждой дуге буквы идут строго слева направо
import stamp_builder
_oat  = stamp_builder._arc_text
_opc  = stamp_builder._paste_char
_groups = []
def _pc(g):
    def pc(img, ch, st, nw, hpx, wf, x, y, R):
        g.append((ch, x)); return _opc(img, ch, st, nw, hpx, wf, x, y, R)
    return pc
def _at(img, spec, L, cx, cy, rx, ry):
    g = []; _groups.append((L["text"], g))
    stamp_builder._paste_char = _pc(g)
    return _oat(img, spec, L, cx, cy, rx, ry)
stamp_builder._arc_text = _at
stamp_builder.render_stamp(ae)
stamp_builder._arc_text, stamp_builder._paste_char = _oat, _opc
for txt, g in _groups:
    xs = [x for ch, x in g if ch.strip()]
    assert all(xs[i] < xs[i+1] - 0.5 for i in range(len(xs)-1)), f"дуга {txt!r}: буквы не по порядку"

# 25: pic_frame новые глифы — кольцо/пунктир/ромб/крест
pf = copy.deepcopy(base)
pf["layers"] = [L for L in pf["layers"] if L["type"] in ("band", "center_text")]
pf["layers"] += [
    {"type": "pic_frame", "glyph": "ring", "count": 36, "inset_mm": 1.2, "size_mm": 1.6,
     "color": (35, 60, 170)},
    {"type": "pic_frame", "glyph": "dash", "count": 60, "inset_mm": 3.2, "size_mm": 1.6,
     "color": (35, 60, 170)},
    {"type": "pic_frame", "glyph": "diamond", "count": 24, "inset_mm": 5.0, "size_mm": 1.4,
     "color": (170, 40, 40)},
    {"type": "pic_frame", "glyph": "plus", "count": 40, "inset_mm": 6.6, "size_mm": 1.4,
     "color": (35, 60, 170)},
]
save(pf, "25_picframe_glyphs.png")

print("ALL RENDER TESTS PASSED")


# 32: построчная геометрия — dx_mm/dy_mm/w_pct/h_pct в line_styles
lg = copy.deepcopy(base)
lg["layers"] = [Lg for Lg in lg["layers"] if Lg["type"] == "center_text"][:1]
lg["noise_pct"] = 0
for Lg in lg["layers"]:
    Lg["lines"] = ["СДВИГ ВПРАВО", "РАСТЯЖКА 150%", "СЖАТИЕ+ПОДЪЁМ"]
    Lg["size_mm"] = 2.6
    Lg["line_styles"] = [
        {"dx_mm": 6.0},
        {"w_pct": 150, "dy_mm": 0.5},
        {"w_pct": 70, "h_pct": 140, "dx_mm": -6.0}]
save(lg, "32_line_geometry.png")
# проверка: центры строк реально разъехались по X (dx=+6 против dx=-6)
from PIL import Image as _Img
import numpy as _np
img32 = _Img.open(os.path.join(OUT, "32_line_geometry.png")).convert("RGBA")
_a = _np.array(img32)[:, :, 3] > 0
_rows = _a.any(axis=1)
_y0, _y1 = _rows.argmax(), len(_rows) - _rows[::-1].argmax()
band = (_y1 - _y0) / 3
_centers = []
for _k in range(3):
    seg = _a[int(_y0 + _k*band + 5):int(_y0 + (_k+1)*band - 5), :]
    xs = _np.where(seg.any(axis=0))[0]
    _centers.append(float(xs.mean()))
# dx=+6 против dx=-6: центр строки 1 должен быть правее центра строки 3 заметно
_shift = _centers[0] - _centers[2]
assert _shift > 0.10 * img32.size[0], f"построчный dx не работает: centers={_centers}"
print("32_line_geometry OK, center shift px:", round(_shift, 1))

# ============ v3.8: core-фиксы очистки и LaMa ============
import numpy as _n
import cv2 as _cv
from core.inpaint import crop_mask_bbox  # noqa: E402
from core.clean import build_clean_masks as _bcm, smart_fill as _sf  # noqa: E402

# 33: bbox-кроп для динамического LaMa
_mk = _n.zeros((3000, 2000), _n.uint8)
_mk[1000:1100, 1200:1400] = 255
_box = crop_mask_bbox(_mk.shape, _mk)
assert _box == (1152, 952, 1448, 1148), f"crop_mask_bbox: {_box}"
assert crop_mask_bbox((100, 100), _n.zeros((100, 100), _n.uint8)) == (0, 0, 100, 100)
_big = _n.zeros((100, 100), _n.uint8); _big[:, :] = 255
assert crop_mask_bbox((100, 100), _big) == (0, 0, 100, 100)
print("33_crop_bbox OK")

# 34: пипетка ФОНА — цветная бумага CMR не затирается «своим»
_pap = _n.full((300, 300, 3), (120, 120, 130), _n.uint8)  # «синяя бумага», lum~123
_ownc = (40, 30, 170)
_pap[140:160, 60:240] = _ownc  # своя синяя надпись
_m1 = _bcm(_pap, (0, 0, 300, 300), _ownc, None, 35, "rect")
_m2 = _bcm(_pap, (0, 0, 300, 300), _ownc, None, 35, "rect", bg_bgr=(120, 120, 130))
_f1 = _cv.countNonZero(_m1["foreign"]); _f2 = _cv.countNonZero(_m2["foreign"])
assert _f1 > 5000, f"без пипетки фон должен попадать в чужое: {_f1}"
assert _f2 == 0, f"с пипеткой ФОНА чужого быть не должно: {_f2}"
print(f"34_bg_pipette OK (before={_f1}, after={_f2})")

# 35: мульти-пипетка ЧУЖОГО ловит «пограничные» пиксели
_w = _n.full((200, 200, 3), 245, _n.uint8)
_gap = (120, 80, 140)
_w[80:120, 80:140] = _gap  # цвет «между своим и чужим»
_w[20:30, 20:180] = _ownc  # своя синева
_a1 = _cv.countNonZero(_bcm(_w, (0, 0, 200, 200), _ownc, None, 35, "rect")["foreign"][85:115, 85:135])
_a2 = _cv.countNonZero(_bcm(_w, (0, 0, 200, 200), _ownc, [_gap], 35, "rect")["foreign"][85:115, 85:135])
_a3 = _cv.countNonZero(_bcm(_w, (0, 0, 200, 200), _ownc, _gap, 35, "rect")["foreign"][85:115, 85:135])
assert _a1 == 0, f"без эталона чужого пограничный цвет не должен попадать: {_a1}"
assert _a2 > 500, f"с эталоном чужого он обязан ловиться: {_a2}"
assert _a3 == _a2, "одинарный tuple должен работать как раньше"
print(f"35_multi_foreign OK (off={_a1}, on={_a2})")

# 36: подкраска внутри печати = локальный inpaint (градиент чернил), не плоская медиана
_W, _H = 240, 120
_img36 = _n.full((_H, _W, 3), 235, _n.uint8)
_truth = _img36.copy()
for _x in range(20, 220):  # горизонтальная «своя» черта с градиентом плотности
    _b = 90 + int(120 * (_x - 20) / 200)
    _img36[55:61, _x] = (20, 20, _b)
    _truth[55:61, _x] = (20, 20, _b)
_img36[50:66, 40:81] = (15, 15, 15)  # чужая подпись через черту (слева, где градиент заметен)
_m36 = _bcm(_img36, (0, 0, _W, _H), (20, 20, 150), None, 35, "rect")
_res = _sf(_img36, _m36["own"], _m36["foreign"], seed=7)
# свои пиксемы вне чужого не тронуты
_chg = (_res != _img36).any(axis=2)
assert not (_chg & (_m36["foreign"] == 0)).any(), "трогает пиксели вне маски"
_zone = _n.zeros((_H, _W), bool); _zone[55:61, 46:76] = True
_err = _n.abs(_res[_zone].astype(int) - _truth[_zone].astype(int)).mean()
_med = _n.abs(_n.array([20, 20, 150]) - _truth[_zone].astype(int)).mean()  # ошибка плоской медианы
assert _err < 25, f"заливка не повторяет чернила: err={_err:.1f}"
assert _err < _med, f"заливка хуже плоской медианы: {_err:.1f} vs {_med:.1f}"
# бумага под чужим остаётся бумагой
_pz = _n.zeros((_H, _W), bool); _pz[50:54, 46:76] = True
_perr = _n.abs(_res[_pz].astype(int) - 235).mean()
assert _perr < 30, f"бумага испорчена: {_perr:.1f}"
print(f"36_inpaint_fill OK (err={_err:.1f}, flat_median_err={_med:.1f})")

# 37: LaMa не оставляет «белое поле» (ONNX отдаёт выход 0..255 — обязательна нормализовка;
#     плюс tiled-режим родного разрешения для fixed-512 модели). Тест с живой моделью.
try:
    from core.inpaint import LamaInpainter, find_lama_model
    _mdl = find_lama_model()
except Exception:
    _mdl = None
if _mdl:
    _PAP = _n.array((205, 165, 105), _n.uint8)  # BGR «синяя бумага»
    _Hb, _Wb = 1000, 900
    _bs = _n.empty((_Hb, _Wb, 3), _n.uint8); _bs[:] = _PAP
    _yy, _xx = _n.ogrid[:_Hb, :_Wb]
    _e37 = ((_xx - 450) / 220) ** 2 + ((_yy - 500) / 180) ** 2
    _ink37 = (_e37 > 0.7) & (_e37 < 1.0)
    _im37 = _bs.copy()
    _im37[_ink37] = (70, 35, 195)  # пурпурно-красные «чернила»
    _mk37 = _cv.dilate(_ink37.astype(_n.uint8) * 255, _n.ones((5, 5), _n.uint8))
    _lm = LamaInpainter(_mdl)
    _o37 = _lm(_im37, _mk37)
    _sel = _mk37 > 0
    _white = float((_o37[_sel] > 235).all(axis=-1).mean())
    _red_in = float((_im37[_sel].astype(int)[:, 2] - _im37[_sel].astype(int)[:, :2].mean(axis=1)).mean())
    _red_out = float((_o37[_sel].astype(int)[:, 2] - _o37[_sel].astype(int)[:, :2].mean(axis=1)).mean())
    _pap = float((_n.abs(_o37[_sel].astype(float) - _PAP.astype(float)).mean(axis=-1) < 45).mean())
    assert _white < 0.05, f"осталось белое поле: {_white:.3f}"
    assert _red_out < _red_in * 0.3, f"краснота не убрана: {_red_out:.1f} vs {_red_in:.1f}"
    assert _pap > 0.7, f"заполнение непохоже на бумагу: {_pap:.3f}"
    print(f"37_lama_no_white_field OK (white={_white:.3f}, red {_red_in:.0f}->{_red_out:.0f}, paper={_pap:.2f})")
else:
    print("37_lama_no_white_field SKIP (lama.onnx не найдена)")

# 38: приоритет пипетки ЧУЖОГО над «своим» (баг пользователя: синяя полоса при
# пурпурной печати помечалась ЗЕЛЁНЫМ — проекция делала её «своей»). Сценарий
# повторяет скан CMR: пурпурная круглая печать + синяя горизонтальная полоса.
_Hh, _Ww = 600, 900
_img38 = _n.full((_Hh, _Ww, 3), 240, _n.uint8)
_yy38, _xx38 = _n.ogrid[:_Hh, :_Ww]
_e38 = ((_xx38 - 450) / 220.0) ** 2 + ((_yy38 - 300) / 170.0) ** 2
_ring = (_e38 > 0.85) & (_e38 < 1.0)
_img38[_ring] = (150, 60, 110)                      # пурпурная «своя» печать
_stripe = (_yy38 >= 296) & (_yy38 <= 302) & (_xx38 >= 60) & (_xx38 <= 840)
_img38[_stripe] = (200, 60, 40)                     # синяя полоса ЧУЖОГО (поверх)
_m38 = _bcm(_img38, (40, 40, 820, 520), (150, 60, 110), [(200, 60, 40)], 35, "rect")
_own38, _fg38 = _m38["own"] > 0, _m38["foreign"] > 0
_ssel = _n.zeros((_Hh, _Ww), bool); _ssel[297:302, 70:831] = True
_rsel = _ring & (_n.abs(_yy38 - 300) > 20)
_f_stripe = float(_fg38[_ssel].mean())
_f_ring_own = float(_own38[_rsel].mean())
_f_ring_fg = float(_fg38[_rsel].mean())
assert _f_stripe > 0.85, f"синяя полоса не стала чужим: {_f_stripe:.3f}"
assert _f_ring_own > 0.85, f"печать потерялась в «своем»: {_f_ring_own:.3f}"
assert _f_ring_fg < 0.05, f"печать попала в чужое: {_f_ring_fg:.3f}"
_ov = _img38.astype(_n.float32)
_red = _n.zeros_like(_ov); _red[..., 2] = 255
_grn = _n.zeros_like(_ov); _grn[..., 1] = 255
_ov[_fg38] = _ov[_fg38] * 0.35 + _red[_fg38] * 0.65
_ov[_own38 & ~_fg38] = _ov[_own38 & ~_fg38] * 0.5 + _grn[_own38 & ~_fg38] * 0.5
_Img.fromarray(_cv.cvtColor(_n.clip(_ov, 0, 255).astype(_n.uint8), _cv.COLOR_BGR2RGB))\
    .save(os.path.join(OUT, "38_pip_priority.png"))
print(f"38_pip_foreign_priority OK (stripe_fg={_f_stripe:.2f}, ring_own={_f_ring_own:.2f}, ring_fg={_f_ring_fg:.2f})")

# 39: «Рамка: стереть» БЕЗ рамки выделения — трогает только помеченное.
# Баг пользователя: всё чёрное по всему документу затёрлось белым (автоклассификатор
# без рамки работал по всему изображению).
_Hh39, _Ww39 = 700, 1000
_img39 = _n.full((_Hh39, _Ww39, 3), 240, _n.uint8)
for _ty in range(50, _Hh39 - 40, 60):                       # «текст» по всему листу
    _img39[_ty:_ty + 5, 50:950] = (30, 30, 30)
_yy39, _xx39 = _n.ogrid[:_Hh39, :_Ww39]
_e39a = ((_xx39 - 750) / 50.0) ** 2 + ((_yy39 - 300) / 45.0) ** 2
_ring_in = (_e39a > 0.85) & (_e39a < 1.0)                   # печать ВНУТРИ метки
_e39b = ((_xx39 - 750) / 170.0) ** 2 + ((_yy39 - 300) / 160.0) ** 2
_ring_out = (_e39b > 0.85) & (_e39b < 1.0)                  # та же «своя» печать СНАРУЖИ
_img39[_ring_in | _ring_out] = (150, 60, 110)
_mark = _n.zeros((_Hh39, _Ww39), _n.uint8)                  # «Рамка: стереть» вокруг печати
_mark[240:361, 690:811] = 255
_m39 = _bcm(_img39, None, (150, 60, 110), None, 35, "rect", region=_mark)
_fg39 = _m39["foreign"] > 0
_far = _n.zeros((_Hh39, _Ww39), bool); _far[55:141, 50:950] = True   # текст вдали от метки
assert int(_fg39[_far].sum()) == 0, f"текст вдали затронут: {int(_fg39[_far].sum())} px"
assert _fg39[_ring_in].mean() > 0.9, "печать внутри метки не стирается"
_txt_in = _n.zeros((_Hh39, _Ww39), bool); _txt_in[290:295, 695:806] = True  # строка внутри
assert _fg39[_txt_in].mean() > 0.9, "текст внутри «Рамки: стереть» не стёрся"
_halo39 = _cv.dilate(_mark, _n.ones((41, 41), _n.uint8)) > 0
assert _fg39[_ring_out & ~_halo39].mean() < 0.05, \
    "своя печать вне метки попала в чужое"
_ov39 = _img39.astype(_n.float32)
_red39 = _n.zeros_like(_ov39); _red39[..., 2] = 255
_ov39[_fg39] = _ov39[_fg39] * 0.35 + _red39[_fg39] * 0.65
_Img.fromarray(_cv.cvtColor(_n.clip(_ov39, 0, 255).astype(_n.uint8), _cv.COLOR_BGR2RGB))\
    .save(os.path.join(OUT, "39_rect_erase_local.png"))
print(f"39_rect_erase_local OK (far_touched=0, in_ring={_fg39[_ring_in].mean():.2f}, "
      f"in_txt={_fg39[_txt_in].mean():.2f})")

# 40: «своя» розовая, в кадре её нет; голубая полоса — ЧУЖОЙ пипеткой.
# Баг пользователя (2026-11-11, реальный CMR): полоса подсвечивалась ЗЕЛЁНЫМ
# (попадала в «своё») из-за проекции на направление сигнатуры.
_Hh40, _Ww40 = 400, 600
_img40 = _n.full((_Hh40, _Ww40, 3), 235, _n.uint8)
_yy40, _xx40 = _n.ogrid[:_Hh40, :_Ww40]
_g40 = _n.broadcast_to((_yy40 - 120) / 160.0, (_Hh40, _Ww40))  # голубая ПОЛОСА с градиентом
_band = (_yy40 >= 120) & (_yy40 < 280) & (_xx40 >= 250) & (_xx40 < 450)
for _ch, (_a, _dlt) in enumerate([(200, 35), (150, 40), (60, 30)]):
    _img40[_band, _ch] = _n.clip(_a + _dlt * _g40[_band], 0, 255).astype(_n.uint8)
_e40 = ((_xx40 - 510) / 35.0) ** 2 + ((_yy40 - 200) / 30.0) ** 2   # розовое кольцо (своё)
_ring40 = (_e40 > 0.8) & (_e40 < 1.0)
_img40[_ring40] = (100, 80, 230)
_m40 = _bcm(_img40, (50, 50, 560, 350), (100, 80, 230), [(215, 170, 75)], 35, "rect")
_fg40 = _m40["foreign"] > 0
_own40 = _m40["own"] > 0
_core40 = _n.zeros((_Hh40, _Ww40), bool); _core40[135:265, 265:435] = True
assert _fg40[_core40].mean() > 0.95 and _own40[_core40].mean() < 0.02, \
    f"полоса: fg={_fg40[_core40].mean():.2f} own={_own40[_core40].mean():.2f}"
assert _own40[_ring40].mean() > 0.9, "розовая печать перестала узнаваться"
_ov40 = _img40.astype(_n.float32)
_red40 = _n.zeros_like(_ov40); _red40[..., 2] = 255
_ov40[_fg40] = _ov40[_fg40] * 0.35 + _red40[_fg40] * 0.65
_gr40 = _n.zeros_like(_ov40); _gr40[..., 1] = 255
_ov40[_own40] = _ov40[_own40] * 0.35 + _gr40[_own40] * 0.65
_Img.fromarray(_cv.cvtColor(_n.clip(_ov40, 0, 255).astype(_n.uint8), _cv.COLOR_BGR2RGB))\
    .save(os.path.join(OUT, "40_hue_foreign_band.png"))
print(f"40_hue_foreign_band OK (band_fg={_fg40[_core40].mean():.2f}, "
      f"band_own={_own40[_core40].mean():.2f}, ring_own={_own40[_ring40].mean():.2f})")

# ============ v3.8.6: 41 — типовые пресеты: загрузка/рендер/round-trip ============
from PIL import Image as _Img41
_pdir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "presets")
_tiles, _ok41 = [], []
for _fn in sorted(os.listdir(_pdir)):
    if not _fn.endswith(".json"):
        continue
    _p41 = os.path.join(_pdir, _fn)
    with open(_p41, encoding="utf-8") as _f41:
        _spec41 = json.load(_f41)
    _im41 = render_stamp(_spec41)
    _a41 = _im41.split()[3]
    assert _a41.getextrema()[1] > 0, f"{_fn}: пустой рендер"
    # JSON round-trip: сохранение/перезагрузка не меняет ни спецификацию, ни картинку
    _rt = json.loads(json.dumps(_spec41, ensure_ascii=False))
    assert _rt == _spec41, f"{_fn}: round-trip меняет spec"
    assert render_stamp(_rt) == _im41, f"{_fn}: round-trip меняет рендер"
    # геометрия: текст не должен пересекать кольца/звёзды (объективная проверка,
    # в отличие от взгляда на монтаж) — слои рендерятся по-отдельности, маски
    # пересекаются как множества пикселей
    import numpy as _np41
    _base_rl41 = [L for L in _spec41["layers"] if L["type"] in ("ring", "band", "pic_frame")]
    for _L41 in _spec41["layers"]:
        if _L41["type"] not in ("arc_text", "center_text"):
            continue
        # текст на закрашенной ленте (auto_band) лежит на ленте НАМЕРЕННО —
        # для таких слоём лента не препятствие
        _rl41 = [L for L in _base_rl41
                 if not (L["type"] == "band" and _L41.get("auto_band"))]
        _mR41 = None
        if _rl41:
            _mR41 = _np41.asarray(render_stamp({**_spec41, "layers": _rl41}).split()[3]) > 128
        if _mR41 is None:
            continue
        _mT41 = _np41.asarray(render_stamp({**_spec41, "layers": [_L41]}).split()[3]) > 128
        _ov41 = int(_np41.logical_and(_mT41, _mR41).sum())
        if _fn == "jenti_example.json":  # легальный исторический пример: не «ремонтируем»
            continue
        assert _ov41 <= 20, f"{_fn}: текст пересекает рамку ({_ov41} px): {_L41.get('text', _L41.get('lines'))!r}"
    # цвет задаём RGB (40,60,190): проверяем, что дух сохраняется «синим», не красным
    _rgb41 = _n.asarray(_im41)[:, :, :3]
    _inkm41 = _n.asarray(_a41) > 128
    if _fn != "jenti_example.json":
        _mean41 = _rgb41[_inkm41].mean(axis=0)
        assert _mean41[2] > _mean41[0], f"{_fn}: цвет стал красным: {_mean41}"
    _th41 = 360
    _im41.thumbnail((_th41, _th41))
    _cv41 = _Img41.new("RGBA", (_th41, _th41), (255, 255, 255, 255))
    _off41 = ((_th41 - _im41.width) // 2, (_th41 - _im41.height) // 2)
    _cv41.alpha_composite(_im41, _off41)
    _tiles.append(_cv41)
    _ok41.append(_fn)
assert len(_ok41) >= 5, f"пресетов меньше 5: {_ok41}"
_strip = _Img41.new("RGB", (360 * len(_tiles), 360), (255, 255, 255))
for _i41, _t41 in enumerate(_tiles):
    _strip.paste(_t41, (360 * _i41, 0))
_strip.save(os.path.join(OUT, "41_presets.png"))
print(f"41_presets OK ({len(_ok41)} presets: {', '.join(_ok41)})")
