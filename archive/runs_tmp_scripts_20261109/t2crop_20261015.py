# -*- coding: utf-8 -*-
import json, sys
import numpy as np, cv2
from pathlib import Path
R = Path(r"D:\Skye\Documents\Work\高维智矿\7.13杂活")
sys.path.insert(0, str(R))
from src.core import paths
from openpyxl import load_workbook

g = cv2.imread(str(paths.RAW_DIR / "钻孔柱状图1042.JPG"), cv2.IMREAD_GRAYSCALE)
H, W = g.shape
print("image", W, H)
hm = json.loads((R / "runs/table_reconstruct/钻孔柱状图1042_表头映射.json").read_text(encoding="utf-8"))
sb = hm["sep_x_band"]
sps = {s["index"]: s for s in hm["sep_pts"] if s["index"] is not None}

def interp(idx, y):
    s = sps.get(idx)
    if not s: return None
    ys = np.array(s["ys"], float); xs = np.array(s["xs"], float)
    o = np.argsort(ys)
    return float(np.interp(y, ys[o], xs[o]))

print()
print("== sep_pts 折线在各 y 的插值 x ==")
for y in (1000, 1160, 5280, 10000, 14160, 19000):
    print("  y=%-6d " % y + "  ".join("idx%d=%.0f" % (i, interp(i, y)) for i in (5, 6, 7, 8)))

ink = (g < 128).astype(np.uint8)
print()
print("== 该 y 实测墨峰(x<1300) ==")
for y in (1160, 5280, 14160):
    band = ink[y - 4:y + 5, :]
    col = band.sum(axis=0).astype(float)
    cs = np.convolve(col, np.ones(5) / 5.0, mode="same")
    pk = [i for i in range(3, 1300) if cs[i] >= 4.5 and cs[i] == cs[max(0, i - 6):i + 7].max()]
    print("  y=%-6d %s" % (y, " ".join("%d(%.1f)" % (i, cs[i]) for i in pk[:30])))

def save(name, x0, x1, y0, y1, reds=None, greens=None, scale=1):
    x0 = max(0, x0); x1 = min(W, x1); y0 = max(0, y0); y1 = min(H, y1)
    c = cv2.cvtColor(g[y0:y1, x0:x1], cv2.COLOR_GRAY2BGR)
    for x in (reds or []):
        if x is not None and x0 <= x < x1:
            cv2.line(c, (int(x) - x0, 0), (int(x) - x0, c.shape[0] - 1), (0, 0, 255), 2)
    for x in (greens or []):
        if x is not None and x0 <= x < x1:
            cv2.line(c, (int(x) - x0, 0), (int(x) - x0, c.shape[0] - 1), (0, 200, 0), 2)
    if scale != 1:
        c = cv2.resize(c, None, fx=scale, fy=scale, interpolation=cv2.INTER_NEAREST)
    p = R / "runs/tmp" / name
    cv2.imwrite(str(p), c)
    print("saved", name, c.shape)

save("t2_hdr_zoom.png", 470, 1070, 730, 945, reds=[int(v) for v in sb], scale=2)
save("t2_up.png", 0, 1300, 1000, 1320, greens=[interp(i, 1160) for i in (1, 2, 3, 4, 5, 6, 7, 8)])
save("t2_lo.png", 0, 1300, 14000, 14320, greens=[interp(i, 14160) for i in (1, 2, 3, 4, 5, 6, 7, 8)])

print()
print("== 参考表 1042 表头 ==")
ref = R / "runs/参考表_1015-1044_20261011/1015-1044/钻孔柱状图1042_llm_corrected.xlsx"
ws = load_workbook(ref).active
hdr = [ws.cell(row=1, column=c).value for c in range(1, ws.max_column + 1)]
print("  列:", hdr)
for r in range(2, 8):
    print("  r%d:" % r, [ws.cell(row=r, column=c).value for c in range(1, ws.max_column + 1)])
