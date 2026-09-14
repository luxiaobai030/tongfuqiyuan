# -*- coding: utf-8 -*-
"""把战斗胜利提示框里的奖励文字改成和实际奖励一致。

原版这一屏（主时间轴第 2545 帧）的奖励数字是「画死在画面里的静态美术字」
（DefineText 2388 / 2389），不是一个会跟着变的变量，所以战斗奖励翻倍之后，
框里的字还停在老的 +3 / +5 / +10 / +50 和「一张武林帖」。

做法：
  1. 从 tools/build_logic.py 读奖励表（REWARD_X2 × REWARD_MULT），算出新文字；
  2. 复制 decompiled/texts 到临时目录，改掉 2388 / 2389 两个文件；
  3. ffdec 批量导入文字，得到一份改过文字的 SWF 副本；
  4. 按原版第 2545 帧的显示列表（haltview）渲染成 PNG，覆盖 decompiled/frames/2545.png；
  5. 顺带把游戏里用到的那张背景图（第 2545 帧 -> 背景图 id）也换掉。

跑完再导一次 exe 就能看到新数字。奖励数值改了要重跑本工具；
如果数字位数变了（比如金钱从三位变四位），第二列的 GAP2 可能要跟着调。

用法：python tools/build_reward_panel.py
"""
import os, io, re, sys, ast, json, shutil, subprocess
import struct
sys.stdout.reconfigure(encoding="utf-8")
import numpy as np
from PIL import Image

B = r"F:\路小白。。\一些尝试\游戏\同福奇缘_移植"
DEC = os.path.join(B, "decompiled")
FRAMES = os.path.join(DEC, "frames")
TEXTS = os.path.join(DEC, "texts")
GAME = os.path.join(B, "game")
BG = os.path.join(GAME, "assets", "bg")
FRAME = 2545                     # 战斗胜利结算那一帧
TEXT_ID_BOX = "2389"             # 框里三行文字（生命 / 修为 / 技力 + 金钱）
TEXT_ID_WLT = "2388"             # 「得到武林帖一张！」
REC_SEP = "\r\n--- RECORDSEPARATOR ---\r\n"
JAVA = r"F:\APP\jre\jdk-21.0.12.1+1-jre\bin\java.exe"
FFDEC = r"F:\APP\ffdec\ffdec.jar"
TMP = os.path.join(B, "_poc", "reward_panel")
## 排版：原版第一列「生命+3」后面 7 个空格、第二列后面也是 7 个空格。
## 翻倍后第二列多一位数字，减掉一格空格，第三列才会落回原来的位置。
GAP1 = " " * 7
GAP2 = " " * 6
CN_NUM = {1: "一", 2: "两", 3: "三", 4: "四", 5: "五", 6: "六", 7: "七", 8: "八", 9: "九", 10: "十"}


def reward_values():
    """读 tools/build_logic.py 里的奖励表，和逻辑生成器用同一份数值"""
    src = io.open(os.path.join(B, "tools", "build_logic.py"), encoding="utf-8").read()
    table, mult = None, 1
    for node in ast.parse(src).body:
        if isinstance(node, ast.Assign) and isinstance(node.targets[0], ast.Name):
            if node.targets[0].id == "REWARD_X2":
                table = ast.literal_eval(node.value)
            elif node.targets[0].id == "REWARD_MULT":
                mult = ast.literal_eval(node.value)
    assert table and mult, "没读到 tools/build_logic.py 里的 REWARD_X2 / REWARD_MULT"
    return {var: base * mult for var, base in table}, mult


def box_text(v):
    return ("生命+%d" % v["hp"] + GAP1 + "得到修为%d点" % v["xiuwei"] + GAP2 + "掌柜技力%d点" % v["ZG_JL"]
            + REC_SEP + "金钱+%d" % v["money"])


def wlt_text(v):
    return "得到武林帖%s张！" % CN_NUM.get(v["WLT"], str(v["WLT"]))


