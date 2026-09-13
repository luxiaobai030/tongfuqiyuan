# -*- coding: utf-8 -*-
"""生成 Godot 资源：去重背景 + 文字图层 + UI 数据"""
import os, io, sys, json, hashlib, shutil
sys.stdout.reconfigure(encoding="utf-8")
import numpy as np
from PIL import Image

B = r"F:\路小白。。\一些尝试\游戏\同福奇缘_移植"
DEC = os.path.join(B, "decompiled")
OUT = os.path.join(B, "game", "assets")
os.makedirs(os.path.join(OUT, "bg"), exist_ok=True)
os.makedirs(os.path.join(OUT, "txt"), exist_ok=True)
os.makedirs(os.path.join(B, "game", "data"), exist_ok=True)

diff = {int(k): v for k, v in json.load(io.open(os.path.join(DEC,"_frame_diff.json"), encoding="utf-8")).items()}
beats = json.load(io.open(os.path.join(DEC,"_beats.json")))

# 需要出货的帧：所有"节拍"帧
want = sorted(set(beats))
print("beats:", len(want))

bg_by_sig = {}     # art sig -> bg file id
bg_map = {}        # frame -> bg id
txt_map = {}       # frame -> [x, y, txtfile] (文字图层)
total_bg = 0; total_txt = 0

def sig_of(img):
    g = np.asarray(img.convert("L").resize((100,75), Image.BILINEAR)).astype(np.int16)
    return hashlib.md5((g//6).astype(np.uint8).tobytes()).hexdigest()[:12]

for n in want:
    cp = os.path.join(DEC, "frames_clean", "%d.png" % n)
    fp = os.path.join(DEC, "frames", "%d.png" % n)
    if not os.path.exists(cp): continue
    cim = Image.open(cp).convert("RGB")
    s = sig_of(cim)
    if s not in bg_by_sig:
        bid = "b%04d" % len(bg_by_sig)
        bg_by_sig[s] = bid
        p = os.path.join(OUT, "bg", bid + ".webp")
        cim.save(p, "WEBP", quality=90, method=5)
        total_bg += os.path.getsize(p)
    bg_map[n] = bg_by_sig[s]
    # 文字图层
    A = np.asarray(Image.open(fp).convert("RGB"))
    C = np.asarray(cim)
    if A.shape == C.shape:
        d = np.abs(A.astype(np.int16)-C.astype(np.int16)).max(axis=2)
        mask = d > 24
        if mask.any():
            ys, xs = np.nonzero(mask)
            x0, y0, x1, y1 = int(xs.min()), int(ys.min()), int(xs.max())+1, int(ys.max())+1
            sub = A[y0:y1, x0:x1]
            m = mask[y0:y1, x0:x1]
            rgba = np.dstack([sub, (m*255).astype(np.uint8)])
            tim = Image.fromarray(rgba, "RGBA")
            # 尽量裁掉纯透明列/行
            bbox = tim.getbbox()
            if bbox:
                tim = tim.crop(bbox)
                x0 += bbox[0]; y0 += bbox[1]
                p = os.path.join(OUT, "txt", "%d.webp" % n)
                tim.save(p, "WEBP", quality=92, method=5)
                total_txt += os.path.getsize(p)
                txt_map[n] = [x0, y0]
print("unique bg:", len(bg_by_sig), "bg bytes: %.1f MB" % (total_bg/1048576))
print("txt layers:", len(txt_map), "txt bytes: %.1f MB" % (total_txt/1048576))
json.dump({"bg": bg_map, "txt": txt_map}, io.open(os.path.join(B,"game","data","frames.json"),"w",encoding="utf-8"))
