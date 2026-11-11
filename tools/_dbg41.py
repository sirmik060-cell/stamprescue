# tools/_dbg41.py — объективная проверка: дуговой/центральный текст не пересекает кольца
import sys, os, json
import numpy as np
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from stamp_builder import render_stamp

root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
pd = os.path.join(root, "presets")
fail = False
for fn in sorted(os.listdir(pd)):
    if not fn.endswith(".json") or fn == "jenti_example.json":
        continue
    spec = json.load(open(os.path.join(pd, fn), encoding="utf-8"))
    ring_layers = [L for L in spec["layers"] if L["type"] in ("ring", "band", "pic_frame")]
    mR = None
    if ring_layers:
        mR = np.asarray(render_stamp({**spec, "layers": ring_layers}).split()[3]) > 128
    bad = []
    for L in spec["layers"]:
        if L["type"] not in ("arc_text", "center_text"):
            continue
        mT = np.asarray(render_stamp({**spec, "layers": [L]}).split()[3]) > 128
        if mR is not None:
            ov = int(np.logical_and(mT, mR).sum())
            if ov > 20:
                bad.append((L["type"], str(L.get("text", L.get("lines")))[:24], ov))
    print(fn, "->", "CLEAN" if not bad else bad)
    fail = fail or bool(bad)
sys.exit(1 if fail else 0)
