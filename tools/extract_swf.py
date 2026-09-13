# -*- coding: utf-8 -*-
"""同福奇缘 SWF 资源提取器  by godot-bridge"""
import struct, zlib, os, sys, json, binascii

BODY = sys.argv[1]
OUT  = sys.argv[2]
buf  = open(BODY, "rb").read()
os.makedirs(OUT, exist_ok=True)
for d in ("audio","images","text","actions"):
    os.makedirs(os.path.join(OUT, d), exist_ok=True)

def cstr(b, off, lim=None):
    e = off
    end = len(b) if lim is None else min(len(b), off+lim)
    while e < end and b[e] != 0:
        e += 1
    return b[off:e].decode("utf-8", "replace"), e + 1

def rect_len(b, off):
    nb = b[off] >> 3
    return (5 + nb*4 + 7)//8

# ---------- 头部 ----------
p = 0
nb = buf[0] >> 3
p += (5 + nb*4 + 7)//8
fps  = struct.unpack_from("<H", buf, p)[0] / 256.0
nfrm = struct.unpack_from("<H", buf, p+2)[0]
p += 4
print("fps=%.2f frames=%d" % (fps, nfrm))

# ---------- 标签遍历 ----------
tags = []
while p + 2 <= len(buf):
    rh = struct.unpack_from("<H", buf, p)[0]; p += 2
    code = rh >> 6; ln = rh & 0x3F
    if ln == 0x3F:
        ln = struct.unpack_from("<I", buf, p)[0]; p += 4
    if code == 0: break
    tags.append((code, p, ln)); p += ln
print("标签数 =", len(tags))

# ---------- 各类型提取 ----------
def w(path, data):
    with open(path, "wb") as f: f.write(data)
    return len(data)

