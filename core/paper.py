# core/paper.py
"""
Синтез бумажной заплатки (идея из Mini-Nitro: measure_background +
make_background_patch), улучшенная под БОЛЬШИЕ рамки: тон замеряется
по 4 сторонам каймы и интерполируется градиентом (Coons), сверху —
низкочастотное «бумажное» зерно. Результат статистически = окружение,
поэтому границы вклейки не видно даже без feather.
"""
import cv2
import numpy as np

from core.inpaint import build_frame_mask


def _robust_sigma(pixels):
    """pixels: (N,3) float. Робастный разброс по центральным 70% каждого канала."""
    out = np.empty(3, np.float32)
    for c in range(3):
        a = np.sort(pixels[:, c])
        n = a.size
        if n == 0:
            out[c] = 2.0
            continue
        lo = a[max(0, int(n * 0.15))]
        hi = a[min(n - 1, int(n * 0.85))]
        core = a[(a >= lo) & (a <= hi)]
        if core.size == 0:
            core = a
        out[c] = float(np.clip(np.std(core), 1.5, 7.0))
    return out


def _measure_edges(bgr, x0, y0, x1, y1, band):
    """
    Возвращает профили медиан по 4 сторонам каймы + глобальную sigma.
    top/bottom: (W,3); left/right: (H,3). Если кайма у края листа —
    недостающая сторона заменяется глобальной медианой.
    """
    H, W = bgr.shape[:2]
    w, h = x1 - x0, y1 - y0
    band = max(2, int(band))
    f = bgr.astype(np.float32)

    yt0, yt1 = max(0, y0 - band), y0
    yb0, yb1 = y1, min(H, y1 + band)
    xl0, xl1 = max(0, x0 - band), x0
    xr0, xr1 = x1, min(W, x1 + band)

    top = np.median(f[yt0:yt1, x0:x1], axis=0) if yt1 > yt0 else None
    bot = np.median(f[yb0:yb1, x0:x1], axis=0) if yb1 > yb0 else None
    lef = np.median(f[y0:y1, xl0:xl1], axis=1) if xl1 > xl0 else None
    rig = np.median(f[y0:y1, xr0:xr1], axis=1) if xr1 > xr0 else None

    strips = [s for s in (top, bot, lef, rig) if s is not None and s.size]
    if not strips:
        g = np.median(f.reshape(-1, 3), axis=0)
        return (np.tile(g, (w, 1)), np.tile(g, (w, 1)),
                np.tile(g, (h, 1)), np.tile(g, (h, 1)),
                np.full(3, 2.0, np.float32))

    glob_med = np.median(np.concatenate(strips, axis=0), axis=0)
    sigma = _robust_sigma(np.concatenate(strips, axis=0))

    if top is None or top.size == 0:
        top = np.tile(glob_med, (w, 1))
    if bot is None or bot.size == 0:
        bot = np.tile(glob_med, (w, 1))
    if lef is None or lef.size == 0:
        lef = np.tile(glob_med, (h, 1))
    if rig is None or rig.size == 0:
        rig = np.tile(glob_med, (h, 1))

    # согласованные углы для Coons (среднее смежных профилей на концах)
    P00 = (top[0] + lef[0]) * 0.5
    P10 = (top[-1] + rig[0]) * 0.5
    P01 = (bot[0] + lef[-1]) * 0.5
    P11 = (bot[-1] + rig[-1]) * 0.5
    return top, bot, lef, rig, sigma, P00, P10, P01, P11


def _gradient_field(w, h, top, bot, lef, rig, P00, P10, P01, P11):
    tx = (np.arange(w, dtype=np.float32) / max(1, w - 1))[None, :, None]   # (1,W,1)
    ty = (np.arange(h, dtype=np.float32) / max(1, h - 1))[:, None, None]   # (H,1,1)

    term_tb = top[None, :, :] * (1.0 - ty) + bot[None, :, :] * ty          # (H,W,3)
    term_lr = lef[:, None, :] * (1.0 - tx) + rig[:, None, :] * tx          # (H,W,3)

    c = (P00[None, None, :] * (1.0 - tx) * (1.0 - ty) +
         P10[None, None, :] * tx * (1.0 - ty) +
         P01[None, None, :] * (1.0 - tx) * ty +
         P11[None, None, :] * tx * ty)

    return np.clip(term_tb + term_lr - c, 0.0, 255.0)


def _low_freq_noise(w, h, sigma, seed):
    """Зерно в половинном разрешении + LANCZOS-апскейл = низкие частоты."""
    rng = np.random.default_rng(int(seed))
    hw, hh = max(2, w // 2), max(2, h // 2)
    small = rng.standard_normal((hh, hw, 3)).astype(np.float32) * sigma[None, None, :]
    if (hw, hh) == (w, h):
        return small
    return cv2.resize(small, (w, h), interpolation=cv2.INTER_LANCZOS4)


def paper_patch(bgr, rect, kind="rect", band=6, seed=None):
    """
    Возвращает изображение того же размера, где внутри маски рамки —
    синтезированная бумага (градиент по кайме + зерно), снаружи — оригинал.
    Для эллипса край сглажен на ~1px (антиалиас), для прямоугольника — жёсткий
    (прямые края совпадают с бумагой, перо не нужно).
    """
    import random as _rnd
    if seed is None:
        seed = _rnd.randint(0, 2_147_483_647)

    H, W = bgr.shape[:2]
    x0, y0, x1, y1 = [int(v) for v in rect]
    x0, y0 = max(0, x0), max(0, y0)
    x1, y1 = min(W, x1), min(H, y1)
    w, h = x1 - x0, y1 - y0
    if w < 3 or h < 3:
        return bgr.copy()

    top, bot, lef, rig, sigma, P00, P10, P01, P11 = _measure_edges(
        bgr, x0, y0, x1, y1, band)

    base = _gradient_field(w, h, top, bot, lef, rig, P00, P10, P01, P11)
    base = base + _low_freq_noise(w, h, sigma, seed)
    base = np.clip(base, 0.0, 255.0).astype(np.uint8)

    # альфа: для эллипса — сглаженный край (антиалиас), для rect — жёсткая маска
    if kind == "ellipse":
        alpha = build_frame_mask((H, W), (x0, y0, x1, y1), "ellipse", feather=1)
    else:
        alpha = build_frame_mask((H, W), (x0, y0, x1, y1), "rect", feather=0)
    if alpha is None:
        return bgr.copy()
    a = (alpha[y0:y1, x0:x1].astype(np.float32) / 255.0)[..., None]   # (h,w,1)

    result = bgr.copy()
    region = bgr[y0:y1, x0:x1].astype(np.float32)
    comp = region * (1.0 - a) + base.astype(np.float32) * a
    result[y0:y1, x0:x1] = np.clip(comp, 0.0, 255.0).astype(np.uint8)
    return result