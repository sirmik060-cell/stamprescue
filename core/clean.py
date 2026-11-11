# core/clean.py
"""
Разделение слоёв по «синеве» + детерминированное замещение.
Свой (печать) = тёмное И синее -> не трогается.
Чужое = тёмное И не синее -> замещается:
  на печати -> цветом чернил печати (+зерно),
  на бумаге -> синтезированной бумагой (замер вокруг, как в Mini-Nitro).
"""
import cv2
import numpy as np

from core.inpaint import build_frame_mask
from core.paper import _gradient_field, _low_freq_noise, _measure_edges


def bgr_to_hsv(bgr_tuple):
    px = np.uint8([[list(bgr_tuple)]])
    return tuple(int(c) for c in cv2.cvtColor(px, cv2.COLOR_BGR2HSV)[0, 0])


def _hsv_to_bgr(hsv_tuple):
    px = np.uint8([[list(hsv_tuple)]])
    return tuple(int(c) for c in cv2.cvtColor(px, cv2.COLOR_HSV2BGR)[0, 0])


def _own_signature(color_bgr):
    """Вектор «цветности» эталона: отклонения каналов от серого. norm<12 = ахромат."""
    s = np.array(color_bgr, np.float32)
    s = s - float(s.mean())
    return s, float(np.linalg.norm(s))


