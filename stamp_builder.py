# stamp_builder.py — v3.7: построчный редактор центра переработан: на строку — шрифт,
# жирность, цвет, кегль, сдвиг X/Y и растяжка шир./выс. симв. в %; «Шрифт со слоя» ->
# «Шрифт», «жирн. со слоя» -> «Жирность» (первый пункт = значения слоя); кнопка «Шрифт из Скана»
import math
import os
import sys
import json
import bisect
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from PySide6.QtCore import Qt, QPointF
from PySide6.QtGui import QImage, QPixmap, QColor, QFont, QPainter, QPen, QPolygonF, QIcon
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLabel, QComboBox, QDoubleSpinBox, QSpinBox, QLineEdit, QCheckBox,
    QPushButton, QListWidget, QFileDialog, QColorDialog, QScrollArea,
    QWidget, QPlainTextEdit, QSplitter, QMenu, QSizePolicy)
from font_matcher import FontMatchDialog

FONT_DIR = "C:\\Windows\\Fonts"
FONT_MAP = {
 "Arial": ("arial.ttf","arialbd.ttf"), "Arial Black": ("ariblk.ttf","ariblk.ttf"),
 "Times New Roman": ("times.ttf","timesbd.ttf"), "Times": ("times.ttf","timesbd.ttf"),
 "Calibri": ("calibri.ttf","calibrib.ttf"),
 "Calibri Light": ("calibril.ttf","calibril.ttf"), "Cambria": ("cambria.ttc","cambriab.ttc"),
 "Candara": ("candara.ttf","candarab.ttf"), "Corbel": ("corbel.ttf","corbelb.ttf"),
 "Consolas": ("consola.ttf","consolab.ttf"), "Courier New": ("cour.ttf","courbd.ttf"),
 "Comic Sans MS": ("comic.ttf","comicbd.ttf"), "Georgia": ("georgia.ttf","georgiab.ttf"),
 "Impact": ("impact.ttf","impact.ttf"), "Lucida Console": ("lucon.ttf","lucon.ttf"),
 "Segoe UI": ("segoeui.ttf","segoeuib.ttf"), "Segoe Print": ("segoepr.ttf","segoepr.ttf"),
 "Tahoma": ("tahoma.ttf","tahoma.ttf"), "Trebuchet MS": ("trebuc.ttf","trebucbd.ttf"),
 "Verdana": ("verdana.ttf","verdanab.ttf"), "Bahnschrift": ("bahnschrift.ttf","bahnschrift.ttf"),
}
# «Times» убран из меню: это тот же times.ttf, что и «Times New Roman» (дубль путал пользователя);
# ключ в FONT_MAP оставлен для старых пресетов.
FONT_NAMES = [k for k in FONT_MAP if k != "Times"]
LABELS = {"text":"Текст","pos":"Позиция","attract":"Притяжение",
 "inset_mm":"Радиус: отступ от края, мм","vshift_mm":"Тонкий сдвиг, мм",
 "auto_band":"Выровнять по центру ленты","w_pct":"Ширина симв., %","h_pct":"Высота симв., %",
 "size_mm":"Кегль, мм","spacing_mm":"Интервал, мм","font":"Шрифт","bold":"Жирный","flip":"Инверсия",
 "color":"Цвет","thickness_mm":"Толщина, мм","inset_out_mm":"Внешн. отступ, мм",
 "inset_in_mm":"Внутр. отступ, мм","lines":"Строки","plate_on":"Подложка","plate_pad_mm":"Поле подложки, мм",
 "plate_color":"Цвет подложки","path":"Файл","height_mm":"Высота, мм","dx_mm":"Сдвиг X, мм","dy_mm":"Сдвиг Y, мм",
 "recolor_on":"Перекрасить","recolor":"Цвет перекраски","glyph":"Глиф","count":"Кол-во",
 "ashift_mm":"Сдвиг по дуге, мм","corner_mm":"Скругление углов, мм","align":"Выравнивание строк"}

SCHEMA = {
 "ring": [("inset_mm","mm",0,30),("thickness_mm","mm",0,5),("color","color",None,None)],
 "band": [("inset_out_mm","mm",0,30),("inset_in_mm","mm",0,30),("color","color",None,None)],
 "arc_text": [("text","text",None,None),("pos","combo",None,["top","bottom"]),
              ("attract","combo",None,["ellipse","circle","rect"]),("auto_band","check",None,None),
              ("inset_mm","mm",0,30),("vshift_mm","mm",-5,5),("ashift_mm","mm",-60,60),("size_mm","mm",0.5,12),
              ("w_pct","pct",10,200),("h_pct","pct",10,200),("spacing_mm","mm",0,3),
              ("font","combo",None,FONT_NAMES),("bold","check",None,None),("flip","check",None,None),("color","color",None,None)],
 "center_text":  [("lines","lines",None,None),("size_mm","mm",0.5,12),("spacing_mm","mm",-8,10),
                 ("align","combo",None,["center","left","right"]),
                 ("dx_mm","f",-40,40),("dy_mm","f",-40,40),
                 ("w_pct","pct",10,200),("h_pct","pct",10,200),("font","combo",None,FONT_NAMES),
                 ("bold","check",None,None),("plate_on","check",None,None),
                 ("plate_pad_mm","mm",0,10),("plate_color","color",None,None),("color","color",None,None)],
 "emblem": [("path","file",None,None),("height_mm","mm",1,60),("dx_mm","mm",-30,30),("dy_mm","mm",-30,30),
            ("recolor_on","check",None,None),("recolor","color",None,None)],
 "pic_frame": [("glyph","combo",None,["tick","hatch","dot","bar","star","ring","dash","diamond","plus"]),("count","int",4,200),
               ("inset_mm","mm",0,30),("size_mm","mm",0.2,6),("color","color",None,None)],
}

def mm2px(mm, dpi): return mm / 25.4 * dpi

def parse_runs(text, base):
    """Текст со стилевыми тегами {..} -> [(фрагмент, стиль)]. Тег действует до следующего тега.
    Пример: 'ОБЫЧНО {size=4;font=Times;bold;color=200,0,0}ЖИРНО'."""
    runs=[]; st=dict(base); buf=""; i=0
    while i < len(text):
        c=text[i]
        if c=="{":
            j=text.find("}", i)
            if j<0: buf+=text[i:]; break
            if buf: runs.append((buf,st)); buf=""
            st=dict(st)
            for part in text[i+1:j].split(";"):
                part=part.strip()
                if not part: continue
                if part=="bold": st["bold"]=True
                elif part=="!bold": st["bold"]=False
                elif "=" in part:
                    k,v=part.split("=",1); k=k.strip().lower(); v=v.strip()
                    try:
                        if k in ("font","f"): st["font"]=v
                        elif k in ("size","kegel"): st["size_mm"]=float(v)
                        elif k=="w": st["w_pct"]=float(v)
                        elif k=="h": st["h_pct"]=float(v)
                        elif k=="dx": st["dx"]=float(v)
                        elif k=="dy": st["dy"]=float(v)
                        elif k=="align" and v in ("left","center","right"): st["align"]=v
                        elif k=="color": st["color"]=tuple(max(0,min(255,int(float(x)))) for x in v.split(","))[:3]
                    except ValueError: pass
            i=j+1; continue
        buf+=c; i+=1
    runs.append((buf,st))   # пустой прогон в конце ловит висячий тег без текста после
    return runs

def _rect_cycle(cx, cy, A, B, r):
    """Обод прямоуг. со скруглением r; старт — середина верхней стороны, обход по часовой (углы в радианах)."""
    r = max(0.0, min(r, A*0.9, B*0.9))
    x0,x1,yt,yb = cx-A, cx+A, cy-B, cy+B
    pts=[(cx, yt, 0.0)]
    def edge(xa,ya,xb,yb2,a): pts.extend([(xa,ya,a),(xb,yb2,a)])
    def arc(ccx,ccy,t0,t1):
        steps=max(2,int(abs(t1-t0)/5))
        for i in range(steps+1):
            th=math.radians(t0+(t1-t0)*i/steps)
            pts.append((ccx+r*math.cos(th), ccy+r*math.sin(th), th+math.pi/2))
    edge(cx,yt, x1-r,yt, 0.0)
    arc(x1-r,yt+r, -90, 0)
    edge(x1,yt+r, x1,yb-r, math.radians(90))
    arc(x1-r,yb-r, 0, 90)
    edge(x1-r,yb, x0+r,yb, math.radians(180))
    arc(x0+r,yb-r, 90, 180)
    edge(x0,yb-r, x0,yt+r, math.radians(270))
    arc(x0+r,yt+r, 180, 270)
    pts.append((cx,yt,0.0))
    return pts

