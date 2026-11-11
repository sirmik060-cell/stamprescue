# tools/gen_splash_music_v2.py — мелодия v1 + саб-слой (прогрев низов).
# Тот же Karplus-Strong мотив; поверх — «псевдо-бас»: основной тон + 2-я/3-я
# гармоники (эффект отсутствующего основного тона: слышно и на мелких
# динамиках ноутбука). Гармония по корням мотивa: Em → G → C → G → Em.
# ВНИМАНИЕ: это ПРЕДПРОСМОТР, пишет assets/splash_bass_v2.wav,
# боец (heartbeat-точки) намеренно НЕ добавлен — ждём решения пользователя.
import math
import os
import wave

import numpy as np

FS = 44100
EIGHTH = 60.0 / 132 / 2  # 132 bpm


def midi_f(m):
    return 440.0 * 2 ** ((m - 69) / 12)


def ks_note(freq, dur_s, vel=0.9, tau=1.2, detune=0.0):
    f = freq * (1.0 + detune)
    n = int(FS * dur_s)
    d = max(2, int(round(FS / f)))
    g = math.exp(-1.0 / (FS * tau))
    rng = np.random.default_rng(int(freq * 97) % (2**31))
    buf = rng.uniform(-1.0, 1.0, d)
    buf = np.convolve(buf, np.ones(3) / 3.0, mode="same")
    out = np.empty(n)
    for i in range(n):
        prev = buf[i % d]
        nxt = buf[(i + 1) % d]
        v = g * 0.5 * (prev + nxt)
        buf[i % d] = v
        out[i] = v
    a = max(1, int(0.002 * FS))
    out[:a] *= np.linspace(0, 1, a)
    return out * vel


def sub_note(freq, dur_s, vel=0.5, tau=1.6):
    """Псевдо-бас: f + 0.5*f2 + 0.22*f3, эксп. огибающая, атака 8 мс."""
    n = int(FS * dur_s)
    t = np.arange(n) / FS
    env = np.minimum(1.0, t / 0.008) * np.exp(-t / tau)
    w = (np.sin(2 * np.pi * freq * t)
         + 0.5 * np.sin(4 * np.pi * freq * t)
         + 0.22 * np.sin(6 * np.pi * freq * t))
    return w * env * vel


def place(L, R, sig, t0, vel=1.0):
    e = min(len(L), t0 + len(sig))
    if e > t0:
        L[t0:e] += sig[:e - t0] * vel
        R[t0:e] += sig[:e - t0] * vel


def main():
    ev = [
        (0, 64, 1.0, 0.85), (1, 67, 1.0, 0.80), (2, 71, 1.0, 0.85),
        (3, 76, 2.0, 1.00), (5, 74, 1.0, 0.80), (6, 71, 1.0, 0.75),
        (7, 67, 2.0, 0.85), (9, 69, 1.0, 0.80), (10, 71, 1.0, 0.80),
        (11, 72, 2.0, 0.90), (13, 71, 1.0, 0.75), (14, 69, 1.0, 0.70),
        (15, 67, 2.0, 0.80), (17, 64, 2.0, 0.85),
    ]
    bass = [
        # (старт в восьмых, midi корня, длительность в восьмых, громкость)
        (0, 40, 3.5, 0.60),   # E2 — тоника Em
        (7, 43, 2.0, 0.50),   # G2
        (11, 36, 2.0, 0.55),  # C2
        (15, 43, 1.5, 0.45),  # G2
        (17, 40, 4.0, 0.60),  # E2 — уход в тон
    ]
    total = int(FS * 5.5)
    L = np.zeros(total)
    R = np.zeros(total)
    # саб-слой пишем ПЕРВЫМ, чтобы гитара осталась читаемой поверх
    for st, m, dl, v in bass:
        t0 = int(st * EIGHTH * FS)
        sig = sub_note(midi_f(m), dl * EIGHTH + 0.3, v, tau=1.8)
        for ch, gch in ((L, 1.0), (R, 1.0)):
            e = min(total, t0 + len(sig))
            if e > t0:
                ch[t0:e] += sig[:e - t0] * gch
    for st, m, dl, v in ev:
        t0 = int(st * EIGHTH * FS)
        note = ks_note(midi_f(m), dl * EIGHTH + 0.25, v, tau=1.3)
        pan = 0.10 * math.sin(m / 5.0)
        for ch, gch in ((L, 1 - pan), (R, 1 + pan)):
            e = min(total, t0 + len(note))
            if e > t0:
                ch[t0:e] += note[:e - t0] * gch
    # финальный боец Em + поддерживающий саб E2
    chord = [52, 59, 64, 67, 71, 76]
    t0 = int(19 * EIGHTH * FS)
    for k, m in enumerate(chord):
        off = int((k * 0.018) * FS)
        note = ks_note(midi_f(m), 2.6, 0.62 - 0.03 * k, tau=2.8,
                       detune=0.0012 * (k % 3 - 1))
        pan = -0.25 + 0.5 * k / (len(chord) - 1)
        for ch, gch in ((L, 1 - pan), (R, 1 + pan)):
            e = min(total, t0 + off + len(note))
            if e > t0 + off:
                ch[t0 + off:e] += note[:e - t0 - off] * gch
    place(L, R, sub_note(midi_f(40), 1.6, 0.35, tau=2.5), t0)

    fade = np.ones(total)
    f0 = int(4.9 * FS)
    fade[f0:] = np.linspace(1, 0, total - f0)
    L, R = L * fade, R * fade
    peak = max(abs(L).max(), abs(R).max())
    k = 0.80 * 32767 / peak
    L, R = L * k, R * k
    # лёгкий мягкий лимитер — тёплый «песок» вместо жёсткой нарезки
    L = np.tanh(1.15 * L / 32767) / math.tanh(1.15) * 32767
    R = np.tanh(1.15 * R / 32767) / math.tanh(1.15) * 32767
    data = np.empty(total * 2, dtype=np.int16)
    data[0::2] = np.clip(L, -32767, 32767).astype(np.int16)
    data[1::2] = np.clip(R, -32767, 32767).astype(np.int16)
    out = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                       "assets", "splash_bass_v2.wav")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with wave.open(out, "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(FS)
        w.writeframes(data.tobytes())
    print("OK", out, f"{total / FS:.2f} s")
    # спектральная самопроверка: энергия <120 Гц относительно всего сигнала
    sp = np.abs(np.fft.rfft((data[0::2] + data[1::2]) / 2.0))
    fr = np.fft.rfftfreq(len(data) // 2 + 1, 1 / FS)
    lo = (fr < 120).sum() and sp[fr < 120].sum() / sp.sum()
    print(f"low-freq share (<120Hz): {lo:.3f}")


if __name__ == "__main__":
    main()
