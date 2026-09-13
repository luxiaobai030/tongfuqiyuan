# -*- coding: utf-8 -*-
"""把根时间轴上所有“会自己播动画的角色（MovieClip）”单独渲染出来，
并导出每个角色的时间轴事件（出现/移动/消失），供移植版当独立动画层播放。

做法：用原 SWF 的全部素材，造一个只在第 1 帧放这一个角色的临时 SWF，
按它在正片里的常用位置/缩放摆放，然后逐帧导出（角色自己会一格一格往前走）。

两种存放方式：
  默认   —— 把该角色所有帧拼成一张贴图集（一次读进显存，适合小角色）
  --per  —— 每帧存一张图（适合 800x600 的整屏角色：贴图集会有几百 MB，显卡吃不消）
"""
import struct, sys, os, io, json, subprocess, shutil
sys.stdout.reconfigure(encoding="utf-8")
import numpy as np
from PIL import Image

B = r"F:\路小白。。\一些尝试\游戏\同福奇缘_移植"
DEC = os.path.join(B, "decompiled")
OUT = os.path.join(B, "game", "assets", "clips")
DATA = os.path.join(B, "game", "data")
TMP = os.path.join(DEC, "_clip_frames")
JAVA = r"F:\APP\jre\jdk-21.0.12.1+1-jre\bin\java.exe"
FFDEC = r"F:\APP\ffdec\ffdec.jar"
sys.path.insert(0, os.path.join(B, "tools"))
import swf_build as SB

for d in (OUT, DATA, TMP):
    os.makedirs(d, exist_ok=True)

ns = {"__name__": "_probe"}
exec(open(os.path.join(B, "tools", "probe_clip.py"), encoding="utf-8").read().split("if __name__")[0], ns)
buf = ns["buf"]; tags = ns["tags"]; tag_list = ns["tag_list"]
parse_place = ns["parse_place"]; ROOT = ns["ROOT_TAGS"]

sprite_frames = {}
for c, o, l in tags:
    if c == 39:
        sprite_frames[struct.unpack_from("<H", buf, o)[0]] = struct.unpack_from("<H", buf, o + 2)[0]

events = {}
placements = {}          # charid -> {(tx,ty,sx,sy): 帧数}
frame = 0
for (c, q, l) in tag_list(ROOT, len(buf)):
    if c == 1:
        frame += 1
    elif c in (4, 26, 70):
        try: r = parse_place(buf, q, c)
        except Exception: continue
        d = r["depth"]
        m = r.get("matrix") or {"tx": 0, "ty": 0, "sx": 1.0, "sy": 1.0}
        if r["charid"] == -1:
            events.setdefault(frame, []).append([d, -1, round(m["tx"] / 20.0, 2), round(m["ty"] / 20.0, 2), round(m["sx"], 4), round(m["sy"], 4)])
        else:
            cid = r["charid"]
            t = (round(m["tx"] / 20.0, 2), round(m["ty"] / 20.0, 2), round(m["sx"], 4), round(m["sy"], 4))
            events.setdefault(frame, []).append([d, cid, t[0], t[1], t[2], t[3]])
            if cid in sprite_frames and sprite_frames[cid] > 1 and r.get("matrix"):
                mstart = q + (5 if c == 26 else 3)
                mbytes = bytes(buf[mstart:r["matrix"]["end"]])
                place = placements.setdefault(cid, {})
                place[mbytes] = place.get(mbytes, 0) + 1
    elif c == 5:
        events.setdefault(frame, []).append([struct.unpack_from("<H", buf, q)[0], -2])
    elif c == 28:
        events.setdefault(frame, []).append([struct.unpack_from("<H", buf, q)[0], -2])

# 每个角色的“常用摆放” = 出现帧数最多的那个矩阵
refs = {}
for cid, pl in placements.items():
    refs[cid] = max(pl.items(), key=lambda kv: kv[1])[0]      # 出现次数最多的矩阵字节
# 参考矩阵的平移/缩放（供移植版换算位置）
parse_matrix = ns["parse_matrix"]
ref_info = {}
for cid, mb in refs.items():
    m = parse_matrix(mb, 0)
    ref_info[cid] = {"tx": round(m["tx"] / 20.0, 2), "ty": round(m["ty"] / 20.0, 2),
                     "sx": round(m["sx"], 4), "sy": round(m["sy"], 4)}