def _path_at(pts):
    cs=[0.0]
    for i in range(1,len(pts)):
        cs.append(cs[-1]+math.hypot(pts[i][0]-pts[i-1][0], pts[i][1]-pts[i-1][1]))
    per=cs[-1]; Lp=len(pts)
    def at(s):
        if per<=0: return pts[0]
        s%=per
        lo,hi=0,Lp-1
        while hi-lo>1:
            mid=(lo+hi)//2
            if cs[mid]<=s: lo=mid
            else: hi=mid
        x1,y1,a1=pts[lo]; x2,y2,a2=pts[hi]
        seg=cs[hi]-cs[lo]; k=0.0 if seg<=0 else (s-cs[lo])/seg
        da=a2-a1
        if da>math.pi: da-=2*math.pi
        if da<-math.pi: da+=2*math.pi
        return (x1+(x2-x1)*k, y1+(y2-y1)*k, a1+da*k)
    return at, per

def _paste_char(img, ch, st, nw, hpx, wf, x, y, R):
    gh=int(hpx*2+16)
    g=Image.new("RGBA",(int(nw+12),gh),(0,0,0,0)); gd=ImageDraw.Draw(g)
    gd.text((g.size[0]/2,g.size[1]/2),ch,font=get_font(st["font"],hpx,st["bold"]),
            fill=tuple(st["color"])+(255,),anchor="mm")
    if wf!=1.0: g=g.resize((max(1,int(g.size[0]*wf)),gh),Image.LANCZOS)
    g=g.rotate(-R,expand=True,resample=Image.BICUBIC)
    img.alpha_composite(g,(int(x-g.size[0]/2),int(y-g.size[1]/2)))

def get_font(family, size_px, bold=False):
    key = str(family or "").strip()
    pair = FONT_MAP.get(key) or {k.lower(): v for k, v in FONT_MAP.items()}.get(key.lower()) \
        or {k.lower(): v for k, v in FONT_MAP.items()}.get(key.lower().replace(" nr", " new roman"))
    f, b = pair or ("arial.ttf", "arialbd.ttf")
    path = os.path.join(FONT_DIR, b if bold else f)
    if not os.path.exists(path): path = os.path.join(FONT_DIR, f)
    try: return ImageFont.truetype(path, max(6, int(size_px)))
    except Exception: return ImageFont.load_default()

