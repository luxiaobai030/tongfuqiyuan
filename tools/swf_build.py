# -*- coding: utf-8 -*-
"""SWF 改造工具：
  hide   —— 把根时间轴上的某些角色换成空壳（得到“没有该角色”的底图，用来渲染背景）
  viewer —— 造一个只放某一个 MovieClip 的临时 SWF（用来单独渲染这个角色自己的逐帧动画）
"""
import struct, sys
sys.stdout.reconfigure(encoding="utf-8")

SRC = r"F:\路小白。。\一些尝试\游戏\同福奇缘_移植\原版\同福奇缘.swf"

# 根时间轴专用标签（ShowFrame / Place / Remove / DoAction / 声音 / 帧标签…），造 viewer 时要去掉
DROPS = {1, 4, 5, 9, 12, 15, 18, 19, 26, 28, 43, 45, 59}
# 角色定义类标签
DEF_CODES = {2, 6, 7, 10, 11, 13, 14, 20, 21, 22, 32, 33, 34, 35, 36, 37, 39, 46, 48, 60, 73, 75, 78, 83, 84, 87, 88, 90, 91}

def load(path):
    raw = open(path, "rb").read()
    assert raw[:3] in (b"FWS", b"CWS"), raw[:3]
    ver = raw[3]
    body = raw[8:]
    rect_end = (5 + (body[0] >> 3) * 4 + 7) // 8
    rect = body[:rect_end]
    fps, nframe = struct.unpack_from("<HH", body, rect_end)
    tags = []                      # (code, 负载偏移, 长度, 标签头偏移)
    q = rect_end + 4
    while q + 2 <= len(body):
        hstart = q
        rh = struct.unpack_from("<H", body, q)[0]; q += 2
        code = rh >> 6; ln = rh & 0x3F
        if ln == 0x3F:
            ln = struct.unpack_from("<I", body, q)[0]; q += 4
        if code == 0:
            tags.append((0, q, 0, hstart))
            break
        tags.append((code, q, ln, hstart))
        q += ln
    return {"ver": ver, "body": body, "rect": rect, "fps": fps, "nframes": nframe, "tags": tags}

def tag_bytes(code, payload):
    if len(payload) < 0x3F:
        return struct.pack("<H", (code << 6) | len(payload)) + payload
    return struct.pack("<H", (code << 6) | 0x3F) + struct.pack("<I", len(payload)) + payload

def make_empty_sprite(sid):
    return tag_bytes(39, struct.pack("<HH", sid, 1) + tag_bytes(1, b""))

def place2(charid, depth, matrix_bytes):
    return tag_bytes(26, bytes([0x06]) + struct.pack("<HH", depth, charid) + matrix_bytes)

def write(path, src, tags_blob, nframes):
    body = bytes(src["rect"]) + struct.pack("<HH", src["fps"], nframes) + tags_blob
    data = b"FWS" + bytes([src["ver"]]) + struct.pack("<I", len(body) + 8) + body
    open(path, "wb").write(data)
    return len(data)

def defs_blob(src, drop_codes=DROPS):
    out = bytearray()
    for (code, off, ln, hstart) in src["tags"]:
        if code in drop_codes or code == 0:
            continue
        out += src["body"][hstart:off + ln]
    return bytes(out)

def max_id(src):
    m = 0
    for (code, off, ln, hstart) in src["tags"]:
        if code in DEF_CODES:
            m = max(m, struct.unpack_from("<H", src["body"], off)[0])
    return m

if __name__ == "__main__":
    cmd = sys.argv[1]
    src = load(SRC)
    if cmd == "hide":
        ids = [int(x) for x in sys.argv[3:]]
        newid = max_id(src) + 1
        body = bytearray(src["body"])
        for (code, off, ln, hstart) in src["tags"]:
            if code in (4, 26, 70):
                flags = body[off]
                if code == 4:
                    if struct.unpack_from("<H", body, off)[0] in ids:
                        struct.pack_into("<H", body, off, newid)
                elif flags & 0x02 and struct.unpack_from("<H", body, off + 3)[0] in ids:
                    struct.pack_into("<H", body, off + 3, newid)
        out = bytearray()
        for (code, off, ln, hstart) in src["tags"]:
            if code == 0:
                break
            out += body[hstart:off + ln]
        n = write(sys.argv[2], src, make_empty_sprite(newid) + bytes(out), src["nframes"])
        print("已生成", sys.argv[2], n, "字节；隐藏", ids, "→ 空角色", newid)
    elif cmd == "viewer":
        sys.path.insert(0, r"F:\路小白。。\一些尝试\游戏\同福奇缘_移植\tools")
        ns = {"__name__": "_probe"}
        exec(open(r"F:\路小白。。\一些尝试\游戏\同福奇缘_移植\tools\probe_clip.py", encoding="utf-8").read().split("if __name__")[0], ns)
        parse_place = ns["parse_place"]; pb = ns["buf"]; ptags = ns["tags"]
        cid = int(sys.argv[3])
        n = 0
        for (code, off, ln, hstart) in src["tags"]:
            if code == 39 and struct.unpack_from("<H", src["body"], off)[0] == cid:
                n = struct.unpack_from("<H", src["body"], off + 2)[0]
        mat = None
        for (code, off, ln) in ptags:
            if code in (4, 26, 70):
                try: r = parse_place(pb, off, code)
                except Exception: continue
                if r.get("charid") == cid and r.get("matrix"):
                    mstart = off + (5 if code == 26 else 3)
                    mat = bytes(pb[mstart:r["matrix"]["end"]])
                    break
        assert mat is not None, "找不到放置矩阵"
        total = int(sys.argv[4]) if len(sys.argv) > 4 else n
        tl = place2(cid, 1, mat) + tag_bytes(1, b"") * total
        n = write(sys.argv[2], src, defs_blob(src) + tl, total)
        print("已生成 viewer", sys.argv[2], n, "字节，角色", cid, "自身帧数", n, "总帧", total, "矩阵", mat.hex())