def png_write(path, w_, h_, rgba):
    """极简 PNG 编码器"""
    raw = b"".join(b"\x00" + rgba[y*w_*4:(y+1)*w_*4] for y in range(h_))
    def chunk(t, d):
        c = t + d
        return struct.pack(">I", len(d)) + c + struct.pack(">I", binascii.crc32(c) & 0xffffffff)
    hdr = struct.pack(">IIBBBBB", w_, h_, 8, 6, 0, 0, 0)
    w(path, b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", hdr) + chunk(b"IDAT", zlib.compress(raw)) + chunk(b"IEND", b""))

def lossless_decode(fmt, w_, h_, raw):
    """返回 RGBA 字节"""
    out = bytearray(w_*h_*4)
    if fmt == 3:
        ncol = len(raw)
        # 结构: RGB colormap (PIX24?) 简化处理，暂不实现
        return None
    if fmt == 4:   # 15-bit
        pads = (4 - (w_ % 4)) % 4
        i = 0
        for y in range(h_):
            for x in range(w_):
                v = struct.unpack_from(">H", raw, i)[0]; i += 2
                r = (v >> 10) & 0x1F; g = (v >> 5) & 0x1F; b = v & 0x1F
                o = (y*w_+x)*4
                out[o]   = (r << 3) | (r >> 2)
                out[o+1] = (g << 3) | (g >> 2)
                out[o+2] = (b << 3) | (b >> 2)
                out[o+3] = 255
            i += pads
        return bytes(out)
    if fmt == 5:   # 24-bit
        pads = (4 - (w_ % 4)) % 4
        i = 0
        for y in range(h_):
            for x in range(w_):
                r,g,b = raw[i], raw[i+1], raw[i+2]; i += 3
                o = (y*w_+x)*4
                out[o],out[o+1],out[o+2],out[o+3] = r,g,b,255
            i += pads
        return bytes(out)
    return None

stats = {"sound":0,"image":0,"text":0,"action":0,"label":0}
exttxt = []

for idx, (code, off, ln) in enumerate(tags):
    try:
        if code == 14:   # DefineSound
            p_ = off + 2
            si = buf[p_]; p_ += 1
            fmt = si >> 4
            rate = (si >> 2) & 3
            typ  = si & 1
            cnt  = struct.unpack_from("<I", buf, p_)[0]; p_ += 4
            data = buf[p_:off+ln]
            if fmt == 2:  # MP3
                for k in range(0, min(4, len(data)-1)):
                    if data[k] == 0xFF and (data[k+1] & 0xE0) == 0xE0:
                        data = data[k:]; break
                ext = "mp3"
            elif fmt == 0: ext = "pcm_be"
            elif fmt == 3: ext = "pcm_le"
            else:          ext = "raw%d" % fmt
            name = "snd%03d_f%d_r%d_%s_%dc.%s" % (idx, fmt, rate, "st" if typ else "mo", cnt, ext)
            w(os.path.join(OUT,"audio",name), data)
            stats["sound"] += 1

        elif code == 6:  # DefineBits
            cid = struct.unpack_from("<H", buf, off)[0]
            d = buf[off+2:off+ln]
            w(os.path.join(OUT,"images","img%03d_id%d_bitmap.jpg" % (idx,cid)), d)
            stats["image"] += 1

        elif code == 21: # DefineBitsJPEG2
            cid = struct.unpack_from("<H", buf, off)[0]
            d = buf[off+2:off+ln]
            if d[:3] == b"\xff\xd8\xff": ext = "jpg"
            elif d[:8] == b"\x89PNG\r\n\x1a\n": ext = "png"
            elif d[:3] == b"GIF": ext = "gif"
            else: ext = "bin"
            w(os.path.join(OUT,"images","img%03d_id%d_jpeg2.%s" % (idx,cid,ext)), d)
            stats["image"] += 1

        elif code == 35: # DefineBitsJPEG3
            cid = struct.unpack_from("<H", buf, off)[0]
            aoff = struct.unpack_from("<I", buf, off+2)[0]
            jpg = buf[off+6:off+6+aoff]
            w(os.path.join(OUT,"images","img%03d_id%d_jpeg3.jpg" % (idx,cid)), jpg)
            try:
                alpha = zlib.decompress(buf[off+6+aoff:off+ln])
                w(os.path.join(OUT,"images","img%03d_id%d_jpeg3.alpha" % (idx,cid)), alpha)
            except Exception: pass
            stats["image"] += 1

        elif code in (20, 36):  # DefineBitsLossless / 2
            cid = struct.unpack_from("<H", buf, off)[0]
            fmt = buf[off+2]
            w_ = struct.unpack_from("<H", buf, off+3)[0]
            h_ = struct.unpack_from("<H", buf, off+5)[0]
            try:
                raw = zlib.decompress(buf[off+7:off+ln])
                rgba = lossless_decode(fmt, w_, h_, raw)
                if rgba:
                    png_write(os.path.join(OUT,"images","img%03d_id%d_loss%d.png" % (idx,cid,fmt)), w_, h_, rgba)
                else:
                    w(os.path.join(OUT,"images","img%03d_id%d_loss%d.raw" % (idx,cid,fmt)), raw)
            except Exception as e:
                w(os.path.join(OUT,"images","img%03d_id%d_loss%d.z" % (idx,cid,fmt)), buf[off+7:off+ln])
            stats["image"] += 1

        elif code == 37: # DefineEditText
            p_ = off + 2
            p_ += rect_len(buf, p_)
            f1 = buf[p_]; f2 = buf[p_+1]; p_ += 2
            has_text   = (f1 >> 7) & 1
            has_color  = (f1 >> 2) & 1
            has_maxlen = (f1 >> 1) & 1
            has_font   = f1 & 1
            has_class  = (f2 >> 7) & 1
            has_layout = (f2 >> 5) & 1
            if has_font: p_ += 2
            if has_class: _, p_ = cstr(buf, p_)
            p_ += 2                       # FontHeight 恒存在
            if has_color:  p_ += 4
            if has_maxlen: p_ += 2
            if has_layout: p_ += 9
            var, p_ = cstr(buf, p_)
            txt = ""
            if has_text:
                txt, p_ = cstr(buf, p_)
                # 闪存字符串里 &#13; 之类不处理
                exttxt.append({"idx":idx,"var":var,"text":txt})
                stats["text"] += 1

        elif code == 43: # FrameLabel
            s, _ = cstr(buf, off, ln)
            stats["label"] += 1

        elif code == 12 or code == 59:  # DoAction / DoInitAction
            w(os.path.join(OUT,"actions","act%04d_c%d.bin" % (idx,code)), buf[off:off+ln])
            stats["action"] += 1
    except Exception as e:
        pass

print("提取统计:", stats)
with open(os.path.join(OUT,"text","edittexts.json"), "w", encoding="utf-8") as f:
    json.dump(exttxt, f, ensure_ascii=False, indent=1)
print("文本框落盘:", len(exttxt))
