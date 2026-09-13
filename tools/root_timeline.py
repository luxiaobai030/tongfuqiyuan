# -*- coding: utf-8 -*-
"""导出根时间轴的显示列表（逐帧：深度 -> 角色 id / 名字 / 位置），输出 JSON 供移植版使用"""
import struct, sys, json, io
sys.path.insert(0, r"F:\路小白。。\一些尝试\游戏\同福奇缘_移植\tools")
sys.stdout.reconfigure(encoding="utf-8")
exec(open(r"F:\路小白。。\一些尝试\游戏\同福奇缘_移植\tools\probe_clip.py", encoding="utf-8").read().split('if __name__')[0])

# sprite 的帧数
sprite_frames = {}
for (c, o, l) in tags:
    if c == 39:
        sid = struct.unpack_from("<H", buf, o)[0]
        sprite_frames[sid] = struct.unpack_from("<H", buf, o + 2)[0]

q = ROOT_TAGS
cur = {}
frame = 0
out = {}
depth_hist = {}
names = {}
for (c, qq, l) in tag_list(ROOT_TAGS, len(buf)):
    if c == 1:
        frame += 1
        if cur:
            out[frame] = {str(d): [v[0], round(v[1] / 20.0, 2), round(v[2] / 20.0, 2), round(v[3], 4), round(v[4], 4)] for d, v in cur.items()}
    elif c in (4, 26, 70):
        try: r = parse_place(buf, qq, c)
        except Exception: continue
        d = r["depth"]
        m = r.get("matrix") or {"tx": 0, "ty": 0, "sx": 1.0, "sy": 1.0}
        if r["charid"] != -1:
            cur[d] = [r["charid"], m["tx"], m["ty"], m["sx"], m["sy"]]
            if r["name"]:
                names[r["name"]] = r["charid"]
        elif d in cur:
            cur[d] = [cur[d][0], m["tx"], m["ty"], m["sx"], m["sy"]]
    elif c == 5:
        cur.pop(struct.unpack_from("<H", buf, qq)[0], None)
    elif c == 28:
        cur.pop(struct.unpack_from("<H", buf, qq)[0], None)

# 统计：哪些 sprite（有动画的）出现在根上
use = {}
for f, dl in out.items():
    for d, v in dl.items():
        cid = v[0]
        if cid in sprite_frames:
            u = use.setdefault(cid, {"frames": 0, "first": f, "last": f, "depths": set(), "nframes": sprite_frames[cid]})
            u["frames"] += 1
            u["last"] = max(u["last"], f)
            u["depths"].add(int(d))
print("名字:", names)
print("根上出现过的 sprite：")
for cid, u in sorted(use.items(), key=lambda x: -x[1]["frames"]):
    print("   char %5d  出现 %5d 帧  %d..%d  深度=%s  自身帧数=%d" % (cid, u["frames"], u["first"], u["last"], sorted(u["depths"]), u["nframes"]))

json.dump(out, io.open(r"F:\路小白。。\一些尝试\游戏\同福奇缘_移植\decompiled\_root_dl.json", "w"))
print("根显示列表已写出：", len(out), "帧")
