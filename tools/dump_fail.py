# -*- coding: utf-8 -*-
import struct, sys
buf = open(sys.argv[1],"rb").read()
p = 0; nb = buf[0]>>3; p += (5+nb*4+7)//8 + 4
tags = []
while p < len(buf)-2:
    rh = struct.unpack_from("<H", buf, p)[0]; p += 2
    code = rh>>6; ln = rh & 0x3F
    if ln == 0x3F: ln = struct.unpack_from("<I", buf, p)[0]; p += 4
    if code == 0: break
    tags.append((code, p, ln)); p += ln

def hexd(b, n=48):
    return " ".join("%02X" % x for x in b[:n])

for code, off, ln in tags:
    if code == 35:
        cid = struct.unpack_from("<H", buf, off)[0]
        aoff = struct.unpack_from("<I", buf, off+2)[0]
        print("JPEG3 id=%-6d tagLen=%-7d alphaOff=%-7d  图像数据前16: %s" % (cid, ln, aoff, hexd(buf[off+6:off+6+16])))
        print("                      尾部前16: %s" % hexd(buf[off+6+aoff:off+6+aoff+16]))
    elif code == 36 and buf[off+2] == 3:
        cid = struct.unpack_from("<H", buf, off)[0]
        w = struct.unpack_from("<H", buf, off+3)[0]; h = struct.unpack_from("<H", buf, off+5)[0]
        ncol = buf[off+7]
        print("LOSS2fmt3 id=%-6d %dx%d tagLen=%-7d 色表size字节=%d" % (cid, w, h, ln, ncol+1))
        print("    off+7 起: %s" % hexd(buf[off+7:off+7+24]))
        for guess in (7+1+(ncol+1)*4, 7+1+(ncol+1)*4+ (4-((ncol+1)*4)%4)%4, 7+(ncol+1)*4):
            print("      猜测偏移 %-4d: %s" % (guess, hexd(buf[off+guess:off+guess+8])))
    elif code == 6:
        cid = struct.unpack_from("<H", buf, off)[0]
        print("DefineBits id=%-6d tagLen=%-7d  数据前24: %s" % (cid, ln, hexd(buf[off+2:off+2+24])))
