# -*- coding: utf-8 -*-
"""生成两样数据：

1. data/buttons.json + assets/btnover/*.webp —— 按钮的「鼠标悬停态」。
   原版按钮是 Flash 的 DefineButton2，带 up/over/down/hit 四种状态。悬停时按钮自己会换成
   over 那一张（客栈属性里「市」图标悬停会弹出花费/收益说明就是这么来的）。移植版的画面是
   整幅烧死的图，只有 up 状态，所以悬停看不到变化。这里把 over 相对 up 多出来的像素存成
   透明贴图，运行时鼠标压上去叠一张。

2. data/hidden.json —— 某一帧里被「后画上去的东西」盖住的文本框。
   原版美术是按深度一层层画的，文字框在深度 20~60，弹出来的说明框/黑幕在深度 120 以上，
   会把文字盖住（比如秀才页悬停「鼓励」时，好感、对郭芙蓉的情感这两个数字就被说明框压住）。
   移植版文字是单独一层画在最上面，会浮在说明框上，所以这些帧要按原版把它藏起来。
   判定办法：哪一帧的画面相对上一个关键帧变了、而且正好盖住了这个文本框，就藏。
"""
import os, io, sys, json
sys.stdout.reconfigure(encoding="utf-8")
import numpy as np
from PIL import Image

B = r"F:\路小白。。\一些尝试\游戏\同福奇缘_移植"
GAME = os.path.join(B, "game")
BTN = os.path.join(B, "decompiled", "buttons")
BG = os.path.join(GAME, "assets", "bg")
OV = os.path.join(GAME, "assets", "btnover")
DATA = os.path.join(GAME, "data")

ui = json.load(io.open(os.path.join(DATA, "ui.json"), encoding="utf-8"))
bgs = json.load(io.open(os.path.join(DATA, "frames.json"), encoding="utf-8"))["bg"]
beats = json.load(io.open(os.path.join(DATA, "beats.json"), encoding="utf-8"))


def abbox(a):
    m = a[:, :, 3] > 8
    ys, xs = np.nonzero(m)
    if not len(xs):
        return None
    return [int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1]


# ---------------------------------------------------------------- 1. 按钮悬停态
def build_buttons():
    os.makedirs(OV, exist_ok=True)
    for f in os.listdir(OV):
        os.remove(os.path.join(OV, f))
    out = {}
    used = {}
    for k in ui:
        for it in ui[k]:
            if it.get("k") == "btn":
                used[int(it["id"])] = True
    total = 0
    for bid in sorted(used):
        p = os.path.join(BTN, "DefineButton2_%d" % bid)
        up_p, ov_p = os.path.join(p, "1_up.png"), os.path.join(p, "2_over.png")
        if not (os.path.exists(up_p) and os.path.exists(ov_p)):
            continue
        A = np.asarray(Image.open(up_p).convert("RGBA")).astype(np.int16)
        C = np.asarray(Image.open(ov_p).convert("RGBA")).astype(np.int16)
        if A.shape != C.shape:
            continue
        mask = np.abs(A - C).max(axis=2) > 8
        if not mask.any():
            continue
        ub = abbox(A)
        if ub is None:
            continue
        rgba = np.zeros((C.shape[0], C.shape[1], 4), dtype=np.uint8)
        rgba[mask] = C[mask].astype(np.uint8)
        bb = abbox(rgba)
        ox, oy = bb[0], bb[1]
        crop = rgba[bb[1]:bb[3], bb[0]:bb[2]]
        q = os.path.join(OV, "%d.webp" % bid)
        Image.fromarray(crop, "RGBA").save(q, "WEBP", lossless=True, method=4)
        total += os.path.getsize(q)
        out[str(bid)] = {"f": "%d.webp" % bid, "w": int(crop.shape[1]), "h": int(crop.shape[0]),
                         "ox": ox, "oy": oy, "uw": ub[2] - ub[0], "uh": ub[3] - ub[1],
                         "ux": ub[0], "uy": ub[1]}
    json.dump(out, io.open(os.path.join(DATA, "buttons.json"), "w", encoding="utf-8"),
              ensure_ascii=False, sort_keys=True)
    print("按钮悬停贴图：%d 个，共 %.1f MB" % (len(out), total / 1048576.0))


# ---------------------------------------------------------------- 2. 被盖住的文本框
def build_hidden():
    cache = {}

    def img(name):
        if name not in cache:
            cache[name] = np.asarray(Image.open(os.path.join(BG, name + ".webp")).convert("RGB")).astype(np.int16)
            if len(cache) > 24:
                cache.pop(next(iter(cache)))
        return cache[name]

    def boxmap(n):
        return {i.get("var"): [float(v) for v in i["box"]]
                for i in (ui.get(str(n)) or []) if i.get("k") == "et"}

    ranges = []
    for i in range(len(beats)):
        lo = beats[i]
        hi = beats[i + 1] - 1 if i + 1 < len(beats) else 4907
        ranges.append((lo, hi, bgs.get(str(lo)), bgs.get(str(beats[i - 1])) if i else None))

    hidden = {}
    for (lo, hi, fg, pg) in ranges:
        if fg is None or pg is None or fg == pg:
            continue
        A = img(fg)
        D = np.abs(A - img(pg)).max(axis=2) > 16
        prev = boxmap(beats[beats.index(lo) - 1]) if lo in beats and beats.index(lo) > 0 else {}
        for n in [lo] + [f for f in range(lo + 1, hi + 1) if ui.get(str(f))]:
            cur = boxmap(n)
            hit = [v for v, b in cur.items()
                   if v in prev and prev[v] == b and _covered(D, b)]
            if hit:
                hidden[str(n)] = sorted(hit)
    json.dump(hidden, io.open(os.path.join(DATA, "hidden.json"), "w", encoding="utf-8"),
              ensure_ascii=False, sort_keys=True)
    print("需要藏起来的文本框：%d 帧，涉及 %d 个" % (len(hidden), sum(len(v) for v in hidden.values())))


def _covered(D, b):
    x0 = max(0, int(round(b[0])))
    y0 = max(0, int(round(b[1])))
    x1 = min(800, int(round(b[0] + b[2])))
    y1 = min(600, int(round(b[1] + b[3])))
    if x1 - x0 < 4 or y1 - y0 < 4:
        return False
    return float(D[y0:y1, x0:x1].mean()) > 0.9


build_buttons()
build_hidden()
