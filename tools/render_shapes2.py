# -*- coding: utf-8 -*-
"""SWF 矢量图形光栅化器 v2（带死循环保护）"""
import struct, os, sys, glob, time
from PIL import Image, ImageDraw

BODY = sys.argv[1]; OUT = sys.argv[2]
LIMIT = int(sys.argv[3]) if len(sys.argv) > 3 else 99999
buf = open(BODY,"rb").read()
os.makedirs(OUT, exist_ok=True)

class BR:
    __slots__ = ("d","p")
    def __init__(self, data, bytepos): self.d = data; self.p = bytepos*8
    def bits(self, n):
        v = 0; d = self.d; p = self.p
        for _ in range(n):
            byte = p >> 3
            if byte >= len(d): self.p = p + n; return v
            v = (v << 1) | ((d[byte] >> (7 - (p & 7))) & 1)
            p += 1
        self.p = p
        return v
    def sbits(self, n):
        if n == 0: return 0
        v = self.bits(n)
        if v & (1 << (n-1)): v -= (1 << n)
        return v

def rgb(d, p, a):
    if a: return (d[p],d[p+1],d[p+2],d[p+3]), p+4
    return (d[p],d[p+1],d[p+2],255), p+3

def mat_len(d, p):
    q = p; b = BR(d,0); b.p = p*8
    if b.bits(5):
        nb = b.bits(5); b.sbits(nb); b.sbits(nb); nb = b.bits(5); b.sbits(nb); b.sbits(nb)
    if b.bits(5):
        nb = b.bits(5); b.sbits(nb); b.sbits(nb)
    return (b.p+7)//8 - p

