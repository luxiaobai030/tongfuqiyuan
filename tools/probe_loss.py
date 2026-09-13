# -*- coding: utf-8 -*-
import struct, zlib, sys
buf = open(sys.argv[1],"rb").read()
p = 0; nb = buf[0]>>3; p += (5+nb*4+7)//8 + 4
tags = []
while p < len(buf)-2:
    rh = struct.unpack_from("<H", buf, p)[0]; p += 2
    code = rh>>6; ln = rh & 0x3F
    if ln == 0x3F: ln = struct.unpack_from("<I", buf, p)[0]; p += 4
    if code == 0: break
    tags.append((code, p, ln)); p += ln

for code, off, ln in tags:
    if code == 36:
        cid = struct.unpack_from("<H", buf, off)[0]
        fmt = buf[off+2]
        w = struct.unpack_from("<H", buf, off+3)[0]
        h = struct.unpack_from("<H", buf, off+5)[0]
        print("\nid=%d  fmt=%d  %dx%d  tagLen=%d" % (cid, fmt, w, h, ln))
        print("  头部 off+0..+15: %s" % " ".join("%02X"%x for x in buf[off:off+16]))
        for delta in range(6, 20):
            q = off + delta
            if q + 2 > len(buf): break
            try:
                raw = zlib.decompressobj().decompress(buf[q:off+ln])
                # 判断解出来是不是完整
                exp_a = ((w+3)//4*4) * h          # 8bit 索引
                exp_b = ((w*2+3)//4*4) * h        # 16bit
                exp_c = ((w*4+3)//4*4) * h        # 32bit
                mark = ""
                if abs(len(raw)-exp_a) < 8: mark = "  <= 匹配 8bit索引"
                elif abs(len(raw)-exp_b) < 8: mark = "  <= 匹配 15/16bit"
                elif abs(len(raw)-exp_c) < 8: mark = "  <= 匹配 32bit"
                print("   delta=%-3d 解开 %-7d 字节%s" % (delta, len(raw), mark))
            except Exception:
                pass
