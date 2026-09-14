# -*- coding: utf-8 -*-
"""从标题页底图里抠出木牌，做成移植版额外界面（菜单 / 存档框 / 道具框）的贴图。

原版标题页那几个木牌（开门营业 / 同心共难 / 合作伙伴 / 游戏说明）是直接画进
b0003.webp 的，没有单独的素材文件。移植版新加的界面要和它们同一套长相，
所以干脆把像素抠出来复用：

  plaque.png  155x42  一块没字的空木牌（中间的文字抹回底板色），
                      1:1 用在标题页「读档」按钮和菜单按钮上，不缩放。
  board.png   310x84  同一块木牌放大 2 倍（边框从 4px 变 8px），
                      给大面板当九宫格底图：四角留 MARGIN 边距，中间随便拉伸，
                      边框和四角云纹都不会变形。
  plaque_on.png       同 plaque.png，整体提亮一档，鼠标压上去时换这张。
  bar.png / bar_on.png  16x16 的窄条：只有底板和外框、没有云纹。右上角那块木牌
                      只有 20px 高，云纹挤进去会糊成一团，所以单独出一张小条。

木牌底板是纯色 (226,197,135)，所以抹字直接填底板色就行，不会留接缝。
"""
import os

from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
GAME = os.path.join(HERE, "..", "game")
SRC = os.path.join(GAME, "assets", "bg", "b0003.webp")
OUT = os.path.join(GAME, "assets", "ui")

# 标题页「开门营业」那块木牌在底图上的位置（逐像素量出来的：外框 4px 深棕，
# 四角云纹向内伸 17px，字是 (153,0,0) 的朱红）
BOX = (571, 196, 726, 238)
FILL = (226, 197, 135)
TEXT_RED_DIFF = 45       # r-g 超过这个值算字
MARGIN = 34              # board.png 的九宫格边距（放大后的 2 倍）
BAR = 16                 # bar.png 的边长（九宫格，边距 5）
BAR_EDGE = 2             # bar.png 的外框宽度


def brighten(im, k=1.09):
    """整体提亮一档（悬停态）。直接乘系数，深浅关系不变。"""
    return im.point(lambda v: min(255, int(v * k + 0.5)))


def make_bar():
    """窄条：只有底板和外框，四角不带云纹"""
    im = Image.new("RGB", (BAR, BAR), FILL)
    px = im.load()
    edge = (124, 90, 50)
    hi = (206, 176, 118)
    for y in range(BAR):
        for x in range(BAR):
            d = min(x, y, BAR - 1 - x, BAR - 1 - y)
            if d < BAR_EDGE:
                px[x, y] = edge
            elif d == BAR_EDGE:
                px[x, y] = hi
    return im


def text_box(im):
    """木牌上那行字占的像素范围（只认朱红，四角云纹是棕色，不会被算进来）"""
    x0, y0, x1, y1 = BOX
    px = im.load()
    xs, ys = [], []
    for y in range(y0 + 8, y1 - 8):
        for x in range(x0 + 20, x1 - 20):
            r, g, b = px[x, y]
            if r - g > TEXT_RED_DIFF and r > 130:
                xs.append(x)
                ys.append(y)
    if not xs:
        raise SystemExit("木牌上没找到字，底图是不是换了？")
    return min(xs), min(ys), max(xs), max(ys)


def main():
    im = Image.open(SRC).convert("RGB")
    tx0, ty0, tx1, ty1 = text_box(im)
    x0, y0, _, _ = BOX
    pl = im.crop(BOX)
    px = pl.load()
    # 往字外面多抹 3 圈，把抗锯齿的边一起盖掉
    for y in range(ty0 - 3 - y0, ty1 + 4 - y0):
        for x in range(tx0 - 3 - x0, tx1 + 4 - x0):
            px[x, y] = FILL

    # 验一下：中间那块除了四角云纹，应该只剩底板色
    bad = 0
    for y in range(18, pl.height - 18):
        for x in range(20, pl.width - 20):
            c = px[x, y]
            if abs(c[0] - FILL[0]) + abs(c[1] - FILL[1]) + abs(c[2] - FILL[2]) > 24:
                bad += 1

    os.makedirs(OUT, exist_ok=True)
    pl.save(os.path.join(OUT, "plaque.png"))
    brighten(pl).save(os.path.join(OUT, "plaque_on.png"))
    pl.resize((pl.width * 2, pl.height * 2), Image.NEAREST).save(os.path.join(OUT, "board.png"))
    bar = make_bar()
    bar.save(os.path.join(OUT, "bar.png"))
    brighten(bar).save(os.path.join(OUT, "bar_on.png"))
    print("plaque.png %dx%d  board.png %dx%d  抹字残留 %d 像素" %
          (pl.width, pl.height, pl.width * 2, pl.height * 2, bad))
    print("九宫格边距 = %d（board.png）/ %d（bar.png）" % (MARGIN, BAR_EDGE * 2 + 1))


if __name__ == "__main__":
    main()
