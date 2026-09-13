# -*- coding: utf-8 -*-
import json, os, sys
d = sys.argv[1]
S = json.load(open(os.path.join(d,"as2_deep","strings_by_block.json"), encoding="utf-8"))
P = json.load(open(os.path.join(d,"as2_deep","pushes_by_block.json"), encoding="utf-8"))

seen = set(); allstr = []
for blk, arr in S.items():
    for s in arr:
        if s not in seen:
            seen.add(s); allstr.append(s)
for blk, arr in P.items():
    for t, v in arr:
        if t == "str" and v not in seen:
            seen.add(v); allstr.append(v)
print("全部去重字符串:", len(allstr))
longs = sorted([s for s in allstr if len(s) >= 6], key=len, reverse=True)
print("长度>=6 的:", len(longs))
print("\n===== 最长的 45 条 =====")
for s in longs[:45]: print("  ", s)
