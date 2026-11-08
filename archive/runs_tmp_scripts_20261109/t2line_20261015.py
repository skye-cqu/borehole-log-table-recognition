# -*- coding: utf-8 -*-
"""1042:精测 真厚|柱状 之间那条竖线(表头截图里肉眼可见,但 sep_x_band 没有)。"""
import sys
import numpy as np, cv2
from pathlib import Path
R = Path(r"D:\Skye\Documents\Work\高维智矿\7.13杂活")
sys.path.insert(0, str(R))
from src.core import paths

g = cv2.imread(str(paths.RAW_DIR / "钻孔柱状图1042.JPG"), cv2.IMREAD_GRAYSCALE)
ink = (g < 128).astype(np.uint8)

print("== 表头带 y=[747,911] 内 x=[600,960] 的每列墨量(满格=164) ==")
hb = ink[747:911, 600:960]
cs = hb.sum(axis=0)
for i, v in enumerate(cs):
    if v >= 100:
        print("   x=%d 墨=%d (%.0f%% 带高)" % (600+i, v, 100.0*v/164))

print()
print("== 沿 y 追踪 x=[690,760] 区间内的竖线(逐 200px 窗口取墨峰) ==")
for y in range(760, 19900, 600):
    win = ink[y-3:y+4, 660:800]
    c = win.sum(axis=0)
    c = np.convolve(c, np.ones(3)/3.0, mode="same")
    best = int(np.argmax(c))
    # 找所有 >=4 的峰
    pk = [(660+i, int(c[i])) for i in range(2, len(c)-2)
          if c[i] >= 4 and c[i] == c[max(0,i-4):i+5].max()]
    print("   y=%-6d 峰=%s" % (y, " ".join("%d(%d)" % p for p in pk)))
