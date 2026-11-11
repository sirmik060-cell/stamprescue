# tools/gen_splash_music.py — генерация assets/splash.wav: щипковая гитара
# (алгоритм Karplus-Strong), авторский мотив ~5 с. Ритмика «прыгучего»
# восходящего арпеджио (вайб Nokia-труна), интервалы свои — не копия.
import math
import os
import wave

import numpy as np

FS = 44100
EIGHTH = 60.0 / 132 / 2  # темп 132 bpm, восьмая = 0.227 c


def midi_f(m):
    return 440.0 * 2 ** ((m - 69) / 12)


def ks_note(freq, dur_s, vel=0.9, tau=1.2, detune=0.0):
    """Karplus-Strong: петля шума с FP-сглаживанием; tau — время затухания."""
    f = freq * (1.0 + detune)
    n = int(FS * dur_s)
    d = max(2, int(round(FS / f)))
    g = math.exp(-1.0 / (FS * tau))  # усиление петли -> экспонат. затухание
    rng = np.random.default_rng(int(freq * 97) % (2**31))
    buf = rng.uniform(-1.0, 1.0, d)
    # приглушить атаку: однократное сглаживание старта
    buf = np.convolve(buf, np.ones(3) / 3.0, mode="same")
    out = np.empty(n)
    for i in range(n):
        prev = buf[i % d]
        nxt = buf[(i + 1) % d]
        v = g * 0.5 * (prev + nxt)
        buf[i % d] = v
        out[i] = v
    # естественная огибающая атаки (2 мс)
    a = max(1, int(0.002 * FS))
    out[:a] *= np.linspace(0, 1, a)
    return out * vel


def main():
    ev = [
        # (старт в восьмых, midi, длительность в восьмых, громкость)
        (0, 64, 1.0, 0.85), (1, 67, 1.0, 0.80), (2, 71, 1.0, 0.85),
        (3, 76, 2.0, 1.00), (5, 74, 1.0, 0.80), (6, 71, 1.0, 0.75),
        (7, 67, 2.0, 0.85), (9, 69, 1.0, 0.80), (10, 71, 1.0, 0.80),
        (11, 72, 2.0, 0.90), (13, 71, 1.0, 0.75), (14, 69, 1.0, 0.70),
        (15, 67, 2.0, 0.80), (17, 64, 2.0, 0.85),
    ]
    total = int(FS * 5.5)
    L = np.zeros(total)
    R = np.zeros(total)
    for st, m, dl, v in ev:
        t0 = int(st * EIGHTH * FS)
        note = ks_note(midi_f(m), dl * EIGHTH + 0.25, v, tau=1.3)
        pan = 0.10 * math.sin(m / 5.0)  # лёгкое чередование стерео
        for ch, gch in ((L, 1 - pan), (R, 1 + pan)):
            e = min(total, t0 + len(note))
            if e > t0:
                ch[t0:e] += note[:e - t0] * gch
    # финальный боец Em (щипок снизу вверх, раскид по стерео)
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
    # мастер: фейд-аут 4.9..5.4 c, нормировка
    fade = np.ones(total)
    f0 = int(4.9 * FS)
    fade[f0:] = np.linspace(1, 0, total - f0)
    L, R = L * fade, R * fade
    peak = max(abs(L).max(), abs(R).max())
    k = 0.89 * 32767 / peak
    data = np.empty(total * 2, dtype=np.int16)
    data[0::2] = np.clip(L * k, -32767, 32767).astype(np.int16)
    data[1::2] = np.clip(R * k, -32767, 32767).astype(np.int16)
    out = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                       "assets", "splash.wav")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with wave.open(out, "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(FS)
        w.writeframes(data.tobytes())
    print("OK", out, f"{total / FS:.2f} s")
    # самопроверка: старты энергии по 50-мс окнам должны совпасть с сеткой
    env = np.abs(data.astype(np.float64)[:total * 2:2]).reshape(-1, 2205).max(axis=1)
    ons = [i * 0.05 for i in range(1, len(env)) if env[i] > 3 * env[i - 1] + 200]
    print("onsets(s):", [round(o, 2) for o in ons][:20])


if __name__ == "__main__":
    main()