def _builtin_glyph(kind, s, color):
    s = max(4, int(s)); im = Image.new("RGBA", (s, s), (0,0,0,0)); d = ImageDraw.Draw(im)
    c = tuple(color)+(255,)
    if kind=="tick": d.rectangle([s*0.35,0,s*0.65,s], fill=c)
    elif kind=="hatch": d.line([(0,s),(s,0)], fill=c, width=max(1,s//4))
    elif kind=="dot": d.ellipse([s*0.15,s*0.15,s*0.85,s*0.85], fill=c)
    elif kind=="bar": d.rectangle([0,s*0.3,s,s*0.7], fill=c)
    elif kind=="star":
        import math as _m
        pts = []
        for k in range(10):  # пятиконечная (канонична для печатей), был неправильный 4-лучевой полигон
            r_ = s*0.48 if k % 2 == 0 else s*0.20
            aa = _m.pi/2 + k*_m.pi/5
            pts.append((s/2 + r_*_m.cos(aa), s/2 - r_*_m.sin(aa)))
        d.polygon(pts, fill=c)
    elif kind=="ring": d.ellipse([s*0.1,s*0.1,s*0.9,s*0.9], outline=c, width=max(1,s//6))
    elif kind=="dash": d.rectangle([s*0.05,s*0.40,s*0.95,s*0.60], fill=c)
    elif kind=="diamond": d.polygon([(s/2,s*0.05),(s*0.95,s/2),(s/2,s*0.95),(s*0.05,s/2)], fill=c)
    elif kind=="plus":
        d.rectangle([s*0.40,s*0.05,s*0.60,s*0.95], fill=c)
        d.rectangle([s*0.05,s*0.40,s*0.95,s*0.60], fill=c)
    return im

GLYPH_NAMES = {"tick":"tick (штрих)","hatch":"hatch (наклон)","dot":"dot (точка)",
    "bar":"bar (полоса)","star":"star (звезда)","ring":"ring (кольцо)",
    "dash":"dash (пунктир)","diamond":"diamond (ромб)","plus":"plus (крест)"}

def _band_mid_inset(spec):
    for B in spec["layers"]:
        if B["type"]=="band":
            return (B.get("inset_out_mm",0)+B.get("inset_in_mm",0))/2.0
    return 1.2

def _apply_ink_noise(img, amount, seed=7):
    if amount <= 0: return img
    rng = np.random.default_rng(seed)
    w, h = img.size
    hw, hh = max(2, w//2), max(2, h//2)
    small = rng.normal(0, 1, (hh, hw))
    small = (small - small.min()) / (small.max() - small.min() + 1e-9)
    nimg = Image.fromarray((small*255).astype(np.uint8)).resize((w, h), Image.LANCZOS)
    n = np.array(nimg).astype(np.float32)/255.0
    arr = np.array(img)
    a = arr[...,3].astype(np.float32)/255.0
    a = a * (1 - (amount/100.0)*0.6*n)
    arr[...,3] = np.clip(a*255, 0, 255).astype(np.uint8)
    return Image.fromarray(arr)

def render_stamp(spec):
    dpi = spec["dpi"]
    W = mm2px(spec["width_mm"], dpi); H = mm2px(spec["height_mm"], dpi)
    m = mm2px(3, dpi)
    img = Image.new("RGBA", (int(W+2*m), int(H+2*m)), (0,0,0,0))
    cx, cy = img.size[0]/2, img.size[1]/2
    rx = W/2; ry = H/2
    if spec["form"]=="circle": rx = ry = max(rx, ry)
    for L in spec["layers"]:
        t = L["type"]
        if t=="ring": _ring(img, spec, L, cx, cy, rx, ry)
        elif t=="band": _band(img, spec, L, cx, cy, rx, ry)
        elif t=="arc_text": _arc_text(img, spec, L, cx, cy, rx, ry)
        elif t=="center_text": _center_text(img, spec, L, cx, cy)
        elif t=="emblem": _emblem(img, spec, L, cx, cy)
        elif t=="pic_frame": _pic_frame(img, spec, L, cx, cy, rx, ry)
    img = _apply_ink_noise(img, spec.get("noise", 0))
    rot = spec.get("rotation_deg", 0)
    if rot: img = img.rotate(-rot, expand=True, resample=Image.BICUBIC)
    return img

def _bbox(cx, cy, rx, ry, ins): return [cx-rx+ins, cy-ry+ins, cx+rx-ins, cy+ry-ins]

def _ring(img, spec, L, cx, cy, rx, ry):
    t_mm = L.get("thickness_mm", 0.4)
    if t_mm <= 0: return
    d = ImageDraw.Draw(img); ins = mm2px(L.get("inset_mm", 1.0), spec["dpi"])
    t = max(1, int(mm2px(t_mm, spec["dpi"])))
    col = tuple(L.get("color", (35, 60, 170))) + (255,)
    cr = mm2px(spec.get("corner_mm", 0), spec["dpi"])
    if spec["form"]=="rect":
        if cr>0.5: d.rounded_rectangle(_bbox(cx,cy,rx,ry,ins), radius=cr, outline=col, width=t)
        else: d.rectangle(_bbox(cx,cy,rx,ry,ins), outline=col, width=t)
    else: d.ellipse(_bbox(cx,cy,rx,ry,ins), outline=col, width=t)

def _band(img, spec, L, cx, cy, rx, ry):
    ins_o = mm2px(L.get("inset_out_mm", 0.0), spec["dpi"]); ins_i = mm2px(L.get("inset_in_mm", 2.5), spec["dpi"])
    if ins_i <= ins_o: return
    mask = Image.new("L", img.size, 0); d = ImageDraw.Draw(mask)
    cr = mm2px(spec.get("corner_mm", 0), spec["dpi"])
    if spec["form"]=="rect" and cr>0.5:
        d.rounded_rectangle(_bbox(cx,cy,rx,ry,ins_o), radius=cr, fill=255)
        d.rounded_rectangle(_bbox(cx,cy,rx,ry,ins_i), radius=max(0.0,cr-(ins_i-ins_o)), fill=0)
    else:
        d.rectangle(_bbox(cx,cy,rx,ry,ins_o), fill=255); d.rectangle(_bbox(cx,cy,rx,ry,ins_i), fill=0)
    img.paste(Image.new("RGBA", img.size, tuple(L.get("color", (35, 60, 170))) + (255,)), (0, 0), mask)

def _arc_text(img, spec, L, cx, cy, rx, ry):
    """Текст по эллипсу/кругу/прямоугольному обводу, ПАРАЛЛЕЛЬНО кольцам (между ними).
    attract=rect — строго по периметру прямоугольника (с учётом скругления углов).
    Стили: внутри текста теги {size=..;font=..;bold;color=r,g,b;w=..;h=..} до след. тега.
    ashift_mm — сдвиг вдоль дуги в обе стороны (можно влево)."""
    dpi = spec["dpi"]
    if L.get("auto_band"): ins_mm = _band_mid_inset(spec)
    else: ins_mm = L.get("inset_mm", 1.0)
    ins = mm2px(ins_mm + L.get("vshift_mm", 0), dpi)
    A = max(2.0, rx - ins); B = max(2.0, ry - ins)
    att = L.get("attract","ellipse"); top = L.get("pos","top")=="top"
    base = {"size_mm":L.get("size_mm",2.5),"w_pct":L.get("w_pct",100),"h_pct":L.get("h_pct",100),
            "font":L.get("font","Arial"),"bold":bool(L.get("bold")),
            "color":tuple(L.get("color", (35, 60, 170)))}
    chars=[]; sts=[]
    for txt,st in parse_runs(L.get("text",""), base):
        for ch in txt: chars.append(ch); sts.append(st)
    if not chars: return
    sp = mm2px(L.get("spacing_mm",0.2), dpi)
    adv=[]; nws=[]; hpxs=[]; wfacs=[]
    for ch,st in zip(chars,sts):
        hpx = mm2px(st["size_mm"], dpi)*st["h_pct"]/100.0; wf=st["w_pct"]/100.0
        f = get_font(st["font"], hpx, st["bold"])
        try: nw=f.getlength(ch)
        except Exception: nw=hpx*0.6
        nws.append(nw); adv.append(nw*wf+sp); hpxs.append(hpx); wfacs.append(wf)
    span=sum(adv); shift=mm2px(L.get("ashift_mm",0), dpi)
    if att=="rect":
        cyc=_rect_cycle(cx,cy,A,B,mm2px(spec.get("corner_mm",0),dpi))
        at,per=_path_at(cyc)
        s0 = 0.0 if top else per/2.0
        cur=0.0
        for ch,st,wd,nw,hpx,wf in zip(chars,sts,adv,nws,hpxs,wfacs):
            u = cur + wd/2.0 - span/2.0 + shift
            x,y,ang = at(s0 + (u if top else -u))
            R = math.degrees(ang) + (0.0 if top else 180.0)
            if L.get("flip"): R += 180
            _paste_char(img, ch, st, nw, hpx, wf, x, y, R)
            cur += wd
    else:
        if att=="circle": A2 = B2 = min(A,B)
        else: A2, B2 = A, B
        def P(t):
            return (cx+A2*math.sin(t), cy-B2*math.cos(t))   # t=0 — верх
        def tang(t):
            return math.degrees(math.atan2(B2*math.sin(t), A2*math.cos(t)))
        # буквы раскладываются по ДЛИНЕ ДУГИ (пиксели), а не по радианам;
        # таблица t∈[-2pi..2pi] покрывает периметр с запасом на переносы
        N=960; t0,t1=-2.0*math.pi, 2.0*math.pi
        ts=[t0+(t1-t0)*i/N for i in range(N+1)]
        ss=[0.0]*(N+1); acc=0.0; px,py=P(ts[0])
        for i in range(1,N+1):
            x,y=P(ts[i]); acc+=math.hypot(x-px,y-py); ss[i]=acc; px,py=x,y
        s_top=ss[N//2]    # длина дуги до центра верха (t=0)
        s_bot=ss[3*N//4]  # длина дуги до центра низа (t=pi)
        def T(s):
            s=max(ss[0],min(ss[-1],s))
            j=bisect.bisect_left(ss,s)
            if j<=0: return ts[0]
            if j>N: return ts[N]
            f=(s-ss[j-1])/(ss[j]-ss[j-1]+1e-12)
            return ts[j-1]+(ts[j]-ts[j-1])*f
        cur=0.0
        for ch,st,wd,nw,hpx,wf in zip(chars,sts,adv,nws,hpxs,wfacs):
            if top:
                t_=T(s_top + cur + wd/2.0 - span/2.0 + shift); R=tang(t_)
            else:
                t_=T(s_bot + (span/2.0 - shift) - (cur + wd/2.0)); R=tang(t_)-180.0
            if L.get("flip"): R += 180
            x,y=P(t_)
            _paste_char(img, ch, st, nw, hpx, wf, x, y, R)
            cur += wd

def _center_text(img, spec, L, cx, cy):
    """Центральный блок. Свободное размещение: dx_mm/dy_mm и align сдвигают весь блок,
    а в конце каждой строки можно дописать служебный тег {align=left|center|right;dx=..;dy=..}
    для сдвига именно этой строки. Стилистические теги {size;font;bold;color;w;h} — как обычно.
    line_styles строки также поддерживает dx_mm/dy_mm/w_pct/h_pct (поля редактора строк);
    одноимённые теги в тексте строки перекрывают поля."""
    dpi = spec["dpi"]
    base = {"size_mm":L.get("size_mm",3.0),"w_pct":L.get("w_pct",100),"h_pct":L.get("h_pct",100),
            "font":L.get("font","Arial"),"bold":bool(L.get("bold")),
            "color":tuple(L.get("color", (35, 60, 170)))}
    cx = cx + mm2px(L.get("dx_mm",0), dpi)
    cy = cy + mm2px(L.get("dy_mm",0), dpi)
    block_align = L.get("align","center")
    lines_raw = L.get("lines", [""]) or [""]
    sp = mm2px(L.get("spacing_mm", 1.0), dpi)
    rows=[]
    lstyles = L.get("line_styles") or []
    for li,s in enumerate(lines_raw):
        b2 = dict(base)
        stl = lstyles[li] if li < len(lstyles) else {}
        if stl.get("size_mm"): b2["size_mm"] = float(stl["size_mm"])
        if stl.get("font"):    b2["font"] = stl["font"]
        if "bold" in stl:      b2["bold"] = bool(stl["bold"])
        if stl.get("color"):   b2["color"] = tuple(stl["color"])
        if stl.get("w_pct"):   b2["w_pct"] = float(stl["w_pct"])
        if stl.get("h_pct"):   b2["h_pct"] = float(stl["h_pct"])
        parsed = parse_runs(s, b2)
        lalign=None
        # сдвиг строки из line_styles, мм; тег {dx/dy} в тексте перекрывает
        ldx=float(stl.get("dx_mm",0.0)); ldy=float(stl.get("dy_mm",0.0))
        for _,st in parsed:
            if "align" in st: lalign=st["align"]
            if "dx" in st: ldx=st["dx"]
            if "dy" in st: ldy=st["dy"]
        runs=[]
        for txt,st in parsed:
            if not txt: continue
            hpx = mm2px(st["size_mm"], dpi)*st["h_pct"]/100.0
            wf = st["w_pct"]/100.0
            f = get_font(st["font"], hpx, st["bold"])
            th = sum(f.getmetrics())+2   # плотная строка: интервал 0 = впритык, минус = наезд
            g = Image.new("RGBA",(int(f.getlength(txt))+8, th),(0,0,0,0))
            ImageDraw.Draw(g).text((g.size[0]/2,g.size[1]/2), txt, font=f,
                                   fill=tuple(st["color"])+(255,), anchor="mm")
            if wf!=1.0:
                g = g.resize((max(1,int(g.size[0]*wf)), th), Image.LANCZOS)
            runs.append(g)
        w = sum(g.size[0] for g in runs)
        h = max((g.size[1] for g in runs), default=int(mm2px(base["size_mm"],dpi)*1.6)+8)
        rows.append((runs,w,h,lalign or block_align,
                     mm2px(ldx,dpi), mm2px(ldy,dpi)))
    total_h = sum(r[2] for r in rows) + sp*(len(rows)-1)
    wmax = max((r[1] for r in rows), default=0)
    if L.get("plate_on"):
        pad = mm2px(L.get("plate_pad_mm",1), dpi)
        pw = wmax+2*pad; ph = total_h+2*pad
        pc = L.get("plate_color", tuple(base["color"]))
        ImageDraw.Draw(img).rounded_rectangle([cx-pw/2, cy-ph/2, cx+pw/2, cy+ph/2],
            radius=pad/2, fill=tuple(pc)+(255,))
    y = cy - total_h/2.0
    for runs,w,h,align,ldx,ldy in rows:
        if align=="left": x = cx - wmax/2.0
        elif align=="right": x = cx + wmax/2.0 - w
        else: x = cx - w/2.0
        x += ldx
        for g in runs:
            img.alpha_composite(g, (int(x), int(y + ldy + (h-g.size[1])/2.0)))
            x += g.size[0]
        y += h + sp

def _emblem(img, spec, L, cx, cy):
    p = L.get("path")
    if not p or not os.path.exists(p): return
    e = Image.open(p).convert("RGBA")
    h = mm2px(L.get("height_mm", 15.0), spec["dpi"]); k = h/e.size[1]
    e = e.resize((max(1,int(e.size[0]*k)), int(h)), Image.LANCZOS)
    if L.get("recolor_on"):
        alpha = e.convert("L").point(lambda v: 255-v)
        out = Image.new("RGBA", e.size, tuple(L.get("recolor",(0,0,255)))+(255,))
        out.putalpha(alpha); e = out
    x = int(cx+mm2px(L.get("dx_mm",0),spec["dpi"])-e.size[0]/2)
    y = int(cy+mm2px(L.get("dy_mm",0),spec["dpi"])-e.size[1]/2)
    img.alpha_composite(e, (x,y))

def _pic_frame(img, spec, L, cx, cy, rx, ry):
    dpi = spec["dpi"]; n = int(L.get("count", 60)); ins = mm2px(L.get("inset_mm", 0.5), dpi)
    g0 = _builtin_glyph(L.get("glyph","tick"), mm2px(L.get("size_mm", 1.2), dpi), L.get("color", (35, 60, 170)))
    if spec["form"]=="rect":
        w2,h2 = rx-ins, ry-ins; per = 4*(w2+h2)
        for length,R,edge in [(2*w2,0,0),(2*h2,90,1),(2*w2,180,2),(2*h2,270,3)]:
            cnt = max(1, round(n*length/per))
            for i in range(cnt):
                t=(i+0.5)/cnt
                if edge==0: x,y = cx-w2+length*t, cy-h2
                elif edge==1: x,y = cx+w2, cy-h2+length*t
                elif edge==2: x,y = cx+w2-length*t, cy+h2
                else: x,y = cx-w2, cy+h2-length*t
                g = g0.rotate(-R, expand=True, resample=Image.BICUBIC)
                img.alpha_composite(g,(int(x-g.size[0]/2),int(y-g.size[1]/2)))
    else:
        phase = math.radians(float(L.get("phase_deg", 0.0)))  # поворот раскладки глифов (звёзды-разделители слева/справа)
        for i in range(n):
            a = 2*math.pi*i/n + phase
            x = cx+(rx-ins)*math.sin(a); y = cy+(ry-ins)*math.cos(a)
            tang = math.degrees(math.atan2(ry*math.sin(a), rx*math.cos(a)))
            g = g0.rotate(-tang, expand=True, resample=Image.BICUBIC)
            img.alpha_composite(g,(int(x-g.size[0]/2),int(y-g.size[1]/2)))

def default_spec():
    """Нейтральный демо-пресет (без реальных данных). Реальный пример — presets/jenti_example.json."""
    C = (35,60,170); W = (255,255,255)
    return {"form":"ellipse","width_mm":40,"height_mm":30,"dpi":300,"rotation_deg":0,"noise":15,"corner_mm":0,
      "layers":[
    {"type":"band","inset_out_mm":0.0,"inset_in_mm":2.4,"color":C},
    {"type":"arc_text","text":"ВАША ОРГАНИЗАЦИЯ * ВАША ОРГАНИЗАЦИЯ *","pos":"top","attract":"ellipse",
         "auto_band":True,"inset_mm":1.2,"vshift_mm":0,"size_mm":1.9,"w_pct":100,"h_pct":100,
         "spacing_mm":0.5,"font":"Arial","bold":True,"flip":False,"color":W},
        {"type":"ring","inset_mm":2.9,"thickness_mm":0.35,"color":C},
        {"type":"ring","inset_mm":3.6,"thickness_mm":0.25,"color":C},
        {"type":"arc_text","text":"ДЕМО-ПЕЧАТЬ","pos":"top","attract":"ellipse","auto_band":False,
         "inset_mm":4.6,"vshift_mm":0,"size_mm":2.6,"w_pct":100,"h_pct":100,"spacing_mm":0.5,
         "font":"Arial","bold":True,"flip":False,"color":C},
        {"type":"arc_text","text":"ГОРОД · СТРАНА","pos":"bottom","attract":"ellipse","auto_band":False,
         "inset_mm":5.9,"vshift_mm":0,"size_mm":2.2,"w_pct":100,"h_pct":100,"spacing_mm":0.5,
         "font":"Arial","bold":True,"flip":False,"color":C},
        {"type":"center_text","lines":["ОБРАЗЕЦ","№ 123"],"size_mm":3.4,"spacing_mm":1.0,"align":"center",
         "dx_mm":0,"dy_mm":0,
         "w_pct":100,"h_pct":100,"font":"Arial","bold":True,"plate_on":False,"plate_pad_mm":1,
         "plate_color":C,"color":C},
      ]}

def _bgr_qimage(bgr):
    rgb = np.ascontiguousarray(bgr[..., ::-1])
    h, w = rgb.shape[:2]
    return QImage(rgb.data, w, h, 3*w, QImage.Format_RGB888).copy()

class _PickColorDialog(QDialog):
    def __init__(self, page):
        super().__init__()
        self.page = page; self.color = None
        self.setWindowTitle("Кликните по цвету чернил на скане")
        lay = QVBoxLayout(self)
        sc = QScrollArea(); sc.setWidgetResizable(False)
        self.lbl = QLabel()
        self.lbl.setPixmap(QPixmap.fromImage(_bgr_qimage(page)))
        self.lbl.mousePressEvent = self._click
        sc.setWidget(self.lbl)
        lay.addWidget(sc)
        self.resize(1000, 700)
    def _click(self, ev):
        p = ev.position(); x, y = int(p.x()), int(p.y())
        H, W = self.page.shape[:2]
        if 0 <= x < W and 0 <= y < H:
            b, g, r = [int(v) for v in self.page[y, x]]
            self.color = (r, g, b)
            self.accept()

class PlacementDialog(QDialog):
    def __init__(self, mw, stamp):
        super().__init__(mw)
        self.mw = mw; self.stamp = stamp
        self.page = mw.current_image()
        H, W = self.page.shape[:2]
        self.setWindowTitle("Подгонка эталона на документе")
        root = QVBoxLayout(self)
        self.prev = QLabel(); self.prev.setAlignment(Qt.AlignCenter)
        self.prev.setStyleSheet("background:#222; border:1px solid #444;")
        # политика Ignored: pixmap не должен диктовать minimumSize окна,
        # иначе каждая перерисовка раздувает диалог (+2px за изменение X/Y/масштаба)
        self.prev.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Ignored)
        self._pm = None
        root.addWidget(self.prev, 1)
        f = QFormLayout()
        self.s_x = QSpinBox(); self.s_x.setRange(0, W); self.s_x.setValue(W//2)
        self.s_y = QSpinBox(); self.s_y.setRange(0, H); self.s_y.setValue(H//2)
        self.s_sc = QDoubleSpinBox(); self.s_sc.setRange(5, 400); self.s_sc.setValue(100)
        self.s_rt = QDoubleSpinBox(); self.s_rt.setRange(-180, 180); self.s_rt.setValue(0)
        for w_, lab in [(self.s_x,"X, px"),(self.s_y,"Y, px"),(self.s_sc,"Масштаб, %"),(self.s_rt,"Поворот, °")]:
            f.addRow(lab, w_); w_.valueChanged.connect(self._sync)
        root.addLayout(f)
        bb = QHBoxLayout()
        ok = QPushButton("✅ Применить"); ok.clicked.connect(self._apply); bb.addWidget(ok)
        no = QPushButton("Отмена"); no.clicked.connect(self.reject); bb.addWidget(no)
        root.addLayout(bb)
        self.resize(1100, 800)
        self._sync()
    def _sync(self, *a):
        self.x = self.s_x.value(); self.y = self.s_y.value()
        self.scale = self.s_sc.value(); self.rot = self.s_rt.value()
        self._pm = QPixmap.fromImage(_bgr_qimage(self._composite(1200)))
        self._show_pm()
    def _show_pm(self):
        if getattr(self, "_pm", None) and not self._pm.isNull() and self.prev.width() > 1:
            self.prev.setPixmap(self._pm.scaled(
                self.prev.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation))
    def showEvent(self, ev):
        super().showEvent(ev)
        self._show_pm()   # первый показ: превью по реальному размеру, а не по «до show»
    def resizeEvent(self, ev):
        super().resizeEvent(ev)
        self._show_pm()   # ресайз окна = перемасштабить превью, окно не «разъезжается»
    def _stamp_np(self, k_prev=1.0):
        s = self.stamp
        # масштаб штампа в превью обязан умножаться на k_prev (фактор уменьшения
        # страницы), иначе превь вранья: штамп кажется в 1/k_prev раз крупнее,
        # чем он ляжет в документ при «Применить»
        k = self.scale/100.0 * k_prev
        s = s.resize((max(1,int(s.width*k)), max(1,int(s.height*k))), Image.LANCZOS)
        if self.rot: s = s.rotate(-self.rot, expand=True, resample=Image.BICUBIC)
        return np.array(s)
    def _composite(self, preview_max=None):
        page = self.page
        k_prev = 1.0
        H, W = page.shape[:2]
        if preview_max:
            k_prev = min(1.0, preview_max/float(max(H, W)))
        if k_prev < 1.0:
            rgb = np.ascontiguousarray(page[..., ::-1])
            pim = Image.fromarray(rgb).resize((int(W*k_prev), int(H*k_prev)), Image.LANCZOS)
            page = np.ascontiguousarray(np.array(pim)[..., ::-1])
        arr = self._stamp_np(k_prev)
        sh, sw = arr.shape[:2]
        x0 = int(self.x*k_prev - sw/2); y0 = int(self.y*k_prev - sh/2)
        H, W = page.shape[:2]
        sx0, sy0 = max(0, -x0), max(0, -y0)
        x0c, y0c = max(0, x0), max(0, y0)
        x1c, y1c = min(W, x0+sw), min(H, y0+sh)
        out = page.copy()
        if x1c > x0c and y1c > y0c:
            hh, ww = y1c-y0c, x1c-x0c
            a = arr[sy0:sy0+hh, sx0:sx0+ww, 3:4]/255.0
            rgb = arr[sy0:sy0+hh, sx0:sx0+ww, :3][..., ::-1].astype(np.float32)
            reg = out[y0c:y1c, x0c:x1c].astype(np.float32)
            out[y0c:y1c, x0c:x1c] = np.clip(reg*(1-a)+rgb*a, 0, 255).astype(np.uint8)
        return out
    def _apply(self):
        mw = self.mw
        mw.undo_stack.append((mw.current_page, mw.edited.get(mw.current_page)))
        if len(mw.undo_stack) > 10: mw.undo_stack.pop(0)
        mw.btn_undo.setEnabled(True)
        mw.edited[mw.current_page] = self._composite()
        mw._reload_page()
        self.accept()

def _line_icon(kind):
    """Маленький векторный значок для кнопок строк (копир/корзина) — не зависит от шрифтов."""
    pm = QPixmap(18, 18); pm.fill(Qt.transparent)
    p = QPainter(pm); pen = QPen(QColor("#c9d3e0")); pen.setWidthF(1.5)
    pen.setCapStyle(Qt.RoundCap); p.setPen(pen)
    if kind == "copy":
        p.drawRect(3, 6, 8, 9); p.drawRect(7, 3, 8, 9)
    else:
        p.drawLine(3, 5, 15, 5); p.drawLine(7, 3, 11, 3); p.drawLine(9, 3, 9, 5)
        p.drawPolyline(QPolygonF([QPointF(4, 5), QPointF(5, 15), QPointF(13, 15), QPointF(14, 5)]))
        p.drawLine(7, 8, 7, 12); p.drawLine(11, 8, 11, 12)
    p.end()
    return QIcon(pm)

class BuilderWindow(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.Window)
        self.spec = default_spec()
        self.setWindowTitle("Конструктор печатей / Stamp Builder")
        self.resize(1250, 800)
        root = QHBoxLayout(self)
        self.split = QSplitter(Qt.Horizontal)
        self.split.setHandleWidth(8)
        self.split.setCollapsible(0, False); self.split.setCollapsible(1, False)
        self.split.setStretchFactor(0, 0); self.split.setStretchFactor(1, 1)
        self.split.splitterMoved.connect(lambda *a: self._render())
        lp = QWidget(); left = QVBoxLayout(lp); lp.setContentsMargins(0,0,0,0); lp.setMinimumWidth(620)
        gf = QFormLayout(); left.addLayout(gf)
        self.cb_form = QComboBox(); self.cb_form.addItems(["ellipse","circle","rect"]); gf.addRow("Форма", self.cb_form)
        self.sp_w = QDoubleSpinBox(); self.sp_w.setRange(5,100); self.sp_w.setValue(40); gf.addRow("Ширина, мм", self.sp_w)
        self.sp_h = QDoubleSpinBox(); self.sp_h.setRange(5,100); self.sp_h.setValue(30); gf.addRow("Высота, мм", self.sp_h)
        self.sp_rot = QDoubleSpinBox(); self.sp_rot.setRange(-180,180); gf.addRow("Поворот, °", self.sp_rot)
        self.sp_noise = QDoubleSpinBox(); self.sp_noise.setRange(0,100); self.sp_noise.setValue(15); gf.addRow("Неоднотность, %", self.sp_noise)
        self.cb_corners = QComboBox(); self.cb_corners.addItems(["прямые","скруглённые"]); gf.addRow("Углы прямоугольника", self.cb_corners)
        self.sp_corner = QDoubleSpinBox(); self.sp_corner.setRange(0,20); self.sp_corner.setValue(0); self.sp_corner.setEnabled(False); gf.addRow("Скругление углов, мм", self.sp_corner)
        self.cb_form.currentIndexChanged.connect(self._sync_global)
        self.cb_corners.currentIndexChanged.connect(lambda *a: (self.sp_corner.setEnabled(self.cb_corners.currentIndex()==1), self._sync_global()))
        for w_ in (self.sp_w, self.sp_h, self.sp_rot, self.sp_noise, self.sp_corner): w_.valueChanged.connect(self._sync_global)
        lr = QHBoxLayout(); left.addLayout(lr)
        self.lst = QListWidget(); lr.addWidget(self.lst, 1)
        bb = QVBoxLayout(); lr.addLayout(bb)
        for name, t in [("+Кольцо","ring"),("+Лента","band"),("+Дуга","arc_text"),
                        ("+Центр","center_text"),("+Герб","emblem"),("+РамкаРис","pic_frame")]:
            b = QPushButton(name); b.clicked.connect(lambda c, tt=t: self._add(tt)); bb.addWidget(b)
        b = QPushButton("− Удалить"); b.clicked.connect(self._del); bb.addWidget(b)
        b = QPushButton("↑"); b.clicked.connect(lambda: self._move(-1)); bb.addWidget(b)
        b = QPushButton("↓"); b.clicked.connect(lambda: self._move(1)); bb.addWidget(b)
        self.lst.currentRowChanged.connect(self._rebuild_editor)
        self.ed_scroll = QScrollArea(); self.ed_scroll.setWidgetResizable(True)
        self.ed_widget = QWidget(); self.ed_scroll.setWidget(self.ed_widget)
        self.ed_layout = QFormLayout(self.ed_widget)
        left.addWidget(self.ed_scroll, 1)
        br = QHBoxLayout(); left.addLayout(br)
        b = QPushButton("🎲 Демо"); b.clicked.connect(self._reset_demo); br.addWidget(b)
        b = QPushButton("💾 Пресет"); b.clicked.connect(self._save_preset); br.addWidget(b)
        b = QPushButton("📂 Пресет"); b.clicked.connect(self._load_preset); br.addWidget(b)
        b = QPushButton("🖼 PNG"); b.clicked.connect(self._export); br.addWidget(b)
        br2 = QHBoxLayout(); left.addLayout(br2)
        b = QPushButton("🎯 Цвет со скана"); b.clicked.connect(self._pick_from_scan); br2.addWidget(b)
        b = QPushButton("📌 На документ"); b.clicked.connect(self._place_on_doc); br2.addWidget(b)
        b = QPushButton("🔤 Шрифт из Скана"); b.clicked.connect(self._match_font); br2.addWidget(b)
        self.prev = QLabel(); self.prev.setMinimumSize(360,360)
        self.prev.setAlignment(Qt.AlignCenter)
        self.prev.setStyleSheet("background:#222; border:1px solid #444;")
        self.split.addWidget(lp); self.split.addWidget(self.prev)
        self.split.setSizes([640, 600])
        root.addWidget(self.split, 1)
        self._refresh_list(); self._render()

    def _name(self, L):
        extra = L.get("text") or (L.get("lines") or [""])[0] or L.get("glyph","")
        same = [x for x in self.spec["layers"] if x["type"]==L["type"]]
        num = ""
        if len(same) > 1:
            k = 0
            for x in self.spec["layers"]:
                if x is L: break
                if x["type"]==L["type"]: k += 1
            num = f" #{k+1}"
        return f"{L['type']}{num}: {str(extra)[:16]}"

    def _sync_global(self, *a):
        self.spec["form"]=self.cb_form.currentText(); self.spec["width_mm"]=self.sp_w.value()
        self.spec["height_mm"]=self.sp_h.value(); self.spec["rotation_deg"]=self.sp_rot.value()
        self.spec["noise"]=self.sp_noise.value()
        self.spec["corner_mm"]=self.sp_corner.value() if self.cb_corners.currentIndex()==1 else 0.0
        self._render()

    def _refresh_list(self):
        self.lst.clear()
        for L in self.spec["layers"]: self.lst.addItem(self._name(L))
        if self.lst.count(): self.lst.setCurrentRow(0)

    def _add(self, t):
        d = {"type": t}
        if t=="arc_text": d.update({"text":"ТЕКСТ","pos":"top","attract":"ellipse","auto_band":False,
            "inset_mm":4.0,"vshift_mm":0,"ashift_mm":0,"size_mm":2.5,"w_pct":100,"h_pct":100,"spacing_mm":0.4,
            "font":"Arial","bold":True,"flip":False,"color":(35,60,170)})
        if t=="ring": d.update({"inset_mm":1.0,"thickness_mm":0.4,"color":(35,60,170)})
        if t=="band": d.update({"inset_out_mm":0,"inset_in_mm":2.5,"color":(35,60,170)})
        if t=="center_text": d.update({"lines":["ТЕКСТ"],"size_mm":3,"spacing_mm":1,"align":"center","dx_mm":0,"dy_mm":0,"w_pct":100,"h_pct":100,"font":"Arial",
            "bold":True,"plate_on":False,"plate_pad_mm":1,"plate_color":(35,60,170),"color":(35,60,170)})
        if t=="emblem": d.update({"path":"","height_mm":15,"dx_mm":0,"dy_mm":0,"recolor_on":False,"recolor":(35,60,170)})
        if t=="pic_frame": d.update({"glyph":"tick","count":60,"inset_mm":0.5,"size_mm":1.2,"color":(35,60,170)})
        self.spec["layers"].append(d); self._refresh_list(); self.lst.setCurrentRow(len(self.spec["layers"])-1)

    def _del(self):
        r = self.lst.currentRow()
        if r>=0: self.spec["layers"].pop(r); self._refresh_list(); self._render()

    def _move(self, d):
        r = self.lst.currentRow(); n = len(self.spec["layers"])
        if r<0: return
        j = r+d
        if 0<=j<n:
            self.spec["layers"][r], self.spec["layers"][j] = self.spec["layers"][j], self.spec["layers"][r]
            self._refresh_list(); self.lst.setCurrentRow(j)

    def _rebuild_editor(self, row):
        self.ed_widget = QWidget()
        self.ed_layout = QFormLayout(self.ed_widget)
        self.ed_scroll.setWidget(self.ed_widget)
        if row<0 or row>=len(self.spec["layers"]): return
        L = self.spec["layers"][row]
        wd = {}
        for key,kind,a,b in SCHEMA[L["type"]]:
            try:
                lab = LABELS.get(key, key)
                if kind in ("mm","f"):
                    s = QDoubleSpinBox(); s.setRange(a,b); s.setDecimals(2)
                    s.setSingleStep(0.05 if kind=="f" else 0.1); s.setValue(float(L.get(key,0)))
                    s.valueChanged.connect(lambda v,k=key: self._set(k,v)); wd[key]=s; self.ed_layout.addRow(lab,s)
                elif kind=="int":
                    s = QSpinBox(); s.setRange(a,b); s.setValue(int(L.get(key,10)))
                    s.valueChanged.connect(lambda v,k=key: self._set(k,v)); self.ed_layout.addRow(lab,s)
                elif kind=="pct":
                    s = QSpinBox(); s.setRange(a,b); s.setSuffix("%"); s.setValue(int(L.get(key,100)))
                    s.valueChanged.connect(lambda v,k=key: self._set(k,v)); self.ed_layout.addRow(lab,s)
                elif kind=="text":
                    e = QLineEdit(str(L.get(key,""))); e.textChanged.connect(lambda v,k=key: self._set(k,v))
                    self.ed_layout.addRow(lab,e)
                elif kind=="lines":
                    if L["type"]=="center_text":
                        self._build_lines(L)
                    else:
                        e = QPlainTextEdit(); e.setPlainText("\n".join(L.get(key,[])))
                        e.textChanged.connect(lambda k=key,e=e: self._set(k, e.toPlainText().split("\n")))
                        self.ed_layout.addRow(lab,e)
                elif kind=="combo":
                    c = QComboBox()
                    names = GLYPH_NAMES if key=="glyph" else {}
                    cur = str(L.get(key,b[0]))
                    c.addItems([names.get(str(v), str(v)) for v in b])
                    c.setCurrentText(names.get(cur, cur))
                    c.currentTextChanged.connect(lambda v,k=key,names=names: self._set(k, next((t for t,n in names.items() if n==v), v)))
                    self.ed_layout.addRow(lab,c)
                elif kind=="check":
                    c = QCheckBox(); c.setChecked(bool(L.get(key,False)))
                    c.toggled.connect(lambda v,k=key: self._set(k,v)); wd[key]=c; self.ed_layout.addRow(lab,c)
                elif kind=="color":
                    cur = L.get(key,(35,60,170)); btn = QPushButton("цвет")
                    btn.setStyleSheet("background:#%02x%02x%02x"%tuple(cur))
                    btn.clicked.connect(lambda c,k=key,btn=btn: self._pick(k,btn))
                    self.ed_layout.addRow(lab,btn)
                elif kind=="file":
                    e = QLineEdit(str(L.get(key,""))); b2 = QPushButton("…")
                    b2.clicked.connect(lambda k=key,e=e: self._browse(k,e))
                    e.textChanged.connect(lambda v,k=key: self._set(k,v))
                    rw = QHBoxLayout(); rw.setContentsMargins(0,0,0,0); rw.addWidget(e); rw.addWidget(b2); self.ed_layout.addRow(lab,rw)
            except Exception:
                pass
        # авто-отступ из ленты делает ручной отступ неактуальным — гасим поле
        if "auto_band" in wd and "inset_mm" in wd:
            cb=wd["auto_band"]; ins=wd["inset_mm"]
            ins.setEnabled(not cb.isChecked())
            cb.toggled.connect(lambda v,w=ins: w.setEnabled(not v))

    def _set(self,k,v):
        r = self.lst.currentRow()
        if r>=0: self.spec["layers"][r][k]=v; self._render()

    def _build_lines(self, L):
        """Поуровневый редактор строк центрального блока: на строку — свой текст, шрифт,
        жирность, цвет, кегль, сдвиг X/Y и растяжка ширины/высоты символов в %."""
        lines = list(L.get("lines", [""])) or [""]
        ls = [dict(s or {}) for s in (L.get("line_styles") or [])]
        while len(ls) < len(lines): ls.append({})
        L["lines"] = lines; L["line_styles"] = ls
        lbl = QLabel("Строки: своя строка = свой шрифт, жирность, цвет, кегль, сдвиг X/Y, "
                     "растяжка симв. %. «Шрифт»/«Жирность» без выбора и кегль по умолчанию = как у слоя. "
                     "Кнопка с копиром у строки переносит её стиль в другую строку, корзина удаляет строку.")
        lbl.setWordWrap(True)
        self.ed_layout.addRow(lbl)
        base_w = int(L.get("w_pct", 100)); base_h = int(L.get("h_pct", 100))
        for idx, txt in enumerate(lines):
            box = QWidget(); v = QVBoxLayout(box); v.setContentsMargins(0,0,0,0); v.setSpacing(4)
            # строка 1: текст + удаление конкретной строки
            r0 = QHBoxLayout(); r0.setContentsMargins(0,0,0,0); r0.setSpacing(5)
            le = QLineEdit(txt); le.textChanged.connect(lambda v2,i=idx: self._line_set(i, text=v2))
            r0.addWidget(le, 1)
            cpb = QPushButton(); cpb.setFixedWidth(30); cpb.setEnabled(len(lines) > 1)
            cpb.setIcon(_line_icon("copy"))
            cpb.setToolTip("Копировать стиль этой строки в другую")
            cpb.clicked.connect(lambda _=None,i=idx,b=cpb: self._line_copy_menu(i, b)); r0.addWidget(cpb)
            delb = QPushButton(); delb.setFixedWidth(30); delb.setIcon(_line_icon("trash"))
            delb.setToolTip("Удалить эту строку")
            delb.clicked.connect(lambda _=None,i=idx: self._line_del_at(i)); r0.addWidget(delb)
            v.addLayout(r0)
            # строка 2: шрифт, жирность, цвет, кегль
            r1 = QHBoxLayout(); r1.setContentsMargins(0,0,0,0); r1.setSpacing(5)
            fb = QComboBox(); fb.addItems(["Шрифт"] + FONT_NAMES)
            fb.setMinimumWidth(100); fb.setSizeAdjustPolicy(QComboBox.AdjustToMinimumContentsLengthWithIcon)
            fb.setMinimumContentsLength(8)
            fb.setCurrentText(ls[idx].get("font", "Шрифт"))
            fb.currentTextChanged.connect(lambda v2,i=idx: self._line_set(i, font=v2)); r1.addWidget(fb, 1)
            bb = QComboBox(); bb.addItems(["Жирность", "да", "нет"]); bb.setMinimumWidth(88)
            bb.setToolTip("«Жирность» без выбора = как у слоя")
            bb.setCurrentIndex(0 if "bold" not in ls[idx] else (1 if ls[idx]["bold"] else 2))
            bb.currentIndexChanged.connect(lambda v2,i=idx: self._line_set(i, bold=(None if v2==0 else v2==1)))
            r1.addWidget(bb)
            btn = QPushButton("цвет"); btn.setMinimumWidth(52)
            if ls[idx].get("color"): btn.setStyleSheet("background:#%02x%02x%02x" % tuple(ls[idx]["color"]))
            btn.clicked.connect(lambda _=None, i=idx, b=btn: self._line_color(i, b)); r1.addWidget(btn)
            r1.addWidget(QLabel("кегль"))
            sb = QDoubleSpinBox(); sb.setRange(0.5, 12); sb.setDecimals(2); sb.setSuffix(" мм")
            sb.setMinimumWidth(78)
            sb.setValue(float(ls[idx].get("size_mm", L.get("size_mm", 3.0))))
            sb.valueChanged.connect(lambda v2,i=idx: self._line_set(i, size=v2)); r1.addWidget(sb)
            v.addLayout(r1)
            # строка 3: сдвиг X/Y строки + растяжка символов строки в %
            r2 = QHBoxLayout(); r2.setContentsMargins(0,0,0,0); r2.setSpacing(5)
            lbx = QLabel("X, мм"); lbx.setToolTip("Сдвиг этой строки по горизонтали, мм")
            r2.addWidget(lbx)
            sdx = QDoubleSpinBox(); sdx.setRange(-40,40); sdx.setDecimals(2); sdx.setSuffix(" мм")
            sdx.setMinimumWidth(75); sdx.setValue(float(ls[idx].get("dx_mm", 0.0)))
            sdx.valueChanged.connect(lambda v2,i=idx: self._line_set(i, dx=v2)); r2.addWidget(sdx)
            lby = QLabel("Y, мм"); lby.setToolTip("Сдвиг этой строки по вертикали, мм")
            r2.addWidget(lby)
            sdy = QDoubleSpinBox(); sdy.setRange(-40,40); sdy.setDecimals(2); sdy.setSuffix(" мм")
            sdy.setMinimumWidth(75); sdy.setValue(float(ls[idx].get("dy_mm", 0.0)))
            sdy.valueChanged.connect(lambda v2,i=idx: self._line_set(i, dy=v2)); r2.addWidget(sdy)
            lbw = QLabel("Шир.%"); lbw.setToolTip("Растяжка символов этой строки по ширине, %")
            r2.addWidget(lbw)
            sw = QSpinBox(); sw.setRange(10,200); sw.setSuffix("%"); sw.setMinimumWidth(58)
            sw.setValue(int(ls[idx].get("w_pct", base_w)))
            sw.valueChanged.connect(lambda v2,i=idx: self._line_set(i, w=v2)); r2.addWidget(sw)
            lbh = QLabel("Выс.%"); lbh.setToolTip("Растяжка символов этой строки по высоте, %")
            r2.addWidget(lbh)
            sh = QSpinBox(); sh.setRange(10,200); sh.setSuffix("%"); sh.setMinimumWidth(58)
            sh.setValue(int(ls[idx].get("h_pct", base_h)))
            sh.valueChanged.connect(lambda v2,i=idx: self._line_set(i, h=v2)); r2.addWidget(sh)
            r2.addStretch(1)
            v.addLayout(r2)
            self.ed_layout.addRow(box)
        r3 = QHBoxLayout()
        ad = QPushButton("+ строку"); ad.clicked.connect(self._line_add); r3.addWidget(ad)
        dl = QPushButton("− последнюю"); dl.clicked.connect(self._line_del); r3.addWidget(dl)
        self.ed_layout.addRow(r3)

    def _line_set(self, idx, text=None, size=None, font=None, bold=None, color=None,
                  w=None, h=None, dx=None, dy=None):
        r = self.lst.currentRow()
        if r < 0: return
        L = self.spec["layers"][r]
        lines = list(L.get("lines", [""]))
        while len(lines) <= idx: lines.append("")
        if text is not None: lines[idx] = text
        L["lines"] = lines
        ls = [dict(s or {}) for s in (L.get("line_styles") or [])]
        while len(ls) < len(lines): ls.append({})
        st = ls[idx]
        if size is not None: st["size_mm"] = size
        if font is not None:
            if font == "Шрифт": st.pop("font", None)
            else: st["font"] = font
        if bold is not None:
            if bold is None: st.pop("bold", None)
            else: st["bold"] = bold
        if color is not None: st["color"] = list(color)
        if w is not None: st["w_pct"] = w
        if h is not None: st["h_pct"] = h
        if dx is not None: st["dx_mm"] = dx
        if dy is not None: st["dy_mm"] = dy
        L["line_styles"] = ls
        self._render()

    def _line_color(self, idx, btn):
        r = self.lst.currentRow()
        if r < 0: return
        cur = (35, 60, 170)
        ls = self.spec["layers"][r].get("line_styles") or []
        if idx < len(ls) and ls[idx].get("color"): cur = tuple(ls[idx]["color"])
        c = QColorDialog.getColor(QColor(*cur), self)
        if c.isValid():
            btn.setStyleSheet("background:#%02x%02x%02x" % (c.red(), c.green(), c.blue()))
            self._line_set(idx, color=(c.red(), c.green(), c.blue()))

    def _line_add(self):
        r = self.lst.currentRow()
        if r < 0: return
        L = self.spec["layers"][r]
        L.setdefault("lines", []).append("новая строка")
        L.setdefault("line_styles", []).append({})
        self._rebuild_editor(r)

    def _line_del(self):
        r = self.lst.currentRow()
        if r < 0: return
        L = self.spec["layers"][r]
        if len(L.get("lines", [])) > 1:
            L["lines"].pop()
            if L.get("line_styles"): L["line_styles"].pop()
            self._rebuild_editor(r)

    def _line_del_at(self, idx):
        r = self.lst.currentRow()
        if r < 0: return
        L = self.spec["layers"][r]
        if len(L.get("lines", [])) > 1:
            L["lines"].pop(idx)
            if len(L.get("line_styles") or []) > idx: L["line_styles"].pop(idx)
            self._rebuild_editor(r)

    _LINE_STYLE_KEYS = ("size_mm", "font", "bold", "color", "w_pct", "h_pct", "dx_mm", "dy_mm")

    def _line_copy_menu(self, src, btn):
        """Меню «→ строка N»: куда скопировать стиль строки src (текст не трогаем)."""
        r = self.lst.currentRow()
        if r < 0: return
        n = len(self.spec["layers"][r].get("lines", []))
        m = QMenu(self)
        for j in range(n):
            if j == src: continue
            m.addAction("→ строка %d" % (j + 1), lambda _=None, d=j, s=src: self._line_copy_style(s, d))
        m.exec(btn.mapToGlobal(btn.rect().bottomLeft()))

    def _line_copy_style(self, src, dst):
        r = self.lst.currentRow()
        if r < 0: return
        L = self.spec["layers"][r]
        ls = [dict(s or {}) for s in (L.get("line_styles") or [])]
        while len(ls) <= max(src, dst): ls.append({})
        src_st, dst_st = ls[src], dict(ls[dst])
        for k in self._LINE_STYLE_KEYS:
            if k in src_st:
                dst_st[k] = list(src_st[k]) if isinstance(src_st[k], list) else src_st[k]
            else:
                dst_st.pop(k, None)
        ls[dst] = dst_st
        L["line_styles"] = ls
        self._rebuild_editor(r)

    def _pick(self,k,btn):
        r = self.lst.currentRow()
        cur = self.spec["layers"][r].get(k,(35,60,170))
        c = QColorDialog.getColor(QColor(*cur), self)
        if c.isValid():
            self.spec["layers"][r][k]=(c.red(),c.green(),c.blue())
            btn.setStyleSheet("background:#%02x%02x%02x"%(c.red(),c.green(),c.blue()))
            self._render()

    def _browse(self,k,e):
        p,_ = QFileDialog.getOpenFileName(self,"Рисунок","","Images (*.png *.bmp *.jpg)")
        if p: e.setText(p)

    def _pick_from_scan(self):
        mw = self.parent()
        if mw is None or not hasattr(mw, "current_image") or not mw.doc: return
        d = _PickColorDialog(mw.current_image())
        if d.exec() and d.color:
            r = self.lst.currentRow()
            if r >= 0:
                key = "recolor" if self.spec["layers"][r]["type"]=="emblem" else "color"
                self._set(key, d.color)
                self._rebuild_editor(r)

    def _place_on_doc(self):
        mw = self.parent()
        if mw is None or not hasattr(mw, "current_image") or not mw.doc: return
        PlacementDialog(mw, render_stamp(self.spec)).exec()

    def _match_font(self):
        mw = self.parent()
        if mw is None or not hasattr(mw, "current_image") or not mw.doc: return
        def apply(fam, bold):
            r = self.lst.currentRow()
            if r >= 0:
                self.spec["layers"][r]["font"] = fam
                self.spec["layers"][r]["bold"] = bold
                self._rebuild_editor(r); self._render()
        FontMatchDialog(mw.current_image(), apply).exec()
    def _render(self):
        try:
            img = render_stamp(self.spec)
            data = img.tobytes("raw","RGBA")
            q = QImage(data, img.size[0], img.size[1], 4*img.size[0], QImage.Format_RGBA8888).copy()
            pm = QPixmap.fromImage(q).scaled(self.prev.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.prev.setPixmap(pm)
        except Exception as e:
            self.prev.setText(f"Ошибка рендера: {e}")

    def resizeEvent(self,e): self._render(); super().resizeEvent(e)

    def _apply_global_widgets(self):
        # сигналы виджетов гасим: иначе setValue() по очереди пишет в spec смесь
        # нового и старого значений (баг загрузки пресета: width из файла терялся)
        for _w in (self.cb_form, self.sp_w, self.sp_h, self.sp_rot, self.sp_noise,
                   self.cb_corners, self.sp_corner):
            _w.blockSignals(True)
        self.cb_form.setCurrentText(self.spec["form"])
        self.sp_w.setValue(self.spec["width_mm"]); self.sp_h.setValue(self.spec["height_mm"])
        self.sp_rot.setValue(self.spec.get("rotation_deg",0)); self.sp_noise.setValue(self.spec.get("noise",15))
        cor = self.spec.get("corner_mm",0)
        self.cb_corners.setCurrentIndex(1 if cor>0 else 0)
        self.sp_corner.setEnabled(cor>0); self.sp_corner.setValue(cor)
        for _w in (self.cb_form, self.sp_w, self.sp_h, self.sp_rot, self.sp_noise,
                   self.cb_corners, self.sp_corner):
            _w.blockSignals(False)

    def _reset_demo(self):
        self.spec = default_spec()
        self._apply_global_widgets()
        self._refresh_list(); self._render()

    @staticmethod
    def _presets_dir():
        """Каталог пресетов: рядом с exe (правится пользователем) → внутри сборки
        (PyInstaller кладёт add-data в _internal == sys._MEIPASS) → исходники."""
        cands = []
        if getattr(sys, "frozen", False):
            exedir = os.path.dirname(sys.executable)
            cands.append(os.path.join(exedir, "presets"))
            meip = getattr(sys, "_MEIPASS", None)
            if meip:
                cands.append(os.path.join(meip, "presets"))
        cands.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), "presets"))
        for c in cands:
            if os.path.isdir(c):
                return c
        return ""

    def _save_preset(self):
        d = self._presets_dir()
        start = os.path.join(d, "stamp_preset.json") if d else "stamp_preset.json"
        p,_ = QFileDialog.getSaveFileName(self,"Сохранить пресет",start,"JSON (*.json)")
        if p:
            with open(p,"w",encoding="utf-8") as f: json.dump(self.spec,f,ensure_ascii=False,indent=2)

    def _load_preset(self):
        d = self._presets_dir()
        p,_ = QFileDialog.getOpenFileName(self,"Загрузить пресет",d or "","JSON (*.json)")
        if p:
            with open(p,encoding="utf-8") as f: self.spec = json.load(f)
            self._apply_global_widgets()
            self._refresh_list(); self._render()

    def _export(self):
        p,_ = QFileDialog.getSaveFileName(self,"Экспорт PNG","stamp.png","PNG (*.png)")
        if p: render_stamp(self.spec).save(p)

if __name__ == "__main__":
    import sys
    from PySide6.QtWidgets import QApplication
    app = QApplication(sys.argv)
    w = BuilderWindow(); w.show()
    sys.exit(app.exec())