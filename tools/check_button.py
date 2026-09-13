# -*- coding: utf-8 -*-
"""校验 DefineButton2 的 ActionOffset 基准"""
import struct, sys

buf = open(sys.argv[1],"rb").read()
p = 0; nb = buf[0]>>3; p += (5+nb*4+7)//8 + 4
btns = []
while p < len(buf)-2:
    rh = struct.unpack_from("<H",buf,p)[0]; code = rh>>6; ln = rh&0x3F; p += 2
    if ln == 0x3F: ln = struct.unpack_from("<I",buf,p)[0]; p += 4
    if code == 0: break
    if code == 34: btns.append((p, ln))
    p += ln
print("DefineButton2 个数:", len(btns))

def chain(buf, off, ln, start, label):
    """从 start 起按 CondActionSize 串接，看是否正好走到 tag 末尾"""
    q = start; n = 0; total = 0
    while q + 4 <= off + ln:
        size = struct.unpack_from("<H", buf, q)[0]
        if size == 0 or q + 2 + size > off + ln + 4: return None
        n += 1; total += size; q += 2 + size
        if n > 200: return None
    ok = abs(q - (off + ln)) <= 2
    return (n, total, q - (off+ln)) if n else None

iok_a = iok_b = 0
for off, ln in btns:
    if ln < 8: continue
    ao = struct.unpack_from("<H", buf, off+3)[0]
    for base, tag in ((off, "A: off+ao"), (off+5, "B: off+5+ao")):
        if ao == 0: continue
        r = chain(buf, off, ln, base+ao, tag)
        if r:
            if tag.startswith("A"): iok_a += 1
            else: iok_b += 1
print("解释A (off+ao) 自洽:", iok_a)
print("解释B (off+5+ao) 自洽:", iok_b)

print("\n== 前 3 个按钮的原始头 24 字节 ==")
for off, ln in btns[:3]:
    ao = struct.unpack_from("<H", buf, off+3)[0]
    print("len=%d btnid=%d flags=0x%02X action_offset=%d" % (ln, struct.unpack_from("<H",buf,off)[0], buf[off+2], ao))
    print("   ", " ".join("%02X"%b for b in buf[off:off+24]))
