# -*- coding: utf-8 -*-
import struct, sys
sys.stdout.reconfigure(encoding="utf-8")
exec(open(r"F:\路小白。。\一些尝试\游戏\同福奇缘_移植\tools\probe_clip.py", encoding="utf-8").read().split("target = sys.argv")[0])
names = {}
def scan_range(s, e, owner):
    q = s
    while q < e - 2:
        rh = struct.unpack_from("<H", buf, q)[0]; q += 2
        c = rh >> 6; l = rh & 0x3F
        if l == 0x3F:
            l = struct.unpack_from("<I", buf, q)[0]; q += 4
        if c == 0: break
        if c in (4, 26, 70):
            try:
                r = parse_place(buf, q, c)
            except Exception:
                r = None
            if r and len(r) == 4 and r[2]:
                names.setdefault(r[2], set()).add((owner, r[0], r[1]))
        q += l
# root
rp = (5 + (buf[0] >> 3) * 4 + 7) // 8 + 4
scan_range(rp, len(buf), "root")
for sid, (s, e) in defs.items():
    scan_range(s, e, sid)
print("名字总数:", len(names))
for k in sorted(names):
    if "boss" in k.lower() or "dr" in k.lower() or "boos" in k.lower():
        print("  ", k, sorted(names[k])[:6])