# -*- coding: utf-8 -*-
"""SWF 时间轴探查器：按名字找放置点、dump 任意 sprite 的时间轴结构"""
import struct, sys
sys.stdout.reconfigure(encoding="utf-8")

BODY = r"F:\路小白。。\一些尝试\游戏\同福奇缘_移植\body_uncompressed.bin"
buf = open(BODY, "rb").read()

p = 0
n0 = buf[0] >> 3
p += (5 + n0 * 4 + 7) // 8 + 4
ROOT_TAGS = p

tags = []
while p + 2 <= len(buf):
    rh = struct.unpack_from("<H", buf, p)[0]; p += 2
    code = rh >> 6; ln = rh & 0x3F
    if ln == 0x3F:
        ln = struct.unpack_from("<I", buf, p)[0]; p += 4
    if code == 0: break
    tags.append((code, p, ln)); p += ln

class Bits:
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

def skip_matrix_bit(b, byteoff):
    br = Bits(b, byteoff)
    if br.bits(1):
        nb = br.bits(5); br.sbits(nb); br.sbits(nb)
    if br.bits(1):
        nb = br.bits(5); br.sbits(nb); br.sbits(nb)
    nb = br.bits(5); br.sbits(nb); br.sbits(nb)
    br.align()
    return br.p // 8

def skip_cxform(b, off, alpha):
    pp = off
    f = b[pp]; pp += 1
    nb = (f >> 4) & 0xF
    n = 4 if alpha else 3
    sz = (nb * n + 7) // 8
    if f & 1: pp += sz
    if f & 2: pp += sz
    return pp

