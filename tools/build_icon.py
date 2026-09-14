# -*- coding: utf-8 -*-
"""把仓库根目录的 图标.jpg 做成游戏的图标。

源图只有 72x72，而 Windows 图标要一路做到 256x256，只能放大。
放大用 Lanczos，再补一点锐化 —— 不补的话放大后边缘发糊。

产物两个：
  game/icon.png   256x256 的 PNG，运行时的窗口 / 任务栏图标
                  （project.godot 里的 application/config/icon）
  game/icon.ico   16/24/32/48/64/128/256 七档，导出 exe 时嵌进 exe
                  （export_presets.cfg 里的 application/icon）

用法：python -X utf8 tools/build_icon.py
"""
import os
import sys

from PIL import Image, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SRC = os.path.join(ROOT, "图标.jpg")
GAME = os.path.join(ROOT, "game")
SIZES = [16, 24, 32, 48, 64, 128, 256]
TOP = 256


def main():
	if not os.path.exists(SRC):
		raise SystemExit("找不到源图：%s" % SRC)
	im = Image.open(SRC).convert("RGB")
	print("源图 %s  %dx%d" % (os.path.basename(SRC), im.width, im.height))

	big = im.resize((TOP, TOP), Image.LANCZOS)
	# 锐化只补一点点：补多了会在头发和衣服边上出现白边
	big = big.filter(ImageFilter.UnsharpMask(radius=1.6, percent=60, threshold=3))

	png = os.path.join(GAME, "icon.png")
	big.save(png)
	print("写出 %s  %dx%d" % (png, big.width, big.height))

	ico = os.path.join(GAME, "icon.ico")
	big.save(ico, format="ICO", sizes=[(s, s) for s in SIZES])
	chk = Image.open(ico)
	print("写出 %s  里面这几档：%s" % (ico, sorted(chk.ico.sizes())))
	return 0


if __name__ == "__main__":
	sys.exit(main())

