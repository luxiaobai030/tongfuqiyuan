# -*- coding: utf-8 -*-
"""AS2 动作块解析：常量池 + Push 值 + 反汇编"""
import struct, os, sys, json, glob

ADIR = sys.argv[1]
OUT  = sys.argv[2]
os.makedirs(OUT, exist_ok=True)
os.makedirs(os.path.join(OUT, "disasm"), exist_ok=True)

def rd_str(b, p):
    e = p
    while e < len(b) and b[e] != 0: e += 1
    return b[p:e].decode("utf-8", "replace"), e + 1

NAMES = {
 0x04:"NextFrame",0x05:"PrevFrame",0x06:"Play",0x07:"Stop",0x08:"ToggleQuality",
 0x09:"StopSounds",0x0A:"Add",0x0B:"Subtract",0x0C:"Multiply",0x0D:"Divide",
 0x0E:"Equals",0x0F:"Less",0x10:"And",0x11:"Or",0x12:"Not",0x13:"StringEquals",
 0x14:"StringLength",0x15:"StringExtract",0x17:"Pop",0x18:"ToInteger",0x19:"GetVariable",
 0x1A:"SetVariable",0x1B:"SetTarget2",0x1C:"StringAdd",0x1D:"GetProperty",
 0x1E:"SetProperty",0x20:"CloneSprite",0x21:"RemoveSprite",0x22:"Trace",0x23:"StartDrag",
 0x24:"EndDrag",0x25:"StringLess",0x26:"Throw",0x27:"CastOp",0x28:"ImplementsOp",
 0x2A:"Delete",0x2B:"Delete2",0x2C:"DefineLocal",0x2D:"CallFunction",0x2E:"Return",
 0x2F:"Modulo",0x30:"NewObject",0x31:"DefineLocal2",0x32:"InitArray",0x33:"InitObject",
 0x34:"TypeOf",0x35:"TargetPath",0x36:"Enumerate",0x37:"Add2",0x38:"Less2",
 0x39:"Equals2",0x3A:"ToNumber",0x3B:"ToString",0x3C:"PushDuplicate",0x3D:"StackSwap",
 0x3E:"GetMember",0x3F:"SetMember",0x40:"Increment",0x41:"Decrement",0x42:"CallMethod",
 0x43:"NewMethod",0x44:"InstanceOf",0x45:"Enumerate2",0x46:"BitAnd",0x47:"BitOr",
 0x48:"BitXor",0x49:"BitLShift",0x4A:"BitRShift",0x4B:"BitURShift",0x4C:"StrictEquals",
 0x4D:"Greater",0x4E:"StringGreater",0x50:"Extends",0x51:"GotoFrame",0x52:"GetURL",
 0x53:"StoreRegister",0x54:"ConstantPool",0x55:"StrictMode",0x5A:"WaitForFrame",
 0x5B:"SetTarget",0x5C:"GotoLabel",0x5D:"WaitForFrame2",0x60:"DefineFunction2",
 0x61:"Try",0x62:"With",0x63:"DefineFunction",0x64:"DefineButtonEvent",
 0x81:"GotoFrame",0x83:"GetURL",0x87:"StoreRegister",0x88:"ConstantPool",
 0x8A:"WaitForFrame",0x8B:"SetTarget",0x8C:"GotoLabel",0x8D:"WaitForFrame2",
 0x8E:"DefineFunction2",0x94:"With",0x96:"Push",0x99:"Jump",0x9A:"GetURL2",
 0x9B:"DefineFunction",0x9D:"If",0x9E:"Call",0x9F:"GotoFrame2",
}

all_strings = {}
all_pushes  = {}
const_pool  = {}