def parse_cxform(b, off):
    """颜色/透明度变换（原版用它在角色出现/消失时做淡入淡出）"""
    br = Bits(b, off)
    has_add = br.bits(1); has_mult = br.bits(1); nb = br.bits(4)
    mult = [br.sbits(nb) for _ in range(4)] if has_mult else None
    add = [br.sbits(nb) for _ in range(4)] if has_add else None
    br.align()
    return {"add": add, "mult": mult, "end": br.p // 8}

def cx_alpha(b, off):
    """这条变换对应的不透明度（0~1）"""
    c = parse_cxform(b, off)
    a = 1.0
    if c["mult"] is not None: a *= c["mult"][3] / 256.0
    if c["add"] is not None: a += c["add"][3] / 256.0
    return max(0.0, min(1.0, a))

def cstr(b, off, lim=None):
    e = off
    end = len(b) if lim is None else min(len(b), off + lim)
    while e < end and b[e] != 0: e += 1
    return b[off:e].decode("utf-8", "replace"), e + 1

def parse_place(b, q, code):
    """返回 dict(depth, charid, name, matrix_off, ...)"""
    if code == 4:
        charid, depth = struct.unpack_from("<HH", b, q)
        return {"depth": depth, "charid": charid, "name": "", "move": False}
    f1 = b[q]; pp = q + 1
    depth = struct.unpack_from("<H", b, pp)[0]; pp += 2
    f2 = 0
    name = ""; charid = -1; matrix = None
    if code == 70:
        f2 = b[pp]; pp += 1
        if f2 & 0x02:
            _, pp = cstr(b, pp)
        if f2 & 0x04:
            pass
        if f2 & 0x08: pp += 4
    if f1 & 0x02:
        charid = struct.unpack_from("<H", b, pp)[0]; pp += 2
    if f1 & 0x04:
        matrix = parse_matrix(b, pp)
        pp = matrix["end"]
    cx_off = -1
    if f1 & 0x08:
        cx_off = pp
        pp = skip_cxform(b, pp, True)
    if f1 & 0x10: pp += 2
    if code == 70 and (f2 & 0x80):
        n = b[pp]; pp += 1 + n * 6
    if f1 & 0x20:
        name, pp = cstr(b, pp)
    if code == 70 and (f2 & 0x40): pp += 1
    if code == 70 and (f2 & 0x20): pp += 4
    if code == 70 and (f2 & 0x10): pp += 1
    if code == 70 and (f2 & 0x08): pp += 4
    if f1 & 0x40: pp += 2
    return {"depth": depth, "charid": charid, "name": name, "move": bool(f1 & 1),
            "matrix": matrix, "cx_off": cx_off, "end": pp}

def parse_matrix(b, off):
    br = Bits(b, off)
    sx = sy = 1.0; r0 = r1 = 0.0
    if br.bits(1):
        nb = br.bits(5)
        sx = br.sbits(nb) / 65536.0; sy = br.sbits(nb) / 65536.0
    if br.bits(1):
        nb = br.bits(5)
        r0 = br.sbits(nb) / 65536.0; r1 = br.sbits(nb) / 65536.0
    nb = br.bits(5)
    tx = br.sbits(nb); ty = br.sbits(nb)
    br.align()
    return {"sx": sx, "sy": sy, "r0": r0, "r1": r1, "tx": tx, "ty": ty, "end": br.p // 8}

def tag_list(s, e):
    out = []; q = s
    while q < e - 2:
        rh = struct.unpack_from("<H", buf, q)[0]; q += 2
        c = rh >> 6; l = rh & 0x3F
        if l == 0x3F:
            l = struct.unpack_from("<I", buf, q)[0]; q += 4
        if c == 0: break
        out.append((c, q, l)); q += l
    return out

def sub_tags(sid):
    for (c, o, l) in tags:
        if c == 39 and struct.unpack_from("<H", buf, o)[0] == sid:
            return tag_list(o + 4, o + l)
    return None

def all_names():
    """全局：所有 PlaceObject2/3 的名字 -> (owner, depth, charid)"""
    res = {}
    def scan(owner, s, e):
        for (c, q, l) in tag_list(s, e):
            if c in (4, 26, 70):
                try: r = parse_place(buf, q, c)
                except Exception: continue
                if r.get("name"):
                    res.setdefault(r["name"], []).append((owner, r["depth"], r["charid"]))
    scan("root", ROOT_TAGS, len(buf))
    for (c, o, l) in tags:
        if c == 39:
            scan(struct.unpack_from("<H", buf, o)[0], o + 4, o + l)
    # 减去 root 的 o+l 边界（root 扫描到文件尾包含了 sprite 内部，简单起见保留）
    return res

def dump_timeline(sid, show_places=True):
    tl = sub_tags(sid)
    if tl is None:
        print("  没有 sprite %d" % sid); return
    print("  sprite %d：%d 个标签" % (sid, len(tl)))
    cur = {}
    n = 0
    for (c, q, l) in tl:
        if c == 1:
            n += 1
            if show_places:
                short = ", ".join("%d:%d%s" % (d, v[0], ("@" + v[1]) if v[1] else "") for d, v in sorted(cur.items()))
                print("    帧 %3d  %s" % (n, short))
            else:
                print("    帧 %3d" % n)
        elif c in (4, 26, 70):
            try: r = parse_place(buf, q, c)
            except Exception as ex:
                print("    ! 解析失败 off=%d: %s" % (q, ex)); continue
            d = r["depth"]
            if r["charid"] != -1:
                cur[d] = (r["charid"], r["name"] or (cur.get(d, (0, ""))[1]))
            elif r["name"]:
                cur[d] = (cur.get(d, (0, ""))[0], r["name"])
            if show_places:
                extra = ""
                if r.get("matrix"):
                    m = r["matrix"]
                    extra = " pos=(%.0f,%.0f) scale=(%.2f,%.2f) rot=(%.2f,%.2f)" % (m["tx"] / 20, m["ty"] / 20, m["sx"], m["sy"], m["r0"], m["r1"])
                print("    +B depth=%d char=%d name=%s%s" % (d, r["charid"], r["name"], extra))
        elif c == 5:
            cur.pop(struct.unpack_from("<H", buf, q)[0], None)
        elif c == 28:
            # RemoveObject2 的负载就是一个 UI16 深度（老代码误按 RemoveObject 的
            # “角色+深度”布局读了 q+2，导致绝大多数删除事件都没生效）
            cur.pop(struct.unpack_from("<H", buf, q)[0], None)
        elif c == 43:
            nm, _ = cstr(buf, q, l)
            print("    ### 帧标签: %s (第 %d 帧)" % (nm, n + 1))
        elif c == 12:
            print("    *** 帧脚本（%d 字节）: %s" % (l, buf[q:q + l][:120].hex(" ")))
        elif c == 39:
            print("    === 内嵌 sprite %d" % struct.unpack_from("<H", buf, q)[0])

if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "names"
    if mode == "names":
        nm = all_names()
        print("名字数:", len(nm))
        for k in sorted(nm):
            print("  %-14s %s" % (k, sorted(set(nm[k]))[:8]))
    elif mode == "sprite":
        dump_timeline(int(sys.argv[2]), len(sys.argv) > 3)
    elif mode == "find":
        nm = all_names()
        print(nm.get(sys.argv[2], "未找到"))
