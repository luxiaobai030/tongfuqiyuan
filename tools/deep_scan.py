# -*- coding: utf-8 -*-
"""递归收全 AS2 逻辑块：顶层 + DefineSprite 内 + DefineButton2 内"""
import struct, os, sys, glob

buf = open(sys.argv[1],"rb").read(); OUT = sys.argv[2]
ADIR = os.path.join(OUT,"actions_deep"); os.makedirs(ADIR, exist_ok=True)
for f in glob.glob(os.path.join(ADIR,"*.bin")): os.remove(f)

p = 0; nb = buf[0]>>3; p += (5+nb*4+7)//8 + 4
found = []
btn_ok = btn_no = 0

def walk(start, end, path, depth):
    global btn_ok, btn_no
    q = start
    while q < end - 2:
        rh = struct.unpack_from("<H", buf, q)[0]; q += 2
        code = rh >> 6; ln = rh & 0x3F
        if ln == 0x3F: ln = struct.unpack_from("<I", buf, q)[0]; q += 4
        if code == 0: break
        off = q; q += ln
        if q > end: break
        if code == 39 and depth < 5:
            sid = struct.unpack_from("<H", buf, off)[0]
            walk(off+4, off+ln, "%s/sp%d" % (path, sid), depth+1)
        elif code == 34 and depth < 5:
            bid = struct.unpack_from("<H", buf, off)[0]
            ao  = struct.unpack_from("<H", buf, off+3)[0]
            if ao and off+5+ao < off+ln:
                r = off+5+ao; got = 0
                while r + 4 <= off + ln:
                    size = struct.unpack_from("<H", buf, r)[0]
                    if size == 0 or r + 2 + size > off + ln + 2: break
                    act = buf[r+4:r+2+size]
                    if act: found.append(("%s/bt%d"%(path,bid), 12, act)); got += 1
                    r += 2 + size
                if got: btn_ok += 1
                else: btn_no += 1
        elif code in (12, 59):
            found.append((path, code, buf[off:off+ln]))

walk(p, len(buf), "", 0)

for i,(path,code,data) in enumerate(found):
    tag = path.replace("/","_") or "top"
    open(os.path.join(ADIR,"a%05d_c%d_%s.bin"%(i,code,tag)),"wb").write(data)

print("逻辑块总数:", len(found))
print("有动作的按钮:", btn_ok, " 解析失败的按钮:", btn_no)
print("逻辑总字节:", sum(len(d) for _,_,d in found))
sz = sorted((len(d) for _,_,d in found), reverse=True)[:12]
print("最大 12 块:", sz)
