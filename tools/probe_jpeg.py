# -*- coding: utf-8 -*-
import struct, sys, io, os
from PIL import Image
buf = open(sys.argv[1],"rb").read()
p = 0; nb = buf[0]>>3; p += (5+nb*4+7)//8 + 4
tags = []
while p < len(buf)-2:
    rh = struct.unpack_from("<H", buf, p)[0]; p += 2
    code = rh>>6; ln = rh & 0x3F
    if ln == 0x3F: ln = struct.unpack_from("<I", buf, p)[0]; p += 4
    if code == 0: break
    tags.append((code, p, ln)); p += ln

def try_jpeg(d, label):
    s = d.find(b"\xff\xd8")
    e = d.rfind(b"\xff\xd9")
    if s < 0: print("  %s 找不到 SOI" % label); return
    variants = {"到文件尾": d[s:], "到EOI": d[s:e+2] if e > s else d[s:]}
    for name, blob in variants.items():
        try:
            im = Image.open(io.BytesIO(blob))
            im.load()
            print("  %-24s %-9s %sx%s %s  (总长%d, 用%s)" % (label, name, im.size[0], im.size[1], im.mode, len(d), name))
            return blob
        except Exception as ex:
            print("  %-24s %-9s 失败: %s" % (label, name, ex))

for code, off, ln in tags:
    if code == 6:
        cid = struct.unpack_from("<H", buf, off)[0]
        print("DefineBits id=%d 前8字节: %s" % (cid, " ".join("%02X"%x for x in buf[off+2:off+10])))
        try_jpeg(buf[off+2:off+ln], "id%d" % cid)
    elif code == 21:
        cid = struct.unpack_from("<H", buf, off)[0]
        d = buf[off+2:off+ln]
        print("JPEG2 id=%d tagLen=%d 前8字节: %s 尾8: %s" % (cid, ln, " ".join("%02X"%x for x in d[:8]), " ".join("%02X"%x for x in d[-8:])))
        try_jpeg(d, "id%d" % cid)
