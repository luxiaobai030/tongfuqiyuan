# -*- coding: utf-8 -*-
"""正确解出 SWF 里全部 5 种位图标签"""
import struct, zlib, os, sys, glob
from PIL import Image

BODY = sys.argv[1]; OUT = sys.argv[2]
buf = open(BODY,"rb").read()
os.makedirs(OUT, exist_ok=True)
for f in glob.glob(os.path.join(OUT,"*")): os.remove(f)

def jpeg_start(d):
    i = 0
    while True:
        i = d.find(b"\xff\xd8", i)
        if i < 0: return None
        if len(d) > i+3 and d[i+2] == 0xFF and d[i+3] not in (0xD8,0xD9): return i
        i += 2

def jpeg_len(d):
    i = jpeg_start(d)
    if i is None: return None
    e = len(d)
    while i+1 < e:
        if d[i] != 0xFF: i += 1; continue
        m = d[i+1]
        if m == 0xD9: return i+2
        if m == 0xD8 or 0xD0 <= m <= 0xD7: i += 2; continue
        if m == 0xDA:
            j = i+2+struct.unpack(">H", d[i+2:i+4])[0]
            while j+1 < e:
                if d[j] == 0xFF and d[j+1] == 0xD9: return j+2
                j += 1
            return e
        ln = struct.unpack(">H", d[i+2:i+4])[0]; i += 2 + ln
    return e

# 找 JPEGTables 和顶层标签
p = 0; nb = buf[0]>>3; p += (5+nb*4+7)//8 + 4
jt = None
tags = []
while p < len(buf)-2:
    rh = struct.unpack_from("<H", buf, p)[0]; p += 2
    code = rh>>6; ln = rh & 0x3F
    if ln == 0x3F: ln = struct.unpack_from("<I", buf, p)[0]; p += 4
    if code == 0: break
    tags.append((code, p, ln)); p += ln
for c,o,l in tags:
    if c == 8: jt = buf[o:o+l]
print("JPEGTables: %d 字节" % (len(jt) if jt else 0))
jt_body = None
if jt:
    e = jt.rfind(b"\xff\xd9")
    jt_body = jt[2:e] if e > 0 else jt[2:]

def padded(w, bpp):
    return (w*bpp + 3) & ~3

def decode_lossless(fmt, w, h, with_alpha, raw):
    """fmt3=色表 4=15bit 5=24bit"""
    out = bytearray(w*h*4)
    if fmt == 3:
        ncol = raw[0] + 1
        csz = 4 if with_alpha else 3
        table = raw[1:1+ncol*csz]
        data = raw[1+ncol*csz:]
        stride = padded(w, 1)
        for y in range(h):
            for x in range(w):
                idx = data[y*stride + x]
                if idx >= ncol: idx = 0
                o = (y*w+x)*4
                if with_alpha:
                    out[o:o+4] = table[idx*4:idx*4+4]
                else:
                    out[o:o+3] = table[idx*3:idx*3+3]; out[o+3] = 255
        return bytes(out)
    if fmt == 4:
        stride = padded(w, 2); i = 0; pos = 0
        for y in range(h):
            i = y*stride
            for x in range(w):
                v = struct.unpack_from(">H", raw, i)[0]; i += 2
                o = (y*w+x)*4
                if with_alpha:
                    a = 0 if (v & 0x8000) == 0 else 255
                    out[o]   = ((v >> 10) & 0x1F) * 255 // 31
                    out[o+1] = ((v >> 5)  & 0x1F) * 255 // 31
                    out[o+2] = (v & 0x1F) * 255 // 31
                    out[o+3] = a
                else:
                    out[o]   = ((v >> 10) & 0x1F) * 255 // 31
                    out[o+1] = ((v >> 5)  & 0x1F) * 255 // 31
                    out[o+2] = (v & 0x1F) * 255 // 31
                    out[o+3] = 255
        return bytes(out)
    if fmt == 5:
        stride = padded(w, 4 if with_alpha else 3)
        for y in range(h):
            i = y*stride
            for x in range(w):
                o = (y*w+x)*4
                if with_alpha:
                    out[o:o+4] = raw[i:i+4]; i += 4
                else:
                    out[o:o+3] = raw[i:i+3]; out[o+3] = 255; i += 3
        return bytes(out)
    return None

made = []
for idx, (code, off, ln) in enumerate(tags):
    try:
        if code == 6:
            cid = struct.unpack_from("<H", buf, off)[0]
            d = buf[off+2:off+ln]
            full = (jt_body or b"") + d
            n = jpeg_len(full)
            im = Image.open(__import__("io").BytesIO(full[:n]))
            im.save(os.path.join(OUT,"id%d_definebits.png" % cid))
            made.append(("definebits", cid, im.size))
        elif code == 21:
            cid = struct.unpack_from("<H", buf, off)[0]
            d = buf[off+2:off+ln]
            if d[:8] == b"\x89PNG\r\n\x1a\n":
                im = Image.open(__import__("io").BytesIO(d)); nm = "id%d_png" % cid
            else:
                s = jpeg_start(d)
                if s is None: continue
                n = jpeg_len(d[s:])
                im = Image.open(__import__("io").BytesIO(d[s:s+n])); nm = "id%d_jpeg2" % cid
            im.save(os.path.join(OUT, nm + ".png"))
            made.append(("jpeg2", cid, im.size))
        elif code == 35:
            cid = struct.unpack_from("<H", buf, off)[0]
            aoff = struct.unpack_from("<I", buf, off+2)[0]
            d = buf[off+6:off+6+aoff]
            s = jpeg_start(d)
            n = jpeg_len(d[s:])
            im = Image.open(__import__("io").BytesIO(d[s:s+n])).convert("RGB")
            alpha = zlib.decompress(buf[off+6+aoff:off+ln])
            w,h = im.size
            a = Image.new("L", (w,h))
            for y in range(h):
                for x in range(w):
                    k = y*w+x
                    a.putpixel((x,y), alpha[k] if k < len(alpha) else 255)
            rgba = im.convert("RGBA"); rgba.putalpha(a)
            rgba.save(os.path.join(OUT,"id%d_jpeg3.png" % cid))
            made.append(("jpeg3", cid, im.size))
        elif code in (20, 36):
            cid = struct.unpack_from("<H", buf, off)[0]
            fmt = buf[off+2]
            w = struct.unpack_from("<H", buf, off+3)[0]
            h = struct.unpack_from("<H", buf, off+5)[0]
            q = off + 7
            pre = b""
            if fmt == 3:
                ncol = buf[q] + 1
                csz = 4 if code == 36 else 3
                n = 1 + ncol*csz
                pre = buf[q:q+n]; q += n
            raw = zlib.decompress(buf[q:off+ln])
            rgba = decode_lossless(fmt, w, h, code == 36, pre + raw)
            if rgba:
                Image.frombytes("RGBA", (w,h), rgba).save(os.path.join(OUT,"id%d_loss%d.png" % (cid,fmt)))
                made.append(("lossless%d"%fmt, cid, (w,h)))
    except Exception as e:
        print("  [跳过] tag%d code=%d : %s" % (idx, code, e))

print("解出 %d 张:" % len(made))
for k, cid, sz in sorted(made):
    print("  %-12s id=%-6d %s" % (k, cid, sz))
