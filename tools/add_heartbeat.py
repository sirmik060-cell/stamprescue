# tools/add_heartbeat.py — второй слой: «точки сердца» поверх готового
# assets/splash.wav (второй низкий удар с коротким интервалом, «туп-туп»
# с понижением высоты, как приглушённый бочкой). Пишет splash_heart_v3.wav —
# ПРЕДПРОСМОТР; боец на месте ~4.30/4.58 c, до фейда.
import math
import os
import wave

import numpy as np

FS = 44100
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def thump(f0=62.0, f1=42.0, dur=0.34, vel=0.42):
    """Приглушённый «туп»: синус со свипом высоты вниз, быстрая атака,
    короткий эксп. спад + чуть шума самой атаки (щелчок кожи)."""
    n = int(FS * dur)
    t = np.arange(n) / FS
    f = f0 + (f1 - f0) * (1 - np.exp(-t / 0.05))
    phase = 2 * np.pi * np.cumsum(f) / FS
    env = np.minimum(1.0, t / 0.004) * np.exp(-t / 0.11)
    sig = np.sin(phase) * env * vel
    a = int(0.012 * FS)
    rng = np.random.default_rng(7)
    sig[:a] += rng.uniform(-0.25, 0.25, a) * np.exp(-t[:a] / 0.006) * vel
    return sig


def main():
    src = os.path.join(HERE, "assets", "splash.wav")
    with wave.open(src, "rb") as w:
        n = w.getnframes()
        d = np.frombuffer(w.readframes(n), dtype=np.int16).astype(np.float64)
        framerate = w.getframerate()
    assert framerate == FS and w.getnchannels() == 2
    L = d[0::2]
    R = d[1::2]
    for pos, vel in ((4.30, 0.30), (4.58, 0.40)):  # «тУП-туп», второй сильнее
        sig = thump(vel=vel)
        t0 = int(pos * FS)
        e = min(len(L), t0 + len(sig))
        L[t0:e] += sig[:e - t0]
        R[t0:e] += sig[:e - t0] * 0.92  # чуть вправо
    peak = max(abs(L).max(), abs(R).max())
    k = 0.89 * 32767 / peak if peak > 0.89 * 32767 else 1.0  # не трогаем микс, если не кликует
    L, R = L * k, R * k
    out = os.path.join(HERE, "assets", "splash_heart_v3.wav")
    data = np.empty(len(L) * 2, dtype=np.int16)
    data[0::2] = np.clip(L, -32767, 32767).astype(np.int16)
    data[1::2] = np.clip(R, -32767, 32767).astype(np.int16)
    with wave.open(out, "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(FS)
        w.writeframes(data.tobytes())
    print("OK", out, f"{len(L) / FS:.2f} s, rescale={k:.3f}")


if __name__ == "__main__":
    main()