def patched_swf(v):
    """改文字 -> 导入 -> 得到改过文字的 SWF 副本"""
    shutil.rmtree(TMP, ignore_errors=True)
    dst = os.path.join(TMP, "texts")
    os.makedirs(dst)
    ## 只放要改的两个文件：整份文字表里有一个（1158）ffdec 读不回去，会整批放弃导入
    for tid in (TEXT_ID_BOX, TEXT_ID_WLT):
        shutil.copyfile(os.path.join(TEXTS, tid + ".txt"), os.path.join(dst, tid + ".txt"))
    io.open(os.path.join(dst, TEXT_ID_BOX + ".txt"), "w", encoding="utf-8", newline="").write(box_text(v))
    io.open(os.path.join(dst, TEXT_ID_WLT + ".txt"), "w", encoding="utf-8", newline="").write(wlt_text(v))
    src_swf = os.path.join(B, "原版", "同福奇缘.swf")
    out = os.path.join(TMP, "patched.swf")
    subprocess.run([JAVA, "-jar", FFDEC, "-importText", src_swf, out, TMP], check=True)
    check_text_changed(src_swf, out)
    print("   改过文字的 SWF：", out)
    return out


def text_tag(path, charid):
    """取出某个静态文字角色（DefineText，tag 11）的原始字节，用来确认文字真的被改到"""
    body = open(path, "rb").read()[8:]
    p = (5 + (body[0] >> 3) * 4 + 7) // 8 + 4
    while p + 2 <= len(body):
        rh = struct.unpack_from("<H", body, p)[0]
        p += 2
        code, ln = rh >> 6, rh & 0x3F
        if ln == 0x3F:
            ln = struct.unpack_from("<I", body, p)[0]
            p += 4
        if code == 0:
            break
        if code == 11 and struct.unpack_from("<H", body, p)[0] == charid:
            return bytes(body[p:p + ln])
        p += ln
    return None


def check_text_changed(src_swf, out_swf):
    for tid in (TEXT_ID_BOX, TEXT_ID_WLT):
        a, b = text_tag(src_swf, int(tid)), text_tag(out_swf, int(tid))
        assert a and b, "SWF 里找不到文字角色 %s" % tid
        assert a != b, "文字 %s 没被改到（ffdec 导入没生效？）" % tid


def render_frame(swf, outdir):
    env = dict(os.environ, TFQY_SWF=swf)
    subprocess.run([sys.executable, "-X", "utf8", os.path.join(B, "tools", "haltview.py"),
                    str(FRAME), "0", outdir], check=True, env=env)
    shots = sorted(os.listdir(outdir), key=lambda f: int(re.findall(r"\d+", f)[0]))
    return os.path.join(outdir, shots[-1])


def main():
    v, mult = reward_values()
    print("奖励表（x%d）：%s" % (mult, v))
    print("提示框文字：", box_text(v).replace(REC_SEP, " / "), "/", wlt_text(v))
    png = render_frame(patched_swf(v), os.path.join(TMP, "shot"))
    new = Image.open(png).convert("RGB")
    old_path = os.path.join(FRAMES, "%d.png" % FRAME)
    if os.path.exists(old_path):
        old = Image.open(old_path).convert("RGB")
        if old.size == new.size:
            d = np.abs(np.asarray(old).astype(int) - np.asarray(new).astype(int)).sum(axis=2)
            ys, xs = np.where(d > 12)
            if len(ys):
                print("   和旧画面比，改动范围：x %d..%d  y %d..%d（应该只在提示框文字上）"
                      % (xs.min(), xs.max(), ys.min(), ys.max()))
                assert 440 <= ys.min() and ys.max() <= 580 and xs.min() >= 200, "改动跑出提示框范围了，先别覆盖"
            else:
                assert False, "渲染出来和旧画面一模一样，说明文字没改到，先别覆盖"
    new.save(old_path, "PNG")
    print("   已更新", old_path)
    bg_id = json.load(io.open(os.path.join(GAME, "data", "frames.json"), encoding="utf-8"))["bg"].get(str(FRAME))
    if bg_id:
        bg_path = os.path.join(BG, bg_id + ".webp")
        new.save(bg_path, "WEBP", lossless=True, method=0)
        print("   已更新背景图", bg_path, "（第 %d 帧用的就是这张）" % FRAME)
    print("完成。重新导出 exe 就能看到新数字。")


if __name__ == "__main__":
    main()
