# -*- coding: utf-8 -*-
"""修复图片提取 + 抽取 DefineEditText 变量名 + 查看逻辑块规模"""
import struct, os, sys, json, glob, zlib

BODY = sys.argv[1]; OUT = sys.argv[2]
buf = open(BODY,"rb").read()
IDIR = os.path.join(OUT,"images"); os.makedirs(IDIR, exist_ok=True)

def cstr(b, off, lim=None):
    e = off; end = len(b) if lim is None else min(len(b), off+lim)
    while e < end and b[e] != 0: e += 1
    return b[off:e].decode("utf-8","replace"), e+1

def rect_len(b, off): return (5 + (b[off]>>3)*4 + 7)//8

def jpeg_slice(d):
    """跳过 Flash 塞的前导 FFD9 / 重复 FFD8"""
    i = 0
    while True:
        i = d.find(b"\xff\xd8\xff", i)
        if i < 0: return None
        if d[i+3] not in (0xD8, 0xD9): return d[i:]
        i += 3

# 读 JPEGTables
def get_jpegtables(buf):
    p = 0; nb = buf[0]>>3; p += (5+nb*4+7)//8 + 4
    while p < len(buf)-2:
        rh = struct.unpack_from("<H",buf,p)[0]; code = rh>>6; ln = rh&0x3F; p += 2
        if ln == 0x3F: ln = struct.unpack_from("<I",buf,p)[0]; p += 4
        if code == 0: break
        if code == 8: return buf[p:p+ln]
        p += ln
    return None

jt = get_jpegtables(buf)
print("JPEGTables:", len(jt) if jt else 0, "字节")

for f in glob.glob(os.path.join(IDIR,"*.bin")): os.remove(f)
p = 0; nb = buf[0]>>3; p += (5+nb*4+7)//8 + 4
imgs = 0; varnames = []
while p < len(buf)-2:
    rh = struct.unpack_from("<H",buf,p)[0]; code = rh>>6; ln = rh&0x3F; p += 2
    if ln == 0x3F: ln = struct.unpack_from("<I",buf,p)[0]; p += 4
    if code == 0: break
    off = p; p += ln
    if code == 6:                      # DefineBits: 需要拼 JPEGTables
        cid = struct.unpack_from("<H",buf,off)[0]
        d = buf[off+2:off+ln]
        full = (jt[:-2] if jt and jt.endswith(b"\xff\xd9") else jt or b"") + d
        s = jpeg_slice(full) or full
        open(os.path.join(IDIR,"bit_id%d.jpg"%cid),"wb").write(s); imgs += 1
    elif code == 21:                   # DefineBitsJPEG2
        cid = struct.unpack_from("<H",buf,off)[0]
        d = buf[off+2:off+ln]
        if d[:8] == b"\x89PNG\r\n\x1a\n":
            open(os.path.join(IDIR,"png_id%d.png"%cid),"wb").write(d)
        else:
            s = jpeg_slice(d) or d
            open(os.path.join(IDIR,"img_id%d.jpg"%cid),"wb").write(s)
        imgs += 1
    elif code == 35:
        cid = struct.unpack_from("<H",buf,off)[0]
        aoff = struct.unpack_from("<I",buf,off+2)[0]
        s = jpeg_slice(buf[off+6:off+6+aoff])
        if s: open(os.path.join(IDIR,"img3_id%d.jpg"%cid),"wb").write(s)
        imgs += 1
    elif code == 37:
        q = off+2; q += rect_len(buf,q)
        f1 = buf[q]; f2 = buf[q+1]; q += 2
        ht=(f1>>7)&1; hc=(f1>>2)&1; hm=(f1>>1)&1; hf=f1&1
        hcl=(f2>>7)&1; hl=(f2>>5)&1
        if hf: q += 2
        if hcl: _, q = cstr(buf,q)
        q += 2
        if hc: q += 4
        if hm: q += 2
        if hl: q += 9
        var, q = cstr(buf,q)
        txt = ""
        if ht: txt, q = cstr(buf,q)
        varnames.append({"id":struct.unpack_from("<H",buf,off)[0],"var":var,"text":txt})
print("图片写出:", imgs, "个")
json.dump(varnames, open(os.path.join(OUT,"text","edittext_vars.json"),"w",encoding="utf-8"), ensure_ascii=False, indent=1)
named = [v for v in varnames if v["var"]]
print("DefineEditText 共 %d 个，其中有变量名 %d 个" % (len(varnames), len(named)))
print("变量名样例:", [v["var"] for v in named[:40]])
