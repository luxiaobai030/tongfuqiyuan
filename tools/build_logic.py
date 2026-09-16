# -*- coding: utf-8 -*-
"""生成 Godot 侧的逻辑文件：原版帧脚本 + 按钮脚本"""
import os, io, sys, re, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.stdout.reconfigure(encoding="utf-8")
from as2_to_gd import convert

DEC = r"F:\路小白。。\一些尝试\游戏\同福奇缘_移植\decompiled"
OUT = r"F:\路小白。。\一些尝试\游戏\同福奇缘_移植\game\scripts\ported\logic.gd"
S = os.path.join(DEC, "scripts")

frames = {}
buttons = {}       # id -> {"release": code, "hover": code}
skipped = 0
for d in sorted(os.listdir(S)):
    full = os.path.join(S, d)
    if not os.path.isdir(full): continue
    if d.startswith("frame_"):
        n = int(d.split("_")[1])
        f = os.path.join(full, "DoAction.as")
        if not os.path.exists(f): continue
        src = io.open(f, encoding="utf-8").read().strip()
        if src == "":
            continue
        frames[n] = convert(src)
    elif d.startswith("DefineButton2_"):
        bid = d.split("_")[1]
        for root, _, files in os.walk(full):
            for fn in files:
                src = io.open(os.path.join(root, fn), encoding="utf-8").read().strip()
                if not src: continue
                low = src[:120]
                if "on(rollOver" in low:
                    buttons.setdefault(bid, {})["hover"] = convert(src)
                elif "on(rollOut" in low:
                    buttons.setdefault(bid, {})["out"] = convert(src)
                elif "on(release" in low or "on(press" in low:
                    prev = buttons.setdefault(bid, {}).get("release")
                    code = convert(src)
                    buttons[bid]["release"] = (prev + code) if prev else code

## 用户要求：战斗胜利的奖励翻倍。
## 第 2545 帧是战斗胜利的结算（原版：生命 +3 / 修为 +5 / 技力 +10 / 威望 +1 / 铜钱 +50）。
REWARD_X2 = [("hp", 3), ("xiuwei", 5), ("ZG_JL", 10), ("WLT", 1), ("money", 50)]
REWARD_MULT = 2          # 翻倍倍数，tools/build_reward_panel.py 会读这两行，改奖励只要改这里
if 2545 in frames:
    code = frames[2545]
    for var, base in REWARD_X2:
        old = '\tsetv("%s", _add(V("%s"), %d))\n' % (var, var, base)
        new = '\tsetv("%s", _add(V("%s"), %d))\n' % (var, var, base * REWARD_MULT)
        assert old in code, "第 2545 帧的奖励语句和预期不一样：" + old
        code = code.replace(old, new)
    frames[2545] = code

## 文本勘误：原版 SWF 里就写错的字，照搬下来游戏里也是错的。
TEXT_FIXES = [("赛貂禅", "赛貂蝉")]   # 预览里的人物是「赛貂蝉」，原版误写成「禅」
def _fix_text(s):
    for a, b in TEXT_FIXES:
        s = s.replace(a, b)
    return s
for _n in list(frames):
    frames[_n] = _fix_text(frames[_n])
for _bid in buttons:
    for _k in list(buttons[_bid]):
        buttons[_bid][_k] = _fix_text(buttons[_bid][_k])

def fname(prefix, n): return "_%s%s" % (prefix, n)

