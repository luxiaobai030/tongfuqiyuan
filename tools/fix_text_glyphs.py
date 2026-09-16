# -*- coding: utf-8 -*-
'''把烧进画面里的美术字改对：目前只有一处 —— 帮助页「如果和老刑的关系够高」。

原版这行是静态美术字（DefineText），文字早就烤进整幅画面了，所以改错字只能
照游戏自己那套字（内嵌 f34 隶书 20px、#990000）把「邢」重画一遍盖掉原来的「刑」：
先按这一行上下两行之间的空白把底色插值补出来（免得留一块补丁），再把字叠上去。

改两个地方：
  decompiled/frames/457.png —— 画面来源，重新生成资源时不会把错字带回去
  game/assets/bg/b0208.webp —— 实际打包进游戏的那张
（decompiled/ 整体不进仓库，是从 原版/*.swf 现生成的；重跑解包以后要再跑一次本脚本。）

跑法：python -X utf8 tools/fix_text_glyphs.py
'''
import os
import numpy as np
from PIL import Image, ImageDraw, ImageFont

FONT_PATH = 'game/assets/fonts/f34.ttf'
SIZE = 20
INK = np.array([153, 0, 0], dtype=np.float64)      # 量出来的字色 #990000

WRONG, RIGHT = '刑', '邢'
BOX_X0, BOX_X1 = 329, 349          # 要重画的横范围
INK_X0, INK_Y0 = 330, 307          # 图里那个错字的墨迹左上角
ROW0, ROW1 = 304, 322              # 要重画的纵范围
CLEAN_ABOVE, CLEAN_BELOW = (300, 306), (322, 328)

TARGETS = [os.path.join('decompiled', 'frames', '457.png'),
           os.path.join('game', 'assets', 'bg', 'b0208.webp')]


def render(ch):
    img = Image.new('L', (64, 64), 0)
    ImageDraw.Draw(img).text((8, 8), ch, font=ImageFont.truetype(FONT_PATH, SIZE), fill=255)
    return np.asarray(img).astype(np.float64) / 255.0


def inkbox(m):
    ys, xs = np.nonzero(m > 0.45)
    return xs.min(), ys.min()


def _ink_mask(rgb):
    return ((rgb[..., 0] > 90) & (rgb[..., 1] < 110) & (rgb[..., 2] < 110)
            & ((rgb[..., 0] - rgb[..., 1]) > 40))


def _stamp(shape, glyph, x0, y0):
    out = np.zeros(shape, dtype=bool)
    gx, gy = inkbox(glyph)
    dx, dy = x0 - gx, y0 - gy
    for yy in range(glyph.shape[0]):
        for xx in range(glyph.shape[1]):
            if glyph[yy, xx] <= 0.45:
                continue
            px, py = xx + dx - BOX_X0, yy + dy - ROW0
            if 0 <= px < shape[1] and 0 <= py < shape[0]:
                out[py, px] = True
    return out


def _iou(a, b):
    u = (a | b).sum()
    return float((a & b).sum()) / float(u) if u else 0.0


def wrong_still_there(a):
    cur = _ink_mask(a[ROW0:ROW1, BOX_X0:BOX_X1])
    if cur.sum() < 30:
        return False
    wrong = _stamp(cur.shape, render(WRONG), INK_X0, INK_Y0)
    right = _stamp(cur.shape, render(RIGHT), INK_X0, INK_Y0)
    return _iou(cur, wrong) > _iou(cur, right)


def redraw(im):
    a = np.asarray(im.convert('RGB')).astype(np.float64)
    m_wrong, m_right = render(WRONG), render(RIGHT)
    wx, wy = inkbox(m_wrong)
    dx, dy = INK_X0 - wx, INK_Y0 - wy           # 让渲染的「刑」正好落在图里那个的位置上
    patch = a[ROW0:ROW1, BOX_X0:BOX_X1].copy()
    top = a[CLEAN_ABOVE[0]:CLEAN_ABOVE[1], BOX_X0:BOX_X1].mean(axis=0)
    bot = a[CLEAN_BELOW[0]:CLEAN_BELOW[1], BOX_X0:BOX_X1].mean(axis=0)
    y_end = float(CLEAN_BELOW[0] - 1)
    y_beg = float(CLEAN_ABOVE[1] - 1)
    for i, y in enumerate(range(ROW0, ROW1)):
        t = (y - y_beg) / (y_end - y_beg)
        patch[i] = top * (1.0 - t) + bot * t
    for yy in range(m_right.shape[0]):
        for xx in range(m_right.shape[1]):
            al = m_right[yy, xx]
            if al <= 0:
                continue
            px, py = xx + dx - BOX_X0, yy + dy - ROW0
            if not (0 <= px < BOX_X1 - BOX_X0 and 0 <= py < ROW1 - ROW0):
                continue
            patch[py, px] = patch[py, px] * (1.0 - al) + INK * al
    out = a.copy()
    out[ROW0:ROW1, BOX_X0:BOX_X1] = patch
    return Image.fromarray(np.clip(out + 0.5, 0, 255).astype(np.uint8), 'RGB')


if __name__ == '__main__':
    for p in TARGETS:
        if not os.path.exists(p):
            print('跳过（没这个文件）：%s' % p)
            continue
        im = Image.open(p)
        if not wrong_still_there(np.asarray(im.convert('RGB')).astype(np.float64)):
            print('已经是「邢」了，不用改：%s' % p)
            continue
        redraw(im).save(p, 'WEBP', lossless=True, method=0) if p.endswith('.webp') else redraw(im).save(p)
        print('改好了：%s' % p)
