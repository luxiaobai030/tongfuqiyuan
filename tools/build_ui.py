# -*- coding: utf-8 -*-
"""从 swf2xml 的 XML 里提取动态文本框样式 / 字体 / 音效，生成 Godot 侧数据"""
import os, io, sys, json, shutil, re
import xml.etree.ElementTree as ET
sys.stdout.reconfigure(encoding="utf-8")

B   = r"F:\路小白。。\一些尝试\游戏\同福奇缘_移植"
XML = os.path.join(os.environ.get("TEMP", "."), "tfqy.xml")
GAMEDATA = os.path.join(B, "game", "data")
GAMEFONT = os.path.join(B, "game", "assets", "fonts")
os.makedirs(GAMEDATA, exist_ok=True)
os.makedirs(GAMEFONT, exist_ok=True)

def tw(v):
    return float(v) / 20.0

et_styles = {}
fonts     = {}
sounds    = set()
exports   = {}
frame_sounds = {}

stack = []
fi = 0
in_main = False
ctx = ET.iterparse(XML, events=("start", "end"))
for ev, el in ctx:
    if ev == "start":
        stack.append(el)
        continue
    path = [e.tag for e in stack]
    is_item = el.tag == "item"
    typ = el.get("type") if is_item else None
    # 主时间轴 = <swf><tags>
    main_level = len(stack) == 3 and stack[1].tag == "tags" and stack[0].tag == "swf"
    if is_item and typ == "DefineEditTextTag":
        b = el.find("bounds")
        sty = {
            "var":   el.get("variableName") or "",
            "align": int(el.get("align", "0")),
            "size":  round(tw(el.get("fontHeight", "0")), 2),
            "font":  int(el.get("fontId", "-1")) if el.get("hasFont") == "true" else -1,
            "ml":    el.get("multiline") == "true",
            "ww":    el.get("wordWrap") == "true",
            "ro":    el.get("readOnly") == "true",
            "lead":  round(tw(el.get("leading", "0")), 2),
            "lm":    round(tw(el.get("leftMargin", "0")), 2),
        }
        tc = el.find("textColor")
        sty["color"] = ("#%02x%02x%02x" % (int(tc.get("red")), int(tc.get("green")), int(tc.get("blue")))) if tc is not None else "#000000"
        sty["alpha"] = int(tc.get("alpha", "255")) if tc is not None else 255
        if b is not None:
            sty["bw"] = round(tw(int(b.get("Xmax")) - int(b.get("Xmin"))), 2)
            sty["bh"] = round(tw(int(b.get("Ymax")) - int(b.get("Ymin"))), 2)
        et_styles[int(el.get("characterID"))] = sty
    elif is_item and typ in ("DefineFont2Tag", "DefineFont3Tag"):
        fonts[int(el.get("fontID"))] = el.get("fontName")
    elif is_item and typ == "DefineSoundTag":
        sounds.add(int(el.get("soundId")))
    elif is_item and typ == "ExportAssetsTag":
        tg = el.find("tags"); nm = el.find("names")
        if tg is not None and nm is not None and len(tg) and len(nm):
            try: exports[int(tg[0].text)] = nm[0].text
            except Exception: pass
    elif is_item and typ == "ShowFrameTag" and main_level:
        fi += 1
    elif is_item and typ == "StartSoundTag" and main_level:
        frame_sounds.setdefault(fi + 1, []).append(int(el.get("soundId")))
    stack.pop()
    if is_item:
        el.clear()

print("edittext:", len(et_styles), "fonts:", fonts)
print("sounds:", sorted(sounds))
print("exports:", exports)
print("main-timeline sound frames:", sorted(frame_sounds.items())[:25])

json.dump(et_styles, io.open(os.path.join(GAMEDATA, "textfields.json"), "w", encoding="utf-8"), ensure_ascii=False, sort_keys=True)

snd = {}
for sid in sorted(sounds):
    name = exports.get(sid, "")
    fn = "%d_%s.mp3" % (sid, name) if name else "%d.mp3" % sid
    import glob
    cand = glob.glob(os.path.join(B, "decompiled", "sounds", "%d_*.mp3" % sid)) + glob.glob(os.path.join(B, "decompiled", "sounds", "%d.mp3" % sid))
    if cand:
        snd[str(sid)] = {"file": os.path.basename(cand[0]), "name": name}
    else:
        print("missing sound file for", sid)
json.dump({"sounds": snd, "frames": {str(k): v for k, v in sorted(frame_sounds.items())}},
          io.open(os.path.join(GAMEDATA, "sounds.json"), "w", encoding="utf-8"), ensure_ascii=False, sort_keys=True)

want = {}
for cid, sty in et_styles.items():
    fid = sty["font"]
    if fid > 0:
        want[fid] = fonts.get(fid, "?")
print("font ids used by edittext:", want)
for cid, sty in sorted(et_styles.items()):
    print("   id=%d var=%-16s font=%s size=%s align=%d color=%s ml=%s ww=%s box=%sx%s" % (cid, sty["var"], sty["font"], sty["size"], sty["align"], sty["color"], sty["ml"], sty["ww"], sty.get("bw"), sty.get("bh")))
name_from_file = {}
for f in os.listdir(os.path.join(B, "decompiled", "fonts")):
    m = re.match(r"(\d+)_(.+)\.ttf$", f)
    if m: name_from_file[int(m.group(1))] = m.group(2)
for fid in want:
    src = None
    for f in os.listdir(os.path.join(B, "decompiled", "fonts")):
        if f.startswith("%d_" % fid) and f.endswith(".ttf"):
            src = os.path.join(B, "decompiled", "fonts", f); break
    if src:
        shutil.copyfile(src, os.path.join(GAMEFONT, "f%d.ttf" % fid))
        print("font %d (%s) -> f%d.ttf" % (fid, name_from_file.get(fid, "?"), fid))
    else:
        print("font %d NOT FOUND" % fid)
json.dump(name_from_file, io.open(os.path.join(GAMEDATA, "fontnames.json"), "w", encoding="utf-8"), ensure_ascii=False, sort_keys=True)

