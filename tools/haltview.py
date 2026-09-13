# -*- coding: utf-8 -*-
"""haltview —— 按主时间轴任意一帧的显示列表，造一个小 SWF：
根时间轴停在那一帧的内容上，但每个“会动的角色”从它在原版里当时的播放头接着往下走。
用来得到“画面停住后角色继续动”的原版真值（逐帧 PNG）。

用法：
  python tools/haltview.py <主帧F> <额外帧数K> <输出目录> [--drop id,id,...]
输出：
  <输出目录>\1.png .. <总帧>.png；其中第 t_ref 帧 = 主帧 F 当时的样子，
  第 t_ref + k 帧 = 停帧后第 k 步（角色各自往前走 k 格）
"""
import struct, sys, os, subprocess

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import swf_build as SB

JAVA = r"F:\APP\jre\jdk-21.0.12.1+1-jre\bin\java.exe"
FFDEC = r"F:\APP\ffdec\ffdec.jar"

ns = {"__name__": "_probe"}
exec(open(os.path.join(HERE, "probe_clip.py"), encoding="utf-8").read().split("if __name__")[0], ns)
buf = ns["buf"]; ROOT = ns["ROOT_TAGS"]; tag_list = ns["tag_list"]


class BitsR:
    def __init__(self, b, bytepos):
        self.b = b; self.p = bytepos * 8
    def bits(self, n):
        v = 0
        for _ in range(n):
            v = (v << 1) | ((self.b[self.p >> 3] >> (7 - (self.p & 7))) & 1)
            self.p += 1
        return v
    def sbits(self, n):
        if n == 0: return 0
        v = self.bits(n)
        if v & (1 << (n - 1)): v -= (1 << n)
        return v
    def align(self):
        self.p = (self.p + 7) & ~7


class BitW:
    def __init__(self):
        self.acc = 0; self.n = 0; self.out = bytearray()
    def bits(self, v, n):
        for i in range(n - 1, -1, -1):
            self.acc = (self.acc << 1) | ((v >> i) & 1)
            self.n += 1
            if self.n == 8:
                self.out.append(self.acc & 0xFF); self.acc = 0; self.n = 0
    def sbits(self, v, n):
        if v < 0: v += (1 << n)
        self.bits(v, n)
    def align(self):
        if self.n:
            self.out.append((self.acc << (8 - self.n)) & 0xFF)
            self.acc = 0; self.n = 0
    def data(self):
        return bytes(self.out)


def nbits_signed(values):
    nb = 1
    for v in values:
        if v == 0:
            continue
        n = (v.bit_length() + 1) if v > 0 else ((-v - 1).bit_length() + 1)
        nb = max(nb, n)
    return nb


