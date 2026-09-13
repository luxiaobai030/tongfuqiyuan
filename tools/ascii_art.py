# -*- coding: utf-8 -*-
import sys
from PIL import Image
def view(path, label, CW=78, CH=30):
    try:
        im = Image.open(path).convert("RGBA")
    except Exception as e:
        print("%s 打不开: %s" % (label, e)); return
    W,H = im.size
    print("\n===== %s  (%dx%d) =====" % (label, W, H))
    bg = Image.new("RGBA", im.size, (255,255,255,255))
    im = Image.alpha_composite(bg, im).convert("RGB")
    sm = im.resize((CW,CH)); px = list(sm.getdata())
    CHARS = " .:-=+*#%@"
    def ch(r,g,b):
        lum = (0.299*r+0.587*g+0.114*b)/255.0
        mx, mn = max(r,g,b), min(r,g,b)
        if mx-mn < 22:
            return CHARS[min(9,int(lum*9.99))]
        if b >= r and b >= g: return "b" if lum<0.5 else "B"
        if r >= g and r >= b: return "r" if lum<0.5 else "R"
        return "g" if lum<0.5 else "G"
    print("  " + "_"*CW)
    for y in range(CH):
        print("  " + "".join(ch(*px[y*CW+x]) for x in range(CW)))
for p, l in [("art/id2122_jpeg2.png","整屏 640x480"),
             ("art/id1303_jpeg2.png","208x175"),
             ("art/id168_jpeg2.png","角色头像 142x142"),
             ("art/id2000_loss3.png","247x136")]:
    view(sys.argv[1] + "/" + p, l)
