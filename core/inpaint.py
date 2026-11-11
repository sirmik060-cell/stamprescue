# core/inpaint.py
import os
import sys

import cv2
import numpy as np

try:
    import onnxruntime as ort
    HAVE_ORT = True
except ImportError:
    HAVE_ORT = False


def build_frame_mask(shape_hw, rect, kind="rect", feather=0):
    """rect: (x0, y0, x1, y1) или None (без рамки). Возвращает маску 0..255."""
    if rect is None:
        return None
    h, w = shape_hw
    x0, y0, x1, y1 = [int(v) for v in rect]
    x0, y0 = max(0, x0), max(0, y0)
    x1, y1 = min(w, x1), min(h, y1)
    if x1 - x0 < 2 or y1 - y0 < 2:
        return None

    mask = np.zeros((h, w), np.uint8)
    if kind == "ellipse":
        cx, cy = (x0 + x1) // 2, (y0 + y1) // 2
        ax, ay = max(1, (x1 - x0) // 2), max(1, (y1 - y0) // 2)
        cv2.ellipse(mask, (cx, cy), (ax, ay), 0, 0, 360, 255, -1)
    else:
        mask[y0:y1, x0:x1] = 255

    if feather and feather > 0:
        k = int(feather) * 2 + 1
        mask = cv2.GaussianBlur(mask, (k, k), 0)
    return mask


def blend_result(original, result, mask):
    """Вклейка результата только по маске — никаких швов на границе рамки."""
    a = (mask.astype(np.float32) / 255.0)[..., None]
    out = original.astype(np.float32) * (1.0 - a) + result.astype(np.float32) * a
    return np.clip(out, 0, 255).astype(np.uint8)


def opencv_inpaint(bgr, mask, radius=6):
    m = (mask > 127).astype(np.uint8) * 255
    m = cv2.dilate(m, np.ones((3, 3), np.uint8), iterations=2)
    return cv2.inpaint(bgr, m, radius, cv2.INPAINT_TELEA)


def crop_mask_bbox(shape_hw, mask_u8, pad_frac=0.2, min_pad=48):
    """BBox маски + контекст. Для больших страниц LaMa гоняется по кропу,
    а не по всей сжатой странице: модель видит объект крупно и не «белеет»."""
    H, W = shape_hw
    ys, xs = np.where(mask_u8 > 0)
    if len(xs) == 0:
        return 0, 0, W, H
    x0, x1 = int(xs.min()), int(xs.max()) + 1
    y0, y1 = int(ys.min()), int(ys.max()) + 1
    px = max(min_pad, int((x1 - x0) * pad_frac))
    py = max(min_pad, int((y1 - y0) * pad_frac))
    return max(0, x0 - px), max(0, y0 - py), min(W, x1 + px), min(H, y1 + py)


class LamaInpainter:
    """
    LaMa через ONNX. Адаптивный вход: сам читает подпись модели.
      - вход динамический -> вся страница, max_side + pad_mod  (big-lama)
      - вход фиксированный (напр. 512x512) -> crop рамки -> resize -> прогон -> обратно
      - один вход (4 кан) ИЛИ два входа (image+mask) — определяется автоматически
    """

    def __init__(self, model_path):
        if not HAVE_ORT:
            raise RuntimeError("onnxruntime не установлен")
        avail = ort.get_available_providers()
        fast = [p for p in avail if p in ("CUDAExecutionProvider",
                                          "DmlExecutionProvider",
                                          "TensorrtExecutionProvider")]
        providers = fast + ["CPUExecutionProvider"]
        self.session = ort.InferenceSession(str(model_path), providers=providers)
        self.providers = self.session.get_providers()

        self.input_specs = [(i.name, list(i.shape)) for i in self.session.get_inputs()]
        self.input_names = [n for n, _ in self.input_specs]

        self.img_name = next(
            (n for n in self.input_names if ("image" in n.lower() or "img" in n.lower())),
            self.input_names[0])
        self.mask_name = next(
            (n for n in self.input_names if "mask" in n.lower()),
            self.input_names[1] if len(self.input_names) > 1 else self.input_names[0])

        shapes = dict(self.input_specs)
        mshape = shapes.get(self.mask_name, [])
        self.mask_channels = 1
        if len(mshape) >= 2 and isinstance(mshape[1], int) and mshape[1] in (1, 3):
            self.mask_channels = mshape[1]

        self.two_input = (len(self.input_names) >= 2)

        # читаем ожидаемый H,W входа картинки: числа = фикс, строки/None = динам
        ishape = shapes.get(self.img_name, [])
        self.fixed_hw = None
        if len(ishape) >= 4 and isinstance(ishape[2], int) and isinstance(ishape[3], int):
            self.fixed_hw = (int(ishape[2]), int(ishape[3]))   # (H, W)

    # ---- тензоры ----
    def _img_tensor(self, img, m):
        return (img * (1.0 - m[..., None])).transpose(2, 0, 1)[None].astype(np.float32)

    def _mask_tensor(self, m, c):
        return np.tile(m[None, None], (1, c, 1, 1)).astype(np.float32)

    def _run(self, img_t, m_t):
        if not self.two_input:
            x = np.concatenate([img_t[0].transpose(1, 2, 0), m_t[0].transpose(1, 2, 0)],
                               axis=2).transpose(2, 0, 1)[None].astype(np.float32)
            return self._norm_out(self.session.run(None, {self.input_names[0]: x})[0])
        c = self.mask_channels
        feed = {self.img_name: img_t, self.mask_name: m_t if m_t.shape[1] == c
                else self._mask_tensor_from(m_t, c)}
        try:
            return self._norm_out(self.session.run(None, feed)[0])
        except Exception as e:
            msg = str(e).lower()
            if "mask" in msg or "shape" in msg or "dimension" in msg:
                c2 = 3 if c == 1 else 1
                feed = {self.img_name: img_t,
                        self.mask_name: self._mask_tensor_from(m_t, c2)}
                return self._norm_out(self.session.run(None, feed)[0])
            raise

    @staticmethod
    def _norm_out(out):
        """Некоторые ONNX-экспорты LaMa отдают выход в 0..255 вместо 0..1.
        Без нормализовки clip(0,1) превращал ВСЁ в белый — «белое поле»."""
        if float(out.max()) > 2.0:
            out = out / 255.0
        return out

    def _mask_tensor_from(self, m_t, c):
        m = m_t[0, 0] if m_t.ndim == 4 else m_t
        return self._mask_tensor(m, c)

    # ---- прогон одного тайла/кропа размера fixed_hw ----
    def _infer_fixed(self, img_hw, m_hw):
        # img_hw: (H,W,3) float01 ; m_hw: (H,W) float01  — УЖЕ размера fixed_hw
        img_t = self._img_tensor(img_hw, m_hw)
        m_t = self._mask_tensor(m_hw, self.mask_channels)
        out = self._run(img_t, m_t)
        return np.clip(out[0].transpose(1, 2, 0), 0.0, 1.0)   # (H,W,3)

    def _feather(self, n, ramp):
        w = np.minimum(np.arange(n, dtype=np.float32) + 1.0,
                       (np.arange(n, dtype=np.float32) + 1.0)[::-1])
        return np.clip(w, 0.0, ramp) / max(ramp, 1.0)

    def _fixed_tiles(self, img, m):
        """fixed-512 модель в РОДНОМ разрешении: скользящие окна с фейдером.
        Окно всегда fixed_hw; сдвиг = размер minus перекрытие. Текст и штрихи
        сохраняют реальный размер — без ужатия всей рамки в 512 (мыло/размытие)."""
        fh, fw = self.fixed_hw
        H0, W0 = img.shape[:2]
        # окно модели ровно fixed_hw: доклеиваем край, если сторона меньше окна
        ph, pw = max(0, fh - H0), max(0, fw - W0)
        if ph or pw:
            img = cv2.copyMakeBorder(img, 0, ph, 0, pw, cv2.BORDER_REPLICATE)
            m = cv2.copyMakeBorder(m, 0, ph, 0, pw, cv2.BORDER_REPLICATE)
        H, W = img.shape[:2]
        oy, ox = int(fh * 0.25), int(fw * 0.25)
        sy, sx = fh - oy, fw - ox
        ys = list(range(0, max(1, H - fh + 1), sy))
        if ys[-1] + fh < H:
            ys.append(H - fh)
        xs = list(range(0, max(1, W - fw + 1), sx))
        if xs[-1] + fw < W:
            xs.append(W - fw)
        wy = self._feather(fh, oy)
        wx = self._feather(fw, ox)
        wmask = wy[:, None] * wx[None, :]
        acc = np.zeros((H, W, 3), np.float32)
        wsum = np.zeros((H, W), np.float32)
        n_done = 0
        for ty in ys:
            for tx in xs:
                mi = m[ty:ty + fh, tx:tx + fw]
                if float(mi.max()) < 0.01:
                    continue
                out_t = self._infer_fixed(img[ty:ty + fh, tx:tx + fw], mi)
                sl = (slice(ty, ty + fh), slice(tx, tx + fw))
                acc[sl] += out_t * wmask[..., None]
                wsum[sl] += wmask
                n_done += 1
        if n_done == 0:
            return img[:H0, :W0].copy()
        res = np.where(wsum[..., None] > 1e-6, acc / np.maximum(wsum, 1e-6)[..., None], img)
        return np.clip(res[:H0, :W0], 0.0, 1.0)

    def __call__(self, bgr, mask, pad_mod=8, max_side=1600):
        h, w = bgr.shape[:2]
        m_full = (mask > 127).astype(np.float32)
        img_full = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB).astype(np.float32) / 255.0

        # ---------- режим ФИКСИРОВАННОГО входа: crop рамки ----------
        if self.fixed_hw is not None:
            fh, fw = self.fixed_hw
            ys, xs = np.where(mask > 0)
            if len(xs) == 0:
                return bgr.copy()

            y0, y1 = int(ys.min()), int(ys.max()) + 1
            x0, x1 = int(xs.min()), int(xs.max()) + 1

            # запас контекста вокруг рамки (но в пределах картинки)
            span = max(y1 - y0, x1 - x0)
            pad = max(24, int(0.15 * span))
            y0c, y1c = max(0, y0 - pad), min(h, y1 + pad)
            x0c, x1c = max(0, x0 - pad), min(w, x1 + pad)

            crop_img = img_full[y0c:y1c, x0c:x1c]
            crop_m = m_full[y0c:y1c, x0c:x1c]
            ch, cw = crop_img.shape[:2]

            if ch > fh or cw > fw:
                # Рамка крупнее окна модели: tiled-режим в родном разрешении.
                # Чуть жирнее маска — чище снимаются края чернил.
                crop_m = np.clip(cv2.dilate(crop_m, np.ones((3, 3), np.float32),
                                            iterations=1), 0.0, 1.0)
                out_crop_f = self._fixed_tiles(crop_img, crop_m)
                out_crop = (out_crop_f * 255.0 + 0.5).astype(np.uint8)
            else:
                down = (ch > fh) or (cw > fw)
                inter = cv2.INTER_AREA if down else cv2.INTER_LINEAR
                img_r = cv2.resize(crop_img, (fw, fh), interpolation=inter)
                m_r = cv2.resize(crop_m, (fw, fh), interpolation=cv2.INTER_LINEAR)

                # чуть жирнее маска в масштабе модели — чище дорисует края чернил
                m_r = np.clip(cv2.dilate(m_r, np.ones((3, 3), np.float32),
                                         iterations=2), 0.0, 1.0)

                out_r = self._infer_fixed(img_r, m_r)                       # (fh,fw,3)
                out_crop = (cv2.resize(out_r, (cw, ch),
                                       interpolation=cv2.INTER_LANCZOS4) * 255.0 + 0.5
                            ).astype(np.uint8)
            out_crop = cv2.cvtColor(out_crop, cv2.COLOR_RGB2BGR)

            result = bgr.copy()
            result[y0c:y1c, x0c:x1c] = out_crop
            return result

        # ---------- режим ДИНАМИЧЕСКОГО входа: кроп вокруг маски ----------
        # Раньше подавали всю страницу, ужатую до max_side: на сканах 2500+px
        # объект становился мелким и модель дорисовывала светлые пятна
        # («белое поле»). Теперь, как в fixed-режиме: кроп с контекстом,
        # сжатие только если сам кроп не влезает в max_side.
        x0c, y0c, x1c, y1c = crop_mask_bbox((h, w), (mask > 127).astype(np.uint8) * 255)
        m = m_full[y0c:y1c, x0c:x1c]
        img = img_full[y0c:y1c, x0c:x1c]
        ch, cw = img.shape[:2]
        scale = min(1.0, max_side / float(max(ch, cw)))
        if scale < 1.0:
            nh, nw = max(1, int(ch * scale)), max(1, int(cw * scale))
            img = cv2.resize(img, (nw, nh), interpolation=cv2.INTER_AREA)
            m = cv2.resize(m, (nw, nh), interpolation=cv2.INTER_AREA)

        H, W = img.shape[:2]
        ph = (pad_mod - H % pad_mod) % pad_mod
        pw = (pad_mod - W % pad_mod) % pad_mod
        img = np.pad(img, ((0, ph), (0, pw), (0, 0)), "reflect")
        m = np.pad(m, ((0, ph), (0, pw)), "reflect")

        img_t = self._img_tensor(img, m)
        m_t = self._mask_tensor(m, self.mask_channels)
        out = self._run(img_t, m_t)

        out = np.clip(out[0].transpose(1, 2, 0), 0.0, 1.0)
        out = (out * 255.0 + 0.5).astype(np.uint8)[:H, :W]
        if scale < 1.0:
            out = cv2.resize(out, (cw, ch), interpolation=cv2.INTER_LANCZOS4)
        out = cv2.cvtColor(out, cv2.COLOR_RGB2BGR)
        result = bgr.copy()
        result[y0c:y1c, x0c:x1c] = out
        return result


def find_lama_model():
    cands = []
    if getattr(sys, "frozen", False):
        exedir = os.path.dirname(sys.executable)
        # 1) внешняя папка рядом с exe (можно вынести/подменить модель), 2) рядом с exe,
        # 3) внутри сборки (PyInstaller 6.x кладёт add-data в _internal == sys._MEIPASS)
        cands.append(os.path.join(exedir, "models", "lama.onnx"))
        cands.append(os.path.join(exedir, "lama.onnx"))
        meip = getattr(sys, "_MEIPASS", None)
        if meip:
            cands.append(os.path.join(meip, "models", "lama.onnx"))
            cands.append(os.path.join(meip, "lama.onnx"))
    else:
        base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        cands.append(os.path.join(base, "models", "lama.onnx"))
        cands.append(os.path.join(base, "lama.onnx"))
    for c in cands:
        if os.path.exists(c):
            return c
    return None