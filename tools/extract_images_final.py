# -*- coding: utf-8 -*-
"""SWF 位图提取 —— 最终版"""
import struct, zlib, os, sys, glob, io
from PIL import Image

BODY, OUT = sys.argv[1], sys.argv[2]
buf = open(BODY,"rb").read()
os.makedirs(OUT, exist_ok=True)
for f in glob.glob(os.path.join(OUT,"*")): os.remove(f)

def jpeg_start(d):
    i = 0
    while True:
        i = d.find(b"\xff\xd8", i)
        if i < 0: return None
        if len(d) > i+3 and d[i+2] == 0xFF and d[i+3] not in (0xD8, 0xD9): return i
        i += 2

def jpeg_len(d):
    i = 0
    while i+1 < len(d):
        if d[i] != 0xFF: i += 1; continue
        m = d[i+1]
        if m == 0xD9: return i+2
        if m == 0xD8 or 0xD0 <= m <= 0xD7: i += 2; continue
        if m == 0xDA:
            j = i+2+struct.unpack(">H", d[i+2:i+4])[0]
            while j+1 < len(d):
                if d[j] == 0xFF and d[j+1] == 0xD9: return j+2
                j += 1
            return len(d)
        ln = struct.unpack(">H", d[i+2:i+4])[0]; i += 2 + ln
    return len(d)

p = 0; nb = buf[0]>>3; p += (5+nb*4+7)//8 + 4
tags = []
while p < len(buf)-2:
    rh = struct.unpack_from("<H", buf, p)[0]; p += 2
    code = rh>>6; ln = rh & 0x3F
    if ln == 0x3F: ln = struct.unpack_from("<I", buf, p)[0]; p += 4
    if code == 0: break
    tags.append((code, p, ln)); p += ln

jt = None
for c,o,l in tags:
    if c == 8: jt = buf[o:o+l]
jt_body = b""
if jt:
    e = jt.rfind(b"\xff\xd9")
    jt_body = jt[2:e] if e > 2 else b""
print("JPEGTables 表体: %d 字节" % len(jt_body))

def open_jpeg(blob):
    s = jpeg_start(blob)
    if s is None: raise ValueError("无 SOI")
    n = jpeg_len(blob[s:])
    im = Image.open(io.BytesIO(blob[s:s+n]))
    im.load()
    return im

def stride8(w): return (w + 3) & ~3
made = []

for code, off, ln in tags:
    try:
        if code == 6:
            cid = struct.unpack_from("<H", buf, off)[0]
            d = buf[off+2:off+ln]
            im = None
            for cand, tag in ((jt_body + d[2:], "拼表"), (d, "原样")):
                try: im = open_jpeg(cand); break
                except Exception: pass
            if im is None: raise ValueError("两种拼法都失败")
            im.save(os.path.join(OUT,"id%04d_definebits.png" % cid))
            made.append(("DefineBits", cid, im.size))
        elif code == 21:
            cid = struct.unpack_from("<H", buf, off)[0]
            d = buf[off+2:off+ln]
            if d[:8] == b"\x89PNG\r\n\x1a\n":
                im = Image.open(io.BytesIO(d)); k = "PNG"
            else:
                im = open_jpeg(d); k = "JPEG2"
            im.save(os.path.join(OUT,"id%04d_jpeg2.png" % cid))
            made.append((k, cid, im.size))
        elif code == 35:
            cid = struct.unpack_from("<H", buf, off)[0]
            aoff = struct.unpack_from("<I", buf, off+2)[0]
            im = open_jpeg(buf[off+6:off+6+aoff]).convert("RGB")
            w,h = im.size
            alpha = zlib.decompress(buf[off+6+aoff:off+ln])
            a = Image.frombytes("L",(w,h), alpha[:w*h].ljust(w*h, b"\xff"))
            rgba = im.convert("RGBA"); rgba.putalpha(a)
            rgba.save(os.path.join(OUT,"id%04d_jpeg3.png" % cid))
            made.append(("JPEG3", cid, im.size))
        elif code in (20, 36):
            cid = struct.unpack_from("<H", buf, off)[0]
            fmt = buf[off+2]
            w = struct.unpack_from("<H", buf, off+3)[0]
            h = struct.unpack_from("<H", buf, off+5)[0]
            wa = (code == 36)
            q = off + 7; ncol = 0
            if fmt == 3:
                ncol = buf[q] + 1; q += 1
            raw = zlib.decompress(buf[q:off+ln])
            if fmt == 3:
                csz = 4 if wa else 3
                tb = raw[:ncol*csz]; px = raw[ncol*csz:]
                st = stride8(w); out = bytearray(w*h*4)
                for y in range(h):
                    for x in range(w):
                        k2 = y*st + x
                        if k2 >= len(px): break
                        idx = px[k2]; o = (y*w+x)*4
                        if wa: out[o:o+4] = tb[idx*4:idx*4+4]
                        else:
                            out[o:o+3] = tb[idx*3:idx*3+3]; out[o+3] = 255
                img = Image.frombytes("RGBA",(w,h),bytes(out))
            elif fmt == 5:
                if wa:
                    img = Image.frombytes("RGBA",(w,h), raw[:w*h*4])
                else:
                    st = (w*3+3)&~3; b = bytearray()
                    for y in range(h):
                        for x in range(w):
                            i2 = y*st+x*3
                            b += bytes((raw[i2],raw[i2+1],raw[i2+2],255))
                    img = Image.frombytes("RGBA",(w,h),bytes(b))
            elif fmt == 4:
                st = (w*2+3)&~3; out = bytearray(w*h*4)
                for y in range(h):
                    for x in range(w):
                        v = struct.unpack_from(">H", raw, y*st+x*2)[0]
                        o = (y*w+x)*4
                        out[o]   = ((v>>10)&31)*255//31
                        out[o+1] = ((v>>5)&31)*255//31
                        out[o+2] = (v&31)*255//31
                        out[o+3] = (0 if (v&0x8000)==0 else 255) if wa else 255
                img = Image.frombytes("RGBA",(w,h),bytes(out))
            else: continue
            img.save(os.path.join(OUT,"id%04d_loss%d.png" % (cid,fmt)))
            made.append(("Lossless%d"%fmt, cid, (w,h)))
    except Exception as e:
        print("  [失败] code=%d off=%d : %s" % (code, off, e))

print("\n成功 %d 张：\n" % len(made))
for k,cid,sz in sorted(made, key=lambda x:-(x[2][0]*x[2][1])):
    print("  %-12s %-11s id=%d" % (k, "%dx%d"%sz, cid))
