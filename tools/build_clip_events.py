# -*- coding: utf-8 -*-
"""重算 clips.json 里的“显示列表事件”（出现/移动/消失/淡入淡出），不重导贴图。
   事件表是移植版独立动画层的数据来源，必须和原版时间轴完全一致。

!! 独立动画层目前是**关闭**的（见下面的 ENABLED）：人物动画按用户要求改回
   「烧在原版整幅画面里」（tools/build_assets.py 取 decompiled/frames），
   这样角色不会盖住叠在他们上层的按钮文字（战斗的「先机/后发」等）。
   想重新启用：把 ENABLED 改成 True，并把 build_assets.py 的画面源换回 _ro_frames。

   事件格式（键 = 主帧号 - 1）：
     [深度, 角色id, 位置x, 位置y, 横向缩放, 纵向缩放, 不透明度]   出现或替换
     [深度, -1, x, y, sx, sy, a]                                  只改动列出的项（null = 不变）
     [深度, -2]                                                  移除
"""
import struct, sys, os, io, json, struct as _s

ENABLED = False

HERE = os.path.dirname(os.path.abspath(__file__))
B = os.path.dirname(HERE)
sys.path.insert(0, HERE)

ns = {"__name__": "_probe"}
exec(open(os.path.join(HERE, "probe_clip.py"), encoding="utf-8").read().split("if __name__")[0], ns)
buf = ns["buf"]; tags = ns["tags"]; tag_list = ns["tag_list"]; ROOT = ns["ROOT_TAGS"]
parse_matrix = ns["parse_matrix"]; cx_alpha = ns["cx_alpha"]

sprite_frames = {}
for c, o, l in tags:
    if c == 39:
        sprite_frames[_s.unpack_from("<H", buf, o)[0]] = _s.unpack_from("<H", buf, o + 2)[0]

data_path = os.path.join(B, "game", "data", "clips.json")
meta = json.load(io.open(data_path, encoding="utf-8"))
if not ENABLED:
    meta["events"] = {}
    json.dump(meta, io.open(data_path, "w", encoding="utf-8"), separators=(",", ":"), ensure_ascii=False)
    print("独立动画层已关闭：events 清空（人物动画走原版整幅画面）")
    sys.exit(0)
clip_ids = set(int(k) for k in meta["clips"])

# 烧进背景层的整屏角色（见 tools/build_assets.py 的说明）：
# 1010 = 大堂，第 564～817 帧唯一在场的角色，原版整幅画面已经带上了它，
# 再单独画一层就是重复叠加（而且会丢掉黑→亮的淡入、画反边框的透明度）。
BURNED = {1010, 547}
clip_ids -= BURNED

def r2(v):
    return round(v, 2)

events = {}
frame = 0
seen = {}
for (c, q, l) in tag_list(ROOT, len(buf)):
    if c == 1:
        frame += 1
    elif c in (4, 26, 70):
        try:
            r = ns["parse_place"](buf, q, c)
        except Exception:
            continue
        d = r["depth"]
        alpha = round(cx_alpha(buf, r["cx_off"]), 3) if r.get("cx_off", -1) >= 0 else None
        m = r.get("matrix")
        if r["charid"] == -1:
            # 只改位置/透明度（没有矩阵就保持原位）
            tx = r2(m["tx"] / 20.0) if m else None
            ty = r2(m["ty"] / 20.0) if m else None
            sx = round(m["sx"], 4) if m else None
            sy = round(m["sy"], 4) if m else None
            if tx is not None or alpha is not None:
                events.setdefault(frame, []).append([d, -1, tx, ty, sx, sy, alpha])
        else:
            cid = r["charid"]
            if cid not in clip_ids:
                continue
            events.setdefault(frame, []).append([d, cid, r2(m["tx"] / 20.0), r2(m["ty"] / 20.0),
                                                 round(m["sx"], 4), round(m["sy"], 4),
                                                 1.0 if alpha is None else alpha])
            seen[cid] = seen.get(cid, 0) + 1
    elif c == 5:
        events.setdefault(frame, []).append([_s.unpack_from("<H", buf, q)[0], -2])
    elif c == 28:
        events.setdefault(frame, []).append([_s.unpack_from("<H", buf, q)[0], -2])

meta["events"] = events
json.dump(meta, io.open(data_path, "w", encoding="utf-8"), separators=(",", ":"), ensure_ascii=False)
print("角色放置次数:", {k: seen[k] for k in sorted(seen)})
n_alpha = sum(1 for evs in events.values() for e in evs if len(e) > 3 and e[-1] is not None)
print("事件帧数:", len(events), "  带透明度的事件条目:", n_alpha, "  文件 %.0f KB" % (os.path.getsize(data_path) / 1024))