def parse_matrix_raw(b, off):
    br = BitsR(b, off)
    sx = sy = 65536; r0 = r1 = 0
    if br.bits(1):
        n = br.bits(5); sx = br.sbits(n); sy = br.sbits(n)
    if br.bits(1):
        n = br.bits(5); r0 = br.sbits(n); r1 = br.sbits(n)
    n = br.bits(5); tx = br.sbits(n); ty = br.sbits(n)
    br.align()
    return {"sx": sx, "sy": sy, "r0": r0, "r1": r1, "tx": tx, "ty": ty, "end": br.p // 8}


def encode_matrix(m):
    w = BitW()
    if m["sx"] != 65536 or m["sy"] != 65536:
        w.bits(1, 1)
        nb = nbits_signed([m["sx"], m["sy"]])
        w.bits(nb, 5); w.sbits(m["sx"], nb); w.sbits(m["sy"], nb)
    else:
        w.bits(0, 1)
    if m["r0"] or m["r1"]:
        w.bits(1, 1)
        nb = nbits_signed([m["r0"], m["r1"]])
        w.bits(nb, 5); w.sbits(m["r0"], nb); w.sbits(m["r1"], nb)
    else:
        w.bits(0, 1)
    nb = nbits_signed([m["tx"], m["ty"]])
    w.bits(nb, 5); w.sbits(m["tx"], nb); w.sbits(m["ty"], nb)
    w.align()
    return w.data()


def parse_cxform(b, off):
    br = BitsR(b, off)
    has_add = br.bits(1); has_mult = br.bits(1); nb = br.bits(4)
    mult = [br.sbits(nb) for _ in range(4)] if has_mult else None
    add = [br.sbits(nb) for _ in range(4)] if has_add else None
    br.align()
    return {"add": add, "mult": mult, "end": br.p // 8}


def encode_cxform(c):
    w = BitW()
    has_add = 1 if c["add"] is not None else 0
    has_mult = 1 if c["mult"] is not None else 0
    w.bits(has_add, 1); w.bits(has_mult, 1)
    vals = (c["mult"] or []) + (c["add"] or [])
    nb = nbits_signed(vals) if vals else 1
    w.bits(nb, 4)
    for v in (c["mult"] or []): w.sbits(v, nb)
    for v in (c["add"] or []): w.sbits(v, nb)
    w.align()
    return w.data()


def parse_place_full(b, q, code):
    r = {"charid": -1, "depth": 0, "move": False, "matrix": None, "cxform": None,
         "ratio": None, "name": None, "clipdepth": None}
    if code == 4:
        charid, depth = struct.unpack_from("<HH", b, q)
        r["charid"] = charid; r["depth"] = depth
        mx = parse_matrix_raw(b, q + 4)
        r["matrix"] = mx; r["end"] = mx["end"]
        return r
    f1 = b[q]; pp = q + 1
    r["move"] = bool(f1 & 1)
    r["depth"] = struct.unpack_from("<H", b, pp)[0]; pp += 2
    f2 = 0
    if code == 70:
        f2 = b[pp]; pp += 1
        if f2 & 0x02:
            while b[pp] != 0: pp += 1
            pp += 1
        if f2 & 0x04: pp += 4
        if f2 & 0x08: pp += 4
    if f1 & 0x02:
        r["charid"] = struct.unpack_from("<H", b, pp)[0]; pp += 2
    if f1 & 0x04:
        mx = parse_matrix_raw(b, pp)
        r["matrix"] = mx; pp = mx["end"]
    if f1 & 0x08:
        cx = parse_cxform(b, pp)
        r["cxform"] = cx; pp = cx["end"]
    if f1 & 0x10:
        r["ratio"] = struct.unpack_from("<H", b, pp)[0]; pp += 2
    if code == 70 and (f2 & 0x80):
        n = b[pp]; pp += 1 + n * 6
    if f1 & 0x20:
        s = pp
        while b[pp] != 0: pp += 1
        r["name"] = b[s:pp].decode("utf-8", "replace"); pp += 1
    if code == 70 and (f2 & 0x40): pp += 1
    if code == 70 and (f2 & 0x20): pp += 4
    if code == 70 and (f2 & 0x10): pp += 1
    if code == 70 and (f2 & 0x08): pp += 4
    if f1 & 0x40:
        r["clipdepth"] = struct.unpack_from("<H", b, pp)[0]; pp += 2
    r["end"] = pp
    return r


def place_tag(e):
    flags = 0x02 | 0x04
    if e["cxform"] is not None: flags |= 0x08
    if e["ratio"] is not None: flags |= 0x10
    if e["name"]: flags |= 0x20
    if e["clipdepth"] is not None: flags |= 0x40
    payload = bytes([flags]) + struct.pack("<HH", e["depth"], e["charid"]) + encode_matrix(e["matrix"])
    if e["cxform"] is not None: payload += encode_cxform(e["cxform"])
    if e["ratio"] is not None: payload += struct.pack("<H", e["ratio"])
    if e["name"]: payload += e["name"].encode("utf-8") + b"\x00"
    if e["clipdepth"] is not None: payload += struct.pack("<H", e["clipdepth"])
    return SB.tag_bytes(26, payload)


def sprite_frame_counts(src):
    out = {}
    for (c, o, l, h) in src["tags"]:
        if c == 39:
            out[struct.unpack_from("<H", src["body"], o)[0]] = struct.unpack_from("<H", src["body"], o + 2)[0]
    return out


def display_list_at(F):
    cur = {}
    frame = 0
    for (c, q, l) in tag_list(ROOT, len(buf)):
        if c == 1:
            frame += 1
            if frame >= F:
                break
            continue
        if c in (4, 26, 70):
            r = parse_place_full(buf, q, c)
            d = r["depth"]
            if r["charid"] != -1:
                cur[d] = {"charid": r["charid"], "depth": d, "matrix": r["matrix"],
                          "cxform": r["cxform"], "ratio": r["ratio"], "name": r["name"],
                          "clipdepth": r["clipdepth"], "place": frame + 1}
            elif d in cur:
                e = cur[d]
                if r["matrix"]: e["matrix"] = r["matrix"]
                if r["cxform"] is not None: e["cxform"] = r["cxform"]
                if r["ratio"] is not None: e["ratio"] = r["ratio"]
                if r["name"]: e["name"] = r["name"]
                if r["clipdepth"] is not None: e["clipdepth"] = r["clipdepth"]
        elif c == 5:
            cur.pop(struct.unpack_from("<H", buf, q)[0], None)
        elif c == 28:
            cur.pop(struct.unpack_from("<H", buf, q)[0], None)
    return cur


def main():
    F = int(sys.argv[1]); K = int(sys.argv[2]); out = sys.argv[3]
    drop = set()
    if "--drop" in sys.argv:
        drop = set(int(x) for x in sys.argv[sys.argv.index("--drop") + 1].split(",") if x)
    src = SB.load(SB.SRC)
    frames_of = sprite_frame_counts(src)
    cur = display_list_at(F)
    items = [cur[d] for d in sorted(cur)]

    clips = []
    for e in items:
        n = frames_of.get(e["charid"], 1)
        if n > 1 and e["charid"] not in drop:
            clips.append((e, n, (F - e["place"]) % n + 1))
    p_max = max([c[2] for c in clips], default=1)
    t_ref = p_max + 1
    total = t_ref + K
    print("主帧 %d：显示列表 %d 项，会动的角色 %d 个，最长播放头 %d，总帧 %d" % (F, len(items), len(clips), p_max, total))
    for e, n, p in clips:
        print("   char %5d 帧数 %3d 当时播放头 %3d（放置于主帧 %d）" % (e["charid"], n, p, e["place"]))

    plan = {}
    for e in items:
        if e["charid"] <= 0 or e["matrix"] is None:
            continue
        n = frames_of.get(e["charid"], 1)
        if n > 1 and e["charid"] not in drop:
            p = (F - e["place"]) % n + 1
            plan.setdefault(t_ref - p + 1, []).append(e)
        elif n <= 1:
            plan.setdefault(1, []).append(e)

    tags = bytearray()
    for f in range(1, total + 1):
        for e in plan.get(f, []):
            tags += place_tag(e)
        tags += SB.tag_bytes(1, b"")
    swf = os.path.join(os.environ["TEMP"], "_hv_%d.swf" % F)
    SB.write(swf, src, SB.defs_blob(src) + bytes(tags), total)
    print("写出", swf, os.path.getsize(swf), "字节")
    os.makedirs(out, exist_ok=True)
    for f in os.listdir(out):
        os.remove(os.path.join(out, f))
    subprocess.run([JAVA, "-Xmx2g", "-jar", FFDEC, "-export", "frame", out, swf],
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    n = len([f for f in os.listdir(out) if f.endswith(".png")])
    print("导出", n, "帧 →", out, "（第 %d 帧 = 主帧 %d 当时的样子）" % (t_ref, F))


if __name__ == "__main__":
    main()
