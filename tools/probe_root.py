# -*- coding: utf-8 -*-
import struct, sys
sys.stdout.reconfigure(encoding="utf-8")
src = open(r"F:\路小白。。\一些尝试\游戏\同福奇缘_移植\tools\probe_clip.py", encoding="utf-8").read()
exec(src.split("target = sys.argv")[0])

rp = (5 + (buf[0] >> 3) * 4 + 7) // 8 + 4
q = rp
n = 0
others = {}
cnt = {}
while q < len(buf) - 2:
    rh = struct.unpack_from("<H", buf, q)[0]; q += 2
    c = rh >> 6; l = rh & 0x3F
    if l == 0x3F:
        l = struct.unpack_from("<I", buf, q)[0]; q += 4
    if c == 0: break
    cnt[c] = cnt.get(c, 0) + 1
    if c in (4, 26, 70):
        r = None
        try:
            r = parse_place(buf, q, c)
        except Exception as ex:
            r = ("ERR", str(ex))
        others.setdefault(c, []).append((q, l, r))
    q += l
print("根标签统计:", sorted(cnt.items(), key=lambda x: -x[1])[:20])
for c in others:
    print("tag %d 数量 %d，前 20 条：" % (c, len(others[c])))
    for (qq, ll, r) in others[c][:20]:
        print("   off=%d len=%d -> %s" % (qq, ll, r))