src = SB.load(SB.SRC)
meta = {}
args = sys.argv[1:]
per = set()
if "--per" in args:
    i = args.index("--per")
    per = set(int(x) for x in args[i + 1:])
    args = args[:i]
only = [int(x) for x in args] if args else sorted(refs)
# 烧进背景层的整屏角色（见 tools/build_assets.py）：1010（大堂）不单独导出，
# 它的像素已经在 decompiled/frames 里了。
only = [c for c in only if c not in (1010,)]
for cid in only:
    n = sprite_frames[cid]
    mat = refs[cid]
    d = os.path.join(TMP, str(cid))
    if os.path.exists(d):
        shutil.rmtree(d)
    swf = os.path.join(TMP, "_v%d.swf" % cid)
    SB.write(swf, src, SB.defs_blob(src) + SB.place2(cid, 1, mat) + SB.tag_bytes(1, b"") * n, n)
    subprocess.run([JAVA, "-Xmx2g", "-jar", FFDEC, "-export", "frame", d, swf],
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    files = sorted(os.listdir(d), key=lambda f: int(os.path.splitext(f)[0])) if os.path.exists(d) else []
    if len(files) != n:
        print("  !! 角色 %d 导出帧数 %d != %d" % (cid, len(files), n))
    ims = []
    x0 = y0 = 10 ** 6; x1 = y1 = -1
    for f in files:
        a = np.asarray(Image.open(os.path.join(d, f)).convert("RGBA"))
        ys, xs = np.nonzero(a[:, :, 3] > 0)
        if len(xs):
            x0 = min(x0, int(xs.min())); y0 = min(y0, int(ys.min()))
            x1 = max(x1, int(xs.max())); y1 = max(y1, int(ys.max()))
        ims.append(a)
    if not ims or x1 < 0:
        print("  !! 角色 %d 全空，跳过" % cid); continue
    w = x1 - x0 + 1; h = y1 - y0 + 1
    cols = int(np.ceil(np.sqrt(len(ims))))
    rows = int(np.ceil(len(ims) / cols))
    ref = ref_info[cid]
    if cid in per:
        # 逐帧存放：只按需读当前那一帧，显存占用恒定
        pd = os.path.join(OUT, str(cid))
        if os.path.exists(pd):
            shutil.rmtree(pd)
        os.makedirs(pd)
        for i, a in enumerate(ims):
            Image.fromarray(a[y0:y1 + 1, x0:x1 + 1], "RGBA").save(
                os.path.join(pd, "%d.webp" % (i + 1)), "WEBP", lossless=True, method=0)
        size = sum(os.path.getsize(os.path.join(pd, f)) for f in os.listdir(pd))
        meta[str(cid)] = {"n": len(ims), "w": w, "h": h, "cols": 1, "rows": len(ims),
                          "x": x0, "y": y0, "ref": ref, "per": 1, "file": "%d/" % cid}
    else:
        atlas = Image.new("RGBA", (cols * w, rows * h), (0, 0, 0, 0))
        for i, a in enumerate(ims):
            atlas.paste(Image.fromarray(a[y0:y1 + 1, x0:x1 + 1], "RGBA"), ((i % cols) * w, (i // cols) * h))
        path = os.path.join(OUT, "%d.webp" % cid)
        atlas.save(path, "WEBP", lossless=True, method=0)
        size = os.path.getsize(path)
        meta[str(cid)] = {"n": len(ims), "w": w, "h": h, "cols": cols, "rows": rows,
                          "x": x0, "y": y0, "ref": ref, "file": "%d.webp" % cid}
    os.remove(swf)
    shutil.rmtree(d)
    print("  角色 %5d 帧数 %3d 参考摆放 %s 单帧 %dx%d → %s (%.0f KB)" % (
        cid, len(ims), ref, w, h, str(meta[str(cid)]["file"]), size / 1024), flush=True)

p = os.path.join(DATA, "clips.json")
cur = {}
if os.path.exists(p):
    try: cur = json.load(io.open(p, encoding="utf-8"))
    except Exception: cur = {}
# 只更新贴图信息；names / jump / stop 由 build_clip_info.py 补，events 由 build_clip_events.py 重算
old = cur.get("clips", {})
for cid, e in meta.items():
    old.setdefault(cid, {}).update(e)
cur["clips"] = old
json.dump(cur, io.open(p, "w", encoding="utf-8"), separators=(",", ":"), ensure_ascii=False)
print("写出", p, "角色数", len(old), "大小 %.0f KB" % (os.path.getsize(p) / 1024))
