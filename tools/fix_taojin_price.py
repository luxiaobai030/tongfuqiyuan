# -*- coding: utf-8 -*-
"""把十八里铺淘宝说明里的「150文」改成「500文」。

那段说明是原版 SWF 烘进画面的（导出时就是一张图），改字只能改图。
好在同一段文字上面那行正好有「价值达15000文的珍品！」——同一个字库、同一个
字号、同一个颜色，所以直接从那行抠「5」「0」两个字贴过来，字形跟周围一模一样。

数字在这一段里是等宽的（每格 10 像素），所以不用认字，按格子搬就行：
    「150文」的 1、5 两格  ←  「15000文」的 5、0 两格
搬完就是「500文」（第三格本来就是 0，不动）。

自检：如果第一格里已经是 5 的样子（而不是 1），说明这图改过了，直接跳过。

用法：
    python -X utf8 tools/fix_taojin_price.py
"""
import os
import numpy as np
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
IMG = os.path.join(ROOT, "game", "assets", "bg", "b0577.webp")

## 数字是等宽的，一格 10 像素（格子左边是对着图量出来的）。
CELL = 10
DST_Y = (318, 344)          # 「要花150文，就有四分之一的机会淘到」这一行
DST_ONE = 262               # 「1」那一格；右边依次是「5」(272)、「0」(282)
SRC_Y = (252, 276)          # 「我们还加入了价值达15000文的珍品！」这一行
SRC_ONE = 402               # 「15000」里 1 那一格；5 在 412、0 在 422


def ink(arr):
    r = arr[..., 0].astype(int)
    g = arr[..., 1].astype(int)
    b = arr[..., 2].astype(int)
    lum = r * 0.299 + g * 0.587 + b * 0.114
    return (r - g > 15) & (r - b > 15) & (lum < 170)


def block(arr, x, y):
    return arr[y[0]:y[1] + 1, x:x + CELL].astype(np.float32)


def alpha_of(blk):
    """把一个字块拆成「笔画浓度 + 笔画颜色」，底子不算数。"""
    lum = blk @ np.array([0.299, 0.587, 0.114], dtype=np.float32)
    bg = np.percentile(lum, 90)
    dark = np.percentile(lum, 2)
    if bg - dark < 20:
        return np.zeros(lum.shape, np.float32), np.zeros(3, np.float32)
    a = np.clip((bg - lum) / (bg - dark), 0.0, 1.0)
    color = blk.reshape(-1, 3)[lum.reshape(-1).argmin()]
    return a, color


def ink_rows(arr, x, y):
    m = ink(arr)[y[0]:y[1] + 1, x:x + CELL]
    rows = np.where(m.any(axis=1))[0]
    return rows


def main():
    im = Image.open(IMG).convert("RGB")
    arr = np.array(im)
    mask = ink(arr)
    print("[淘金] 图：%s（%dx%d）" % (IMG, im.width, im.height))

    ## 已经改过没有：「1」就那么一竖，占不满一格；「5」横平竖直占得宽。
    ## 所以量一下字格里的笔画有多宽就认得出来（比数像素稳）。
    def ink_span(x, y):
        m = mask[y[0]:y[1] + 1, x:x + CELL]
        cols = np.where(m.any(axis=0))[0]
        return int(cols.max() - cols.min() + 1) if cols.size else 0

    w_dst = ink_span(DST_ONE, DST_Y)
    w_one = ink_span(SRC_ONE, SRC_Y)
    w_five = ink_span(SRC_ONE + CELL, SRC_Y)
    print("[淘金] 笔画宽度：目标第一格 %d，样本 1 是 %d，样本 5 是 %d" % (w_dst, w_one, w_five))
    if w_dst * 2 > w_one + w_five:
        print("[淘金] 这里已经是 5 了，不用改")
        return 0

    # 竖着对齐：按笔画的底边（基线）对，别按图块边缘
    dy_dst = ink_rows(arr, DST_ONE + 2 * CELL, DST_Y).max()      # 第三格那个 0 的底边
    dy_src = ink_rows(arr, SRC_ONE + 2 * CELL, SRC_Y).max()      # 取材行 0 的底边
    dy = int(dy_dst) - int(dy_src)
    print("[淘金] 基线差 %d 像素" % dy)

    # 擦掉 1、5 两格：用同一行右边的空底子填
    x0, x1 = DST_ONE - 1, DST_ONE + 2 * CELL
    y0, y1 = DST_Y[0] - 2, DST_Y[1] + 2
    ## 底色就从要擦的这块里取（绕开笔画），这样它带着原图的纹理和明暗，
    ## 不会在对话框上糊出一块死白。
    patch_mask = mask[y0:y1 + 1, x0:x1 + 1]
    blank = arr[y0:y1 + 1, x0:x1 + 1].reshape(-1, 3)[~patch_mask.reshape(-1)]
    bg = np.median(blank, axis=0)
    arr[y0:y1 + 1, x0:x1] = bg.astype(np.uint8)
    print("[淘金] 底色 %s，擦掉 x=%d..%d" % (np.round(bg, 1), x0, x1 - 1))

    # 贴字：5 进第一格，0 进第二格
    for src_x, dst_x in ((SRC_ONE + CELL, DST_ONE), (SRC_ONE + 2 * CELL, DST_ONE + CELL)):
        blk = arr[SRC_Y[0]:SRC_Y[1] + 1, src_x:src_x + CELL]
        a, color = alpha_of(blk)
        ty = DST_Y[0] + dy
        dst = arr[ty:ty + a.shape[0], dst_x:dst_x + CELL].astype(np.float32)
        arr[ty:ty + a.shape[0], dst_x:dst_x + CELL] = np.clip(
            dst * (1 - a[..., None]) + color[None, None, :] * a[..., None], 0, 255).astype(np.uint8)

    tmp = IMG + ".tmp"
    Image.fromarray(arr).save(tmp, "WEBP", quality=95, method=6)
    os.replace(tmp, IMG)
    print("[淘金] 改好了 → %s" % IMG)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
