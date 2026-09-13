# -*- coding: utf-8 -*-
import sys
from PIL import Image
im = Image.open(sys.argv[1]).convert("RGB")
W, H = im.size
print("图像尺寸: %dx%d" % (W, H))
CW, CH = 100, 46
sm = im.resize((CW, CH))
px = list(sm.getdata())

# 统计全局主色
from collections import Counter
full = Counter(im.resize((200,160)).getdata())
print("\n主色 TOP10:")
for c, n in full.most_common(10):
    print("   #%02x%02x%02x  RGB%-16s %d" % (c[0],c[1],c[2], str(c), n))

# 把每个格子映射成字符：按亮度和色相
CHARS = " .:-=+*#%@"
def char_of(r,g,b):
    lum = (0.299*r + 0.587*g + 0.114*b) / 255.0
    # 蓝色系单独标记
    if b > r + 30 and b > 60:
        return "b" if lum < 0.45 else "B"
    if r > 200 and g > 200 and b > 200: return "W"
    if r > g + 30 and r > b + 30: return "r"
    if g > r + 25 and g > b + 25: return "g"
    if lum > 0.85: return "@"
    return CHARS[min(9, int(lum*10))]

print("\n字符画 (%dx%d 格，蓝=b 深/b 浅/B，白=W，红=r，绿=g):" % (CW, CH))
print("+" + "-"*CW + "+")
for y in range(CH):
    row = "".join(char_of(*px[y*CW+x]) for x in range(CW))
    print("|" + row + "|")
print("+" + "-"*CW + "+")
