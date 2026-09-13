# -*- coding: utf-8 -*-
import json, os, sys, collections
d = sys.argv[1]
V = json.load(open(os.path.join(d,"text","edittext_vars.json"), encoding="utf-8"))
names = [v["var"] for v in V if v["var"]]
uniq = sorted(set(names))
print("变量总数:", len(names), " 去重:", len(uniq))
g = collections.OrderedDict()
for n in uniq:
    pre = n.split("_")[0] if "_" in n else "(全局)"
    g.setdefault(pre, []).append(n)
for k, arr in g.items():
    print("\n== %s (%d) ==" % (k, len(arr)))
    print("   " + "  ".join(arr))
