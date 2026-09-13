# -*- coding: utf-8 -*-
"""补齐 clips.json 里“角色自己那条时间轴”的信息：
  - names : 原版根舞台上给角色起的名字（剧本里用这些名字点名播动画，如 dr_boos.gotoAndPlay(24)）
  - 每个角色的 jumps（某帧播完跳回第几帧）/ stops（某帧停住）——原版角色动画“播一次就停”靠的就是它
"""
import os, io, re, json, struct, sys

HERE = os.path.dirname(os.path.abspath(__file__))
B = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.stdout.reconfigure(encoding="utf-8")

ns = {"__name__": "_probe"}
exec(open(os.path.join(HERE, "probe_clip.py"), encoding="utf-8").read().split("if __name__")[0], ns)
buf = ns["buf"]

# 根舞台上带名字的放置点 → 名字 → 角色 id
names = {}
frame = 0
for (c, q, l) in ns["tag_list"](ns["ROOT_TAGS"], len(buf)):
    if c == 1:
        frame += 1
    elif c in (4, 26, 70):
        try:
            r = ns["parse_place"](buf, q, c)
        except Exception:
            continue
        if r.get("name") and r["charid"] > 0:
            names[r["name"]] = r["charid"]

data_path = os.path.join(B, "game", "data", "clips.json")
meta = json.load(io.open(data_path, encoding="utf-8"))
SD = os.path.join(B, "decompiled", "scripts")

for cid in sorted(int(k) for k in meta["clips"]):
    d = os.path.join(SD, "DefineSprite_%d" % cid)
    jumps, stops = {}, []
    if os.path.isdir(d):
        for f in os.listdir(d):
            m = re.match(r"frame_(\d+)$", f)
            if not m:
                continue
            k = int(m.group(1))
            src = io.open(os.path.join(d, f, "DoAction.as"), encoding="utf-8", errors="replace").read()
            for g in re.finditer(r"gotoAndPlay\s*\(\s*(\d+)\s*\)", src):
                jumps[str(k)] = int(g.group(1))
            if re.search(r"(^|[^\w.])stop\s*\(\s*\)", src):
                stops.append(k)
    e = meta["clips"][str(cid)]
    if jumps:
        e["jump"] = jumps
    if stops:
        e["stop"] = sorted(stops)

meta["names"] = names
json.dump(meta, io.open(data_path, "w", encoding="utf-8"), separators=(",", ":"), ensure_ascii=False)
print("名字表:", names)
for cid in sorted(int(k) for k in meta["clips"]):
    e = meta["clips"][str(cid)]
    if "jump" in e or "stop" in e:
        print("  角色 %5d n=%-4d jump=%s stop=%s" % (cid, e["n"], e.get("jump"), e.get("stop")))
print("写出", data_path, os.path.getsize(data_path), "字节")
