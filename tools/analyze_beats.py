# -*- coding: utf-8 -*-
"""分析：原版逐帧画面里，哪些帧真的在变（精确像素比较）"""
import os, io, sys, json, hashlib
sys.stdout.reconfigure(encoding="utf-8")
import numpy as np
from PIL import Image

DEC = r"F:\路小白。。\一些尝试\游戏\同福奇缘_移植\decompiled"
CLEAN = os.path.join(DEC, "frames_clean")
FULL = os.path.join(DEC, "frames")

clean_sig = {}
text_sig = {}
for n in range(1, 4908):
    cp = os.path.join(CLEAN, "%d.png" % n)
    fp = os.path.join(FULL, "%d.png" % n)
    if not os.path.exists(cp) or not os.path.exists(fp):
        clean_sig[n] = "miss%d" % n
        text_sig[n] = "miss%d" % n
        continue
    C = np.asarray(Image.open(cp).convert("RGB"))
    A = np.asarray(Image.open(fp).convert("RGB"))
    clean_sig[n] = hashlib.md5(C.tobytes()).hexdigest()[:12]
    if A.shape == C.shape:
        d = np.abs(A.astype(np.int16) - C.astype(np.int16)).max(axis=2)
        mask = d > 24
        if mask.any():
            ys, xs = np.nonzero(mask)
            key = "%d,%d,%d,%d|" % (int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max()))
            key += hashlib.md5(np.ascontiguousarray(A[mask])).hexdigest()[:12]
            text_sig[n] = key
        else:
            text_sig[n] = ""
    else:
        text_sig[n] = "shape"
    if n % 500 == 0:
        print("...", n, flush=True)

old = set(json.load(io.open(os.path.join(DEC, "_beats.json"), encoding="utf-8")))
new = []
prev = None
for n in range(1, 4908):
    k = (clean_sig[n], text_sig[n])
    if k != prev:
        new.append(n)
        prev = k
print("新关键帧数量:", len(new), " 旧:", len(old))
added = [n for n in new if n not in old]
print("新增帧数:", len(added), " 前 40:", added[:40])
art_changed = [n for n in range(2, 4908) if clean_sig[n] != clean_sig[n-1]]
print("画面(美术层)每帧都在变的帧数:", len(art_changed), "其中旧表漏掉的:", len([n for n in art_changed if n not in old]))
print("相邻两帧完全相同的美术帧数:", 4906 - len(art_changed))
uniq_bg_new = len(set(clean_sig[n] for n in new))
uniq_bg_old_sig = len(set(clean_sig[n] for n in sorted(old)))
print("新方案唯一背景数:", uniq_bg_new, " 旧方案(按帧去重):", uniq_bg_old_sig)
print("新方案带文字层的帧数:", len([n for n in new if text_sig[n] not in ("",) and not text_sig[n].startswith("miss") and text_sig[n] != "shape"]))
json.dump(new, io.open(os.path.join(DEC, "_beats_new.json"), "w"))
print("已写出 _beats_new.json")