buf = io.StringIO()
w = buf.write
w('extends RefCounted\n')
w('## 本文件由 tools/build_logic.py 从原版 SWF 的 ActionScript 自动转译生成\n')
w('var vars: Dictionary = {}\n')
w('var jump := Callable()\n\n')
w('## 角色动画层的回调（原版剧本里 dr_boos.gotoAndPlay(24) 这类点名）\n')
w('var clip_go_cb := Callable()\n')
w('var clip_play_cb := Callable()\n')
w('var clip_stop_cb := Callable()\n')
w('func clip_go(nm: String, t) -> void:\n')
w('\tif clip_go_cb.is_valid(): clip_go_cb.call(nm, int(t))\n')
w('func clip_play(nm: String) -> void:\n')
w('\tif clip_play_cb.is_valid(): clip_play_cb.call(nm)\n')
w('func clip_stop(nm: String) -> void:\n')
w('\tif clip_stop_cb.is_valid(): clip_stop_cb.call(nm)\n\n')
w('func _num(x) -> float:\n')
w('\tif x is bool: return 1.0 if x else 0.0\n')
w('\tif x is String: return float(x) if x.is_valid_float() else 0.0\n')
w('\tif x == null: return 0.0\n')
w('\tif x is float or x is int: return float(x)\n')
w('\treturn 0.0\n')
w('## ActionScript 只有一种数字（双精度），Godot 里浮点数拼成字符串会带上「.0」：\n')
w('## setv("money", _sub(V("money"), 500)) 之后 money_tishi 会变成「500.0文」。\n')
w('## 所以加减乘除的结果只要是整数就转回整数（原版显示的是「500文」）。\n')
w('func _tidy(x):\n')
w('\tif x is float and absf(x) < 1e15 and absf(x - roundf(x)) < 0.0001:\n')
w('\t\treturn int(roundf(x))\n')
w('\treturn x\n')
w('func _snum(x) -> String:\n\tvar t = _tidy(x)\n\treturn t if t is String else str(t)\n')
w('func _add(a, b):\n')
w('\tif a is String or b is String: return _snum(a) + _snum(b)\n')
w('\tif (a is int or a is float) and (b is int or b is float): return _tidy(a + b)\n')
w('\treturn _tidy(_num(a) + _num(b))\n')
w('func _sub(a, b): return _tidy(_num(a) - _num(b))\n')
w('func _mul(a, b): return _tidy(_num(a) * _num(b))\n')
w('func _div(a, b):\n\tvar d := _num(b)\n\treturn 0 if d == 0.0 else _tidy(_num(a) / d)\n')
w('func _eq(a, b) -> bool:\n\tif a is String or b is String: return str(a) == str(b)\n\treturn _num(a) == _num(b)\n')
w('func _mod(a, b):\n\tvar d := _num(b)\n\treturn 0 if d == 0.0 else _tidy(_num(a) - floor(_num(a) / d) * d)\n')
w('func _truth(x) -> bool:\n\tif x is bool: return x\n\tif x is String: return x != ""\n\tif x == null: return false\n\treturn _num(x) != 0.0\n')
w('func _ne(a, b) -> bool:\n\tif a is String or b is String: return str(a) != str(b)\n\treturn _num(a) != _num(b)\n')
w('func _lt(a, b):\n\tif a is String and b is String: return a < b\n\treturn _num(a) < _num(b)\n')
w('func _gt(a, b):\n\tif a is String and b is String: return a > b\n\treturn _num(a) > _num(b)\n')
w('func _le(a, b): return not _gt(a, b)\n')
w('func _ge(a, b): return not _lt(a, b)\n')
w('## ActionScript 的变量名不区分大小写，这里统一转小写；ALIAS 处理原版里的错别字\n')
w('const ALIAS := {\n')
w('\t"lb_chenhao": "lb_chenghao", "dz_chenhao": "dz_chenghao",\n')
w('\t"xg_chenhao": "xg_chenghao", "xc_chenhao": "xc_chenghao",\n')
w('\t"ws_chenhao": "ws_chenghao", "xb_chenhao": "xb_chenghao",\n')
w('\t"zg_chenhao": "zg_chenghao", "xc_zhongchen": "xc_zhongcheng",\n')
w('}\n')
w('func _key(n: String) -> String:\n\tvar k := n.to_lower()\n\treturn ALIAS.get(k, k)\n')
w('func V(n: String):\n\tvar v = vars.get(_key(n))\n\treturn 0 if v == null else v\n')
w('func setv(n: String, v) -> void: vars[_key(n)] = v\n')
w('func unknown_call(n: String, a: Array):\n\tpass\n')
w('var halted := false\n')
w('var want_stop_sounds := false\n')
w('func halt_mm() -> void: halted = true\n')
w('func resume_mm() -> void: halted = false\n')
w('func stop_sounds() -> void: want_stop_sounds = true\n')
w('func G(t) -> void:\n\tjump.call(int(t))\n\n')

w('func run_frame(n: int) -> void:\n\tmatch n:\n')
for n in sorted(frames):
    w('\t\t%d: %s()\n' % (n, fname("f", n)))
w('\t\t_: pass\n\n')

w('func has_frame(n: int) -> bool:\n\treturn n in FRAME_IDS\n\n')
w('const FRAME_IDS := [%s]\n\n' % ", ".join(str(n) for n in sorted(frames)))

w('func run_button(id: int) -> void:\n\tmatch id:\n')
for bid in sorted(buttons, key=lambda x: int(x)):
    if "release" in buttons[bid]:
        w('\t\t%s: %s()\n' % (bid, fname("b", bid)))
w('\t\t_: pass\n\n')

w('func run_button_hover(id: int) -> void:\n\tmatch id:\n')
for bid in sorted(buttons, key=lambda x: int(x)):
    if "hover" in buttons[bid]:
        w('\t\t%s: %s_h()\n' % (bid, fname("b", bid)))
w('\t\t_: pass\n\n')

w('func run_button_out(id: int) -> void:\n\tmatch id:\n')
for bid in sorted(buttons, key=lambda x: int(x)):
    if "out" in buttons[bid]:
        w('\t\t%s: %s_o()\n' % (bid, fname("b", bid)))
w('\t\t_: pass\n\n')

for n in sorted(frames):
    w('func %s() -> void:\n' % fname("f", n))
    w(frames[n])
    w('\n')
for bid in sorted(buttons, key=lambda x: int(x)):
    if "release" in buttons[bid]:
        w('func %s() -> void:\n' % fname("b", bid))
        w(buttons[bid]["release"]); w('\n')
    if "hover" in buttons[bid]:
        w('func %s_h() -> void:\n' % fname("b", bid))
        w(buttons[bid]["hover"]); w('\n')
    if "out" in buttons[bid]:
        w('func %s_o() -> void:\n' % fname("b", bid))
        w(buttons[bid]["out"]); w('\n')

io.open(OUT, "w", encoding="utf-8", newline="\n").write(buf.getvalue())
print("frames:", len(frames), "buttons:", len(buttons), "->", OUT, os.path.getsize(OUT), "bytes")
