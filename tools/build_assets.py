# -*- coding: utf-8 -*-
"""生成 Godot 画面资源：背景层（去重）+ 画面索引

规则（关键）：
1. 背景层 = decompiled/frames，也就是**原版逐帧整幅画面**：人物动画、静态美术字
   全都烧在画面里，和原版播放时看到的完全一样。
   （曾经试过把角色抠成独立动画层单独播，人物能看到「停帧时继续动」，但角色是画在
   整幅画面**上面**的一层，会把原版里叠在角色之上的按钮文字盖住，战斗里「先机/后发」
   就容易点不到；按用户要求改回原来这种「烧进画面」的方案。）
2. 逐帧做精确像素比较去重：只有整幅画面和上一个关键帧完全一样时才合并。
   旧版用模糊缩略图比较，战斗里人物移动/出招这类「只有局部在变」的帧会被
   误判成没变，画面就卡住不动了。
3. 静态美术字本来就在画面里，所以不用单独切文字图层，也不用再叠一层。
"""
import os, io, sys, json, hashlib
sys.stdout.reconfigure(encoding="utf-8")
from PIL import Image

B = r"F:\路小白。。\一些尝试\游戏\同福奇缘_移植"
DEC = os.path.join(B, "decompiled")
SRC = os.path.join(DEC, "frames")
OUT = os.path.join(B, "game", "assets")
BG = os.path.join(OUT, "bg")
DATA = os.path.join(B, "game", "data")
for d in (BG, DATA):
    os.makedirs(d, exist_ok=True)

# 清空旧的背景图层（连同 .import 一起删掉，避免残留文件被打包）
for f in os.listdir(BG):
    os.remove(os.path.join(BG, f))

TOTAL = 4907

beats = []
bg_by_sig = {}
bg_map = {}
prev_sig = None
bg_bytes = 0
skipped = []

for n in range(1, TOTAL + 1):
    p = os.path.join(SRC, "%d.png" % n)
    if not os.path.exists(p):
        skipped.append(n)
        continue
    im = Image.open(p).convert("RGB")
    sig = hashlib.md5(im.tobytes()).hexdigest()
    if sig == prev_sig:
        continue
    prev_sig = sig
    beats.append(n)

    if sig not in bg_by_sig:
        bid = "b%04d" % len(bg_by_sig)
        bg_by_sig[sig] = bid
        q = os.path.join(BG, bid + ".webp")
        im.save(q, "WEBP", lossless=True, method=0)
        bg_bytes += os.path.getsize(q)
    bg_map[n] = bg_by_sig[sig]

    if n % 500 == 0:
        print("  ... %d/%d  关键帧=%d 背景=%d" % (n, TOTAL, len(beats), len(bg_by_sig)), flush=True)

json.dump(beats, io.open(os.path.join(DATA, "beats.json"), "w"))
json.dump({"bg": bg_map}, io.open(os.path.join(DATA, "frames.json"), "w", encoding="utf-8"))

print("缺图帧:", skipped)
print("关键帧:", len(beats))
print("唯一背景:", len(bg_by_sig), "  %.1f MB" % (bg_bytes / 1048576))
