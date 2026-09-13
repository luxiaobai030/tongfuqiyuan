# -*- coding: utf-8 -*-
import os, sys, zlib
from PIL import Image
d = sys.argv[1]
print("%-32s %-14s %-8s %-24s %s" % ("文件","尺寸","模式","主色","说明"))
print("-"*104)
for f in sorted(os.listdir(d)):
    p = os.path.join(d, f)
    sz = os.path.getsize(p)
    try:
        if f.endswith((".jpg",".png")):
            im = Image.open(p).convert("RGBA")
            w,h = im.size
            small = im.resize((16,16))
            px = list(small.getdata())
            ar = sum(1 for r,g,b,a in px if a > 32) / len(px)
            avg = tuple(sum(c[i] for c in px)//len(px) for i in range(3))
            note = []
            if ar < 0.98: note.append("有透明 %.0f%%实心" % (ar*100))
            if w*h >= 400*300: note.append("大图(可能背景)")
            if abs(w-h) < 6 and w < 200: note.append("方形(可能图标/头像)")
            print("%-32s %-14s %-8s #%02x%02x%02x%-16s %s" % (f, "%dx%d"%(w,h), im.mode, avg[0],avg[1],avg[2], "", " ".join(note)))
        elif f.endswith(".alpha"):
            print("%-32s %-14s %-8s %-24s alpha通道 %d 字节" % (f, "-", "-", "", sz))
        elif f.endswith(".z"):
            raw = zlib.decompress(open(p,"rb").read())
            print("%-32s %-14s %-8s %-24s zlib 解开 %d 字节（loss3 待解）" % (f, "-", "-", "", len(raw)))
    except Exception as e:
        print("%-32s 读取失败: %s" % (f, e))