for f in sorted(glob.glob(os.path.join(ADIR, "*.bin"))):
    name = os.path.basename(f)
    b = open(f, "rb").read()
    p = 0
    strings, pushes, dis = [], [], []
    while p < len(b):
        code = b[p]; p += 1
        if code == 0:
            dis.append("  End"); break
        if code >= 0x80:
            ln = struct.unpack_from("<H", b, p)[0]; p += 2
            pl = b[p:p+ln]; p += ln
        else:
            pl = None; ln = 0
        nm = NAMES.get(code, "OP%02X" % code)
        if code == 0x88 and pl is not None and len(pl) >= 2:      # ConstantPool
            cnt = struct.unpack_from("<H", pl, 0)[0]
            q = 2
            for i in range(cnt):
                s, q = rd_str(pl, q)
                strings.append(s)
            const_pool[name] = strings
            dis.append("  ConstantPool x%d: %s" % (cnt, " | ".join(strings[:8])))
        elif code == 0x96 and pl is not None:    # Push
            q = 0
            while q < len(pl):
                t = pl[q]; q += 1
                if t == 0:
                    s, q = rd_str(pl, q); pushes.append(("str", s)); dis.append("  Push str  %r" % s)
                elif t == 1:
                    v = struct.unpack_from("<f", pl, q)[0]; q += 4; pushes.append(("f", v)); dis.append("  Push f    %s" % v)
                elif t == 2: pushes.append(("null", None)); dis.append("  Push null")
                elif t == 3: pushes.append(("undef", None)); dis.append("  Push undef")
                elif t == 4: v = pl[q]; q += 1; pushes.append(("reg", v)); dis.append("  Push reg  %d" % v)
                elif t == 5: v = pl[q]; q += 1; pushes.append(("bool", v)); dis.append("  Push bool %d" % v)
                elif t == 6:
                    v = struct.unpack_from("<d", pl, q)[0]; q += 8; pushes.append(("d", v)); dis.append("  Push d    %s" % v)
                elif t == 7:
                    v = struct.unpack_from("<i", pl, q)[0]; q += 4; pushes.append(("i", v)); dis.append("  Push i    %d" % v)
                elif t == 8: v = pl[q]; q += 1; pushes.append(("c8", v)); dis.append("  Push c8   %d" % v)
                elif t == 9:
                    v = struct.unpack_from("<H", pl, q)[0]; q += 2; pushes.append(("c16", v)); dis.append("  Push c16  %d" % v)
                else:
                    dis.append("  Push ??? type=%d" % t); break
        elif code == 0x99 and pl is not None:    # Jump
            o = struct.unpack_from("<h", pl, 0)[0]; dis.append("  Jump      %+d" % o)
        elif code == 0x9D and pl is not None:    # If
            o = struct.unpack_from("<h", pl, 0)[0]; dis.append("  If        %+d" % o)
        elif code == 0x8C and pl is not None:    # GotoLabel
            s, _ = rd_str(pl, 0); dis.append("  GotoLabel %r" % s)
        elif code == 0x81 and pl is not None:    # GotoFrame
            fr = struct.unpack_from("<H", pl, 0)[0]; dis.append("  GotoFrame %d" % fr)
        elif pl is not None and len(pl) <= 6:
            dis.append("  %-14s %s" % (nm, pl.hex()))
        else:
            dis.append("  %s  (len=%d)" % (nm, 0 if pl is None else len(pl)))
    if strings: all_strings[name] = strings
    if pushes:  all_pushes[name]  = pushes
    if len(b) > 64:
        open(os.path.join(OUT,"disasm",name.replace(".bin",".txt")), "w", encoding="utf-8").write("\n".join(dis))

json.dump(all_strings, open(os.path.join(OUT,"strings_by_block.json"),"w",encoding="utf-8"), ensure_ascii=False, indent=1)
json.dump(all_pushes,  open(os.path.join(OUT,"pushes_by_block.json"),"w",encoding="utf-8"),  ensure_ascii=False, indent=1, default=str)
print("有常量池的块:", len(all_strings))
print("有 Push 的块:", len(all_pushes))
tot = sum(len(v) for v in all_strings.values())
print("常量池字符串总数:", tot)
nums = [x for v in all_pushes.values() for x in v if x[0] in ("i","f","d")]
print("数值 Push 总数:", len(nums))