def build_clean_masks(bgr, rect, own_bgr=None, foreign_bgr=None, tol=35, kind="rect", region=None,
                      bg_bgr=None):
    """Свой/чужое относительно ЦВЕТА ПИПЕТКИ (own_bgr — BGR-эталон своей печати).
   own   = тёмное и по цвету близко к эталону (проекция на цветовую сигнатуру);
   чужое = тёмное и далеко от эталона; пометки кистью (region) — чужое БЕЗ цветовой проверки.
   foreign_bgr — один BGR-эталон или список (до 3): пиксель чужой, если БЛИЗОК ПО
   ЦВЕТУ к ЛЮБОМУ эталону (расстояние, как у фона); это приоритет над «своим».
   bg_bgr — пипетка ФОНА: пиксели, близкие к фону, не считаются ни своим, ни чужим
   (защита от «затирания фона своим цветом» на цветной бумаге типа синего CMR).
    own_bgr=None -> легаси-эвристика «синева» (B > R,G)."""
    H, W = bgr.shape[:2]
    fig = build_frame_mask((H, W), rect, kind, feather=0)
    if fig is None:
        fig = np.ones((H, W), np.uint8) * 255
    figb = fig > 0
    forced = (np.asarray(region) > 0) if region is not None else np.zeros((H, W), bool)
    if rect is None and forced.any():
        # Рамки выделения нет — работают ТОЛЬКО пометки кисти/«Рамки: стереть».
        # Автоклассификацию ограничиваем окрестностью пометок (диляция 41px):
        # иначе «чужим» считается весь документ и чёрный текст затирается белым
        # (баг пользователя: «всё что было черным по всему документу обратилось
        # в белый»). Пометки-приказ при этом действуют всегда, вне рамок.
        figb = cv2.dilate(forced.astype(np.uint8),
                          cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (41, 41))) > 0

    B = bgr[..., 0].astype(np.int16)
    G = bgr[..., 1].astype(np.int16)
    R = bgr[..., 2].astype(np.int16)
    lum = (R.astype(np.int32) * 299 + G.astype(np.int32) * 587 + B.astype(np.int32) * 114) // 1000
    ink = lum < 215                            # всё тёмное (печать+подпись+линии)

    T = int(tol)
    foreign_pip = np.zeros((H, W), bool)
    if own_bgr is None:
        # легаси: «синий = свой»
        bs = B - (R + G) // 2
        own = ink & (bs >= T) & figb
        foreign_core = ink & (bs <= T - 12)
    else:
        s, n = _own_signature(own_bgr)
        # хроматическая величина пикселя: отклонение каналов от его же серого
        sgn = (bgr.astype(np.float32)
               - bgr.astype(np.float32).mean(axis=2, keepdims=True))
        mag = np.sqrt((sgn * sgn).sum(axis=2))
        if n >= 12.0:
            # «своё» = цветной пиксель: оттенок (hue, круговая разница в HSV) близок
            # к эталону И хроматическая величина достаточна (как и раньше, порог T
            # по модулю отклонения). Прежняя метрика — одна проекция на направление
            # с абсолютными каналами — меряла яркость вместо оттенка: голубая полоса
            # с сильным B-каналом давала высокий score при розовой/пурпурной
            # «своей» сигнатуре и попадала в «своё» — в превью ЧУЖОЙ цвет оставался
            # зелёным (баг пользователя 2026-11-11). При этом величина обязана
            # остаться порогом: она отделяет синюю печать от голубой бумаги того же
            # оттенка (кейс 34).
            hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)
            hue_ref = int(cv2.cvtColor(
                np.array([[list(map(int, own_bgr))]], np.uint8),
                cv2.COLOR_BGR2HSV)[0, 0, 0])
            dh = np.abs(hsv[..., 0].astype(np.int16) - hue_ref)
            dh = np.minimum(dh, 180 - dh)
            hue_tol = max(8, int(round(T * 0.6)))   # больше допуск — шире оттенок
            own = ink & figb & (dh <= hue_tol) & (mag >= max(25.0, float(T)))
            foreign_core = ink & ~own
        else:
            # ахроматная своя печать (чёрная/серая): свой = тёмное и бесцветное
            chroma = (bgr.max(axis=2).astype(np.int16)
                      - bgr.min(axis=2).astype(np.int16))
            own = ink & (chroma <= max(10, T * 4 // 10)) & figb
            foreign_core = ink & (chroma >= T + 12)
        # Пипетка ЧУЖОГО = приказ: пиксели, близкие по ЦВЕТУ к эталону (та же
        # метрика расстояния, что у пипетки ФОНА). Направленная проекция не годилась:
        # синяя полоса проецируется почти параллельно пурпурной «своей» сигнатуре
        # (у обеих сильный синий канал) и попадала в «своё» — баг пользователя.
        if foreign_bgr is not None:
            fgs = [foreign_bgr] if isinstance(foreign_bgr, tuple) else list(foreign_bgr)[:3]
            for fgb in fgs:
                d = bgr.astype(np.int32) - np.array(fgb, np.int32)[None, None, :]
                foreign_pip |= (d * d).sum(axis=2) <= max(T, 18) ** 2

    if bg_bgr is not None:
        # фон, который пользователь показал пипеткой, не трогает вообще
        d = bgr.astype(np.int32) - np.array(bg_bgr, np.int32)[None, None, :]
        bgm = (d * d).sum(axis=2) <= max(T, 18) ** 2
        own = own & ~bgm
        foreign_core = foreign_core & ~bgm
        foreign_pip = foreign_pip & ~bgm

    # пипетка ЧУЖОГО приоритетна над цветовой эвристикой «своего»: показанный
    # чужим цвет вычитается из своего (иначе синяя полоса при пурпурной печати
    # оставалась «своей» и не удалялась)
    own = own & ~foreign_pip
    foreign_core = foreign_core | (foreign_pip & ink)
    foreign_u8 = foreign_core.astype(np.uint8) * 255
    foreign_u8 = cv2.dilate(foreign_u8, np.ones((3, 3), np.uint8))  # ореол штриха
    foreign_u8 = ((foreign_u8 > 0) & ~own & figb).astype(np.uint8) * 255  # свой НЕЛЬЗЯ
    if region is not None:
        # кисть/«Рамка: стереть» = приказ: помеченное сотрётся независимо от цвета
        # И независимо от рамки выделения (пометка вне рамки тоже работает)
        force = forced.astype(np.uint8) * 255
        foreign_u8 = cv2.bitwise_or(foreign_u8, force)

    own_u8 = own.astype(np.uint8) * 255
    return {"own": own_u8, "foreign": foreign_u8,
            "paper": ~ink, "fig": fig}


def smart_fill(bgr, own_u8, foreign_u8, seed=None):
    """Детерминированное замещение чужого: на печати -> чернила, на бумаге -> бумага."""
    import random as _rnd
    if seed is None:
        seed = _rnd.randint(0, 2_147_483_647)
    own = own_u8 > 0
    foreign = foreign_u8 > 0
    if not foreign.any():
        return bgr.copy()
    result = bgr.copy()

    # --- чернила печати: медианный цвет + зерно ---
    if own.any():
        px = bgr[own].astype(np.float32)
        own_color = np.median(px, axis=0)
        own_sigma = np.clip(px.std(axis=0), 1.5, 8.0)
    else:
        own_color = np.array([120.0, 80.0, 40.0])
        own_sigma = np.full(3, 3.0)

    on_stamp = foreign & (cv2.dilate(own_u8, np.ones((9, 9), np.uint8)) > 0)
    on_paper = foreign & ~on_stamp

    if on_stamp.any():
        # локальный TELEA-inpaint: штрихи чужого заменяются КОНТЕКСТОМ чернил печати
        # (градиент, толщина, зерно), а не плоским медианным цветом с шумом.
        ys, xs = np.where(on_stamp)
        x0, x1 = int(xs.min()), int(xs.max()) + 1
        y0, y1 = int(ys.min()), int(ys.max()) + 1
        pad = 16
        H, W = bgr.shape[:2]
        cx0, cx1 = max(0, x0 - pad), min(W, x1 + pad)
        cy0, cy1 = max(0, y0 - pad), min(H, y1 + pad)
        crop = bgr[cy0:cy1, cx0:cx1]
        m = (on_stamp[cy0:cy1, cx0:cx1] * 255).astype(np.uint8)
        filled = None
        if crop.size and m.any():
            try:
                filled = cv2.inpaint(crop, m, 4, cv2.INPAINT_TELEA)
            except cv2.error:
                filled = None
        if filled is not None:
            region = result[cy0:cy1, cx0:cx1]
            sel = m > 0
            region[sel] = filled[sel]
            result[cy0:cy1, cx0:cx1] = region
        else:
            # запасной вариант: прежняя плоская заливка медианой+зерном
            rng = np.random.default_rng(seed)
            fill = own_color[None, :] + rng.standard_normal((on_stamp.sum(), 3)) * own_sigma[None, :]
            result[ys, xs] = np.clip(fill, 0, 255).astype(np.uint8)

    if on_paper.any():
        ys, xs = np.where(on_paper)
        x0, x1 = int(xs.min()), int(xs.max()) + 1
        y0, y1 = int(ys.min()), int(ys.max()) + 1
        top, bot, lef, rig, sig, P00, P10, P01, P11 = _measure_edges(bgr, x0, y0, x1, y1, 6)
        base = _gradient_field(x1 - x0, y1 - y0, top, bot, lef, rig, P00, P10, P01, P11)
        field = np.clip(base + _low_freq_noise(x1 - x0, y1 - y0, sig, seed + 1), 0, 255)
        m = on_paper[y0:y1, x0:x1]
        region = result[y0:y1, x0:x1]
        region[m] = field[m]
        result[y0:y1, x0:x1] = region

    return result


def extract_ink(bgr, own_u8, feather=1, padding=8):
    H, W = bgr.shape[:2]
    ys, xs = np.where(own_u8 > 0)
    if len(xs) == 0:
        return None
    x0, y0 = int(xs.min()), int(ys.min())
    x1, y1 = int(xs.max()) + 1, int(ys.max()) + 1
    xp0, yp0 = max(0, x0 - padding), max(0, y0 - padding)
    xp1, yp1 = min(W, x1 + padding), min(H, y1 + padding)

    crop = cv2.cvtColor(bgr[yp0:yp1, xp0:xp1], cv2.COLOR_BGR2BGRA)
    alpha = own_u8[yp0:yp1, xp0:xp1].copy()
    alpha = cv2.dilate(alpha, np.ones((3, 3), np.uint8), iterations=1)
    if feather and feather > 0:
        k = int(feather) * 2 + 1
        alpha = cv2.GaussianBlur(alpha, (k, k), 0)
    crop[..., 3] = alpha
    return crop