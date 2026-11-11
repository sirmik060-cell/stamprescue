# diag_times.py — проверка times.ttf и засечек C при noise 0 vs 15
import os, copy
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
import numpy as np
from PIL import Image, ImageChops
import stamp_builder as sb

fd = sb.FONT_DIR
for f in ("times.ttf", "timesbd.ttf", "arial.ttf"):
    print(f, "exists:", os.path.exists(os.path.join(fd, f)))
print("get_font('Times') path:", sb.get_font("Times", 75).path)
print("get_font('Times New Roman') path:", sb.get_font("Times New Roman", 75).path)

base = sb.default_spec()
print("demo arc#2:", [(L.get("text"), L.get("font")) for L in base["layers"] if L["type"] == "arc_text"])
a2 = next(L for L in base["layers"] if L["type"] == "arc_text" and L.get("text") == "Ratooc")

def arc_only(noise, font):
    s = copy.deepcopy(base)
    s["layers"] = [L for L in s["layers"] if L["type"] == "arc_text"]
    for L in s["layers"]:
        if L.get("text") != "Ratooc":
            s["layers"].remove(L)
    s["noise_pct"] = noise
    a = next(L for L in s["layers"] if L.get("text") == "Ratooc")
    a["font"] = font
    return sb.render_stamp(s)

for tag, noise in (("n0", 0), ("n15", 15)):
    img = arc_only(noise, "Times New Roman")
    img.save(f"result/tests/diag_ratooc_{tag}.png")
    big = img.resize((img.width * 3, img.height * 3), Image.LANCZOS)
    big.save(f"result/tests/diag_ratooc_{tag}_3x.png")

# одиночная C крупно, Times New Roman, для эталона засечек
im = Image.new("RGB", (160, 160), (255, 255, 255))
from PIL import ImageDraw
d = ImageDraw.Draw(im)
d.text((80, 80), "C", font=sb.get_font("Times New Roman", 120), fill=(0, 0, 0), anchor="mm")
im.save("result/tests/diag_C_times.png")
im2 = Image.new("RGB", (160, 160), (255, 255, 255))
d2 = ImageDraw.Draw(im2)
d2.text((80, 80), "C", font=sb.get_font("Arial", 120), fill=(0, 0, 0), anchor="mm")
im2.save("result/tests/diag_C_arial.png")
diff = ImageChops.difference(arc_only(0, "Times New Roman"), arc_only(15, "Times New Roman"))
print("pixel diff n0 vs n15 bbox:", diff.getbbox())
print("saved diag_ratooc_n0/n15(_3x), diag_C_times, diag_C_arial")
