# -*- coding: utf-8 -*-
"""小贝页晚上那一版（第 142 帧）的「允许」按钮：把原版那两个死按钮换成能用的。

原版第 142 帧《小贝属性_晚上》那两个位置放的是角色 368 —— SWF 里 taglen=41、
actionoffset=0，一个根本没写动作的按钮，可它渲染出来和白天版（345/346、369/370）
一个像素都不差。玩家点下去只会以为按钮坏了（「莫小贝没法去西凉河摸鱼，点两个
按钮都没有用」就是这么来的）。

这里把它们换成 369/370：白天能用，晚上拦住并说明原因（369/370 自带 time0 判断）。
改的是 game/data/ui.json，幂等，重复跑没有副作用。
"""
import io
import json
import os
import sys

sys.stdout.reconfigure(encoding="utf-8")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UI = os.path.join(ROOT, "game", "data", "ui.json")

## 帧号 → [(按钮中心的 y, 换成谁)]：这一帧 368 放了两个（上=后山探险 下=西凉河捉鱼）
FIX = {"142": [(372.4, 369), (418.4, 370)]}

ui = json.load(io.open(UI, encoding="utf-8"))
changed = 0
for frame, slots in FIX.items():
    for it in ui.get(frame, []):
        if it.get("k") != "btn" or int(it.get("id", -1)) != 368:
            continue
        cy = float(it["box"][1]) + float(it["box"][3]) / 2.0
        for want_y, want_id in slots:
            if abs(cy - want_y) < 1.0:
                it["id"] = want_id
                changed += 1
expect = sum(len(v) for v in FIX.values())
assert changed in (0, expect), "第 142 帧的 368 数量不对：%d" % changed
if changed:
    io.open(UI, "w", encoding="utf-8", newline="\n").write(json.dumps(ui, ensure_ascii=False))
print("换了 %d 个按钮 → %s" % (changed, UI))
