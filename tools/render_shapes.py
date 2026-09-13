# -*- coding: utf-8 -*-
"""SWF 矢量图形光栅化器（SHAPE / SHAPE2 / SHAPE3）"""
import struct, os, sys, glob
from PIL import Image, ImageDraw

buf = open(sys.argv[1],"rb").read()
OUT = sys.argv[2]
os.makedirs(OUT, exist_ok=True)
for f in glob.glob(os.path.join(OUT,"*.png")): os.remove(f)

class BR:
    def __init__(self, data, pos):
        self.d = data; self.p = pos * 8
    def bits(self, n):
        v = 0
        for _ in range(n):
            byte = self.p >> 3
            if byte >= len(self.d): return 0
            bit = 7 - (self.p & 7)
            v = (v << 1) | ((self.d[byte] >> bit) & 1)
            self.p += 1
        return v
    def sbits(self, n):
        if n == 0: return 0
        v = self.bits(n)
        if v & (1 << (n-1)): v -= (1 << n)
        return v
    def align(self):
        self.p = (self.p + 7) & ~7

def rgb(d, p, alpha):
    if alpha: return (d[p], d[p+1], d[p+2], d[p+3]), p+4
    return (d[p], d[p+1], d[p+2], 255), p+3

def read_fillstyles(d, p, alpha):
    n = d[p]; p += 1
    if n == 0xFF: n = struct.unpack_from("<H", d, p)[0]; p += 2
    styles = []
    for _ in range(n):
        t = d[p]; p += 1
        if t == 0x00:
            c, p = rgb(d, p, alpha); styles.append(("solid", c))
        elif t in (0x10, 0x12, 0x13):
            m = struct.unpack_from("<B", d, p)[0]; p += 1
            g = None
            if t == 0x13: g, p = rgb(d, p, alpha)
            stops = struct.unpack_from("<B", d, p)[0]; p += 1
            cols = []
            for _ in range(stops):
                off = struct.unpack_from("<B", d, p)[0]; p += 1
                c, p = rgb(d, p, alpha); cols.append(c)
            styles.append(("grad", cols[len(cols)//2] if cols else (128,128,128,255)))
        elif t in (0x40, 0x41, 0x42, 0x43):
            p += 2
            m = struct.unpack_from("<H", d, p)[0]  # matrix (skip, 粗略)
            p += matrix_len(d, p)
            styles.append(("bmp", (150, 150, 150, 255)))
        else:
            styles.append(("?", (120,120,120,255)))
    return styles, p

def read_linestyles(d, p, alpha):
    n = d[p]; p += 1
    if n == 0xFF: n = struct.unpack_from("<H", d, p)[0]; p += 2
    styles = []
    for _ in range(n):
        w = struct.unpack_from("<H", d, p)[0]; p += 2
        c, p = rgb(d, p, alpha)
        styles.append((w, c))
    return styles, p

def matrix_len(d, p):
    b = BR(d, 0); b.p = p*8
    hs = b.bits(5)
    if hs:
        nb = b.bits(5); b.sbits(nb); b.sbits(nb)
        nb = b.bits(5); b.sbits(nb); b.sbits(nb)
    ns = b.bits(5)
    if ns:
        nb = b.bits(5); b.sbits(nb); b.sbits(nb)
    return (b.p + 7)//8 - p

def parse_shape(d, off, ln, tagcode):
    alpha = (tagcode == 32)
    p = off + 2                      # 跳过 shapeId
    nb = d[p] >> 3
    p += (5 + nb*4 + 7)//8           # RECT
    fills, p = read_fillstyles(d, p, alpha)
    lines, p = read_linestyles(d, p, alpha)
    if tagcode in (22, 32, 83):
        fb = d[p] >> 4; lb = d[p] & 0x0F; p += 1
    else:
        fb = 4; lb = 4
    b = BR(d, 0); b.p = p*8

    paths = []          # [(fill_idx, [(x,y),...])]
    cur = None
    x = y = 0
    fill0 = fill1 = 0
    line = 0
    color_override = None
    def start(fi):
        return [(x, y)]
    while True:
        if b.p >> 3 >= off + ln: break
        if b.bits(1) == 0:                     # 样式变更
            flags = b.bits(5)
            if flags & 0x01:                   # MoveTo
                mb = b.bits(5)
                x = b.sbits(mb); y = b.sbits(mb)
            if flags & 0x02: fill0 = b.bits(fb)
            if flags & 0x04: fill1 = b.bits(fb)
            if flags & 0x08: line  = b.bits(lb)
            toclose = (flags & 0x01) != 0 or (flags & 0x02) or (flags & 0x04) or (flags & 0x08)
            if toclose and cur and len(cur[1]) > 2:
                paths.append(cur)
            fi = fill1 if fill1 else fill0
            cur = (fi, [(x, y)]) if fi else None
            if flags & 0x10:                   # NewStyles
                fills, p2 = read_fillstyles(d, b.p//8, alpha)
                lines, p2 = read_linestyles(d, p2, alpha)
                fb = d[p2] >> 4; lb = d[p2] & 0x0F
                b.p = (p2+1)*8
        else:
            if b.bits(1) == 1:                 # StraightEdge
                nbits = b.bits(4) + 2
                if b.bits(1):                  # GeneralLine
                    dx = b.sbits(nbits); dy = b.sbits(nbits)
                else:
                    if b.bits(1): dx = 0; dy = b.sbits(nbits)
                    else: dx = b.sbits(nbits); dy = 0
                x += dx; y += dy
                if cur is None: cur = (fill1 or fill0, [(x-dx, y-dy)])
                cur[1].append((x, y))
            else:                              # CurvedEdge
                nbits = b.bits(4) + 2
                cx = b.sbits(nbits); cy = b.sbits(nbits)
                ax = b.sbits(nbits); ay = b.sbits(nbits)
                x0, y0 = x, y
                xc, yc = x + cx, y + cy
                xa, ya = xc + ax, yc + ay
                if cur is None: cur = (fill1 or fill0, [(x0, y0)])
                for i in range(1, 9):
                    t = i / 8.0
                    px = (1-t)**2*x0 + 2*(1-t)*t*xc + t*t*xa
                    py = (1-t)**2*y0 + 2*(1-t)*t*yc + t*t*ya
                    cur[1].append((px, py))
                x, y = xa, ya
    if cur and len(cur[1]) > 2: paths.append(cur)
    return paths, fills, lines

# 收集所有图形标签（含 sprite 内）
p = 0; nb0 = buf[0]>>3; p += (5+nb0*4+7)//8 + 4
shapes = []
def walk(start, end, depth):
    q = start
    while q < end - 2:
        rh = struct.unpack_from("<H", buf, q)[0]; q += 2
        code = rh >> 6; ln = rh & 0x3F
        if ln == 0x3F: ln = struct.unpack_from("<I", buf, q)[0]; q += 4
        if code == 0: break
        if code in (2, 22, 32, 83):
            shapes.append((code, q, ln))
        elif code == 39 and depth < 3:
            walk(q+4, q+ln, depth+1)
        q += ln
walk(p, len(buf), 0)
print("图形标签数: %d" % len(shapes))

MARGIN = 4
ok = 0
for code, off, ln in shapes:
    try:
        sid = struct.unpack_from("<H", buf, off)[0]
        paths, fills, lines = parse_shape(buf, off, ln, code)
        if not paths: continue
        xs = [pt[0] for _, pts in paths for pt in pts]
        ys = [pt[1] for _, pts in paths for pt in pts]
        if not xs: continue
        minx, maxx = min(xs), max(xs); miny, maxy = min(ys), max(ys)
        w = maxx-minx; h = maxy-miny
        if w <= 0 or h <= 0 or w > 4000 or h > 4000: continue
        img = Image.new("RGBA", (int(w)+MARGIN*2, int(h)+MARGIN*2), (0,0,0,0))
        dr = ImageDraw.Draw(img)
        for fi, pts in paths:
            if not pts: continue
            col = (128,128,128,255)
            if fi and 0 < fi <= len(fills):
                st = fills[fi-1]
                col = st[1] if st[0] in ("solid","grad","bmp") else (128,128,128,255)
            poly = [((px-minx)+MARGIN, (py-miny)+MARGIN) for px, py in pts]
            try: dr.polygon(poly, fill=col)
            except Exception: pass
        # 描边
        for w_, c in lines:
            for fi, pts in paths:
                if len(pts) < 2: continue
                poly = [((px-minx)+MARGIN, (py-miny)+MARGIN) for px, py in pts]
                try: dr.line(poly, fill=c, width=max(1,int(w_)), joint="curve")
                except Exception: pass
        img.save(os.path.join(OUT, "shape%05d_id%d.png" % (off, sid)))
        ok += 1
    except Exception as e:
        pass
print("渲染出 %d 张矢量图 -> %s" % (ok, OUT))