def read_fills(d, p, a):
    n = d[p]; p += 1
    if n == 0xFF: n = struct.unpack_from("<H", d, p)[0]; p += 2
    out = []
    for _ in range(n):
        if p >= len(d): break
        t = d[p]; p += 1
        if t == 0: c,p = rgb(d,p,a); out.append(("s",c))
        elif t in (0x10,0x12,0x13):
            p += 1
            if t == 0x13: _,p = rgb(d,p,a)
            k = d[p]; p += 1; cols = []
            for _ in range(k):
                p += 1; c,p = rgb(d,p,a); cols.append(c)
            out.append(("g", cols[len(cols)//2] if cols else (128,128,128,255)))
        elif t in (0x40,0x41,0x42,0x43):
            p += 2; p += mat_len(d,p); out.append(("b",(150,150,150,255)))
        else: out.append(("?",(120,120,120,255)))
    return out, p

def read_lines(d, p, a):
    n = d[p]; p += 1
    if n == 0xFF: n = struct.unpack_from("<H", d, p)[0]; p += 2
    out = []
    for _ in range(n):
        if p+2 >= len(d): break
        w = struct.unpack_from("<H", d, p)[0]; p += 2
        c, p = rgb(d, p, a); out.append((w,c))
    return out, p

def parse(d, off, ln, code):
    a = (code == 32)
    p = off + 2
    nb = d[p] >> 3; p += (5 + nb*4 + 7)//8
    fills, p = read_fills(d, p, a)
    lines, p = read_lines(d, p, a)
    if code in (22, 32, 83):
        fb = d[p] >> 4; lb = d[p] & 15; p += 1
    else: fb = 4; lb = 4
    b = BR(d, 0); b.p = p*8
    endbit = (off+ln)*8
    paths = []; cur = None
    x = y = 0; f0 = f1 = 0
    iters = 0; stall = 0; lastp = b.p
    while b.p < endbit:
        iters += 1
        if iters > 200000: break
        if b.p <= lastp: stall += 1
        else: stall = 0
        lastp = b.p
        if stall > 100: break
        if b.bits(1) == 0:
            fl = b.bits(5)
            if fl & 0x01:
                mb = b.bits(5); x = b.sbits(mb); y = b.sbits(mb)
            if fl & 0x02: f0 = b.bits(fb)
            if fl & 0x04: f1 = b.bits(fb)
            if fl & 0x08: b.bits(lb)
            if cur and len(cur[1]) > 2: paths.append(cur)
            fi = f1 if f1 else f0
            cur = (fi, [(x,y)]) if fi else None
            if fl & 0x10:
                p2 = b.p // 8
                nf, p2 = read_fills(d, p2, a)
                nl, p2 = read_lines(d, p2, a)
                if p2 > b.p//8:
                    fills, lines = nf, nl
                    fb = d[p2] >> 4; lb = d[p2] & 15
                    b.p = (p2+1)*8
                else:
                    break
        else:
            if b.bits(1) == 1:
                n = b.bits(4) + 2
                if b.bits(1): dx = b.sbits(n); dy = b.sbits(n)
                elif b.bits(1): dx = 0; dy = b.sbits(n)
                else: dx = b.sbits(n); dy = 0
                if cur is None: cur = (f1 or f0, [(x,y)])
                x += dx; y += dy
                if len(cur[1]) < 6000: cur[1].append((x,y))
            else:
                n = b.bits(4) + 2
                cx = b.sbits(n); cy = b.sbits(n); ax = b.sbits(n); ay = b.sbits(n)
                x0,y0 = x,y; xc,yc = x+cx,y+cy; xa,ya = xc+ax,yc+ay
                if cur is None: cur = (f1 or f0, [(x0,y0)])
                if len(cur[1]) < 6000:
                    for i in range(1, 6):
                        t = i/5.0
                        cur[1].append(((1-t)**2*x0 + 2*(1-t)*t*xc + t*t*xa,
                                       (1-t)**2*y0 + 2*(1-t)*t*yc + t*t*ya))
                x,y = xa,ya
    if cur and len(cur[1]) > 2: paths.append(cur)
    return paths, fills, lines

p = 0; n0 = buf[0]>>3; p += (5+n0*4+7)//8 + 4
shapes = []
def walk(s, e, dep):
    q = s
    while q < e-2:
        rh = struct.unpack_from("<H", buf, q)[0]; q += 2
        c = rh>>6; l = rh & 0x3F
        if l == 0x3F: l = struct.unpack_from("<I", buf, q)[0]; q += 4
        if c == 0: break
        if c in (2,22,32,83): shapes.append((c,q,l))
        elif c == 39 and dep < 3: walk(q+4, q+l, dep+1)
        q += l
walk(p, len(buf), 0)
print("图形标签数: %d" % len(shapes))

M = 3; ok = 0; t0 = time.time()
for i, (code, off, ln) in enumerate(shapes[:LIMIT]):
    if time.time() - t0 > 200: print("时间到，停在 %d" % i); break
    try:
        sid = struct.unpack_from("<H", buf, off)[0]
        paths, fills, lines = parse(buf, off, ln, code)
        if not paths: continue
        xs = [q[0] for _,pts in paths for q in pts]; ys = [q[1] for _,pts in paths for q in pts]
        if not xs: continue
        mnx,mxx,mny,mxy = min(xs),max(xs),min(ys),max(ys)
        w = mxx-mnx; h = mxy-mny
        if w <= 0 or h <= 0 or w > 3000 or h > 3000: continue
        img = Image.new("RGBA", (int(w)+M*2, int(h)+M*2), (0,0,0,0))
        dr = ImageDraw.Draw(img)
        for fi, pts in paths:
            if len(pts) < 3: continue
            col = (128,128,128,255)
            if fi and 0 < fi <= len(fills): col = fills[fi-1][1]
            poly = [((px-mnx)+M, (py-mny)+M) for px,py in pts]
            try: dr.polygon(poly, fill=col)
            except Exception: pass
        for w_, c in lines:
            for fi, pts in paths:
                if len(pts) < 2: continue
                poly = [((px-mnx)+M, (py-mny)+M) for px,py in pts]
                try: dr.line(poly, fill=c, width=max(1,int(w_)), joint="curve")
                except Exception: pass
        img.save(os.path.join(OUT, "s%05d_id%d.png" % (i, sid)))
        ok += 1
    except Exception:
        pass
print("渲染 %d / %d 张，用时 %.1f 秒" % (ok, min(LIMIT,len(shapes)), time.time()-t0))
