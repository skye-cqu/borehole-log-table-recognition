# -*- coding: utf-8 -*-
"""裁 1023 与 1015 表头带 1:1 原图,并标注列界,供肉眼核验。"""
import json, sys
import numpy as np, cv2
from pathlib import Path
R = Path(r"D:\Skye\Documents\Work\高维智矿\7.13杂活")
sys.path.insert(0, str(R))
from src.core import paths
RECON = paths.RUNS_DIR / "table_reconstruct"
OUT = R / "runs/tmp"

def crop(stem, tag, pad_up=40, pad_dn=40, x_lo=None, x_hi=None):
    w = json.loads((RECON/f"{stem}_表头映射.json").read_text(encoding="utf-8"))
    b0, b1 = w["band"]
    g = cv2.imread(str(paths.RAW_DIR/f"{stem}.JPG"), cv2.IMREAD_GRAYSCALE)
    H, W = g.shape
    x0 = x_lo if x_lo is not None else int(min(c["x_in_band"][0] for c in w["columns"])) - 30
    x1 = x_hi if x_hi is not None else int(max(c["x_in_band"][1] for c in w["columns"])) + 30
    y0 = max(0, b0 - pad_up); y1 = min(H, b1 + pad_dn)
    img = cv2.cvtColor(g[y0:y1, x0:x1], cv2.COLOR_GRAY2BGR)
    # 画列界(红)与列名
    for c in w["columns"]:
        for xb in (c["x_in_band"][0], c["x_in_band"][1]):
            xi = int(round(xb)) - x0
            if 0 <= xi < img.shape[1]:
                cv2.line(img, (xi, 0), (xi, img.shape[0]-1), (0,0,255), 1)
        xm = int(round((c["x_in_band"][0]+c["x_in_band"][1])/2)) - x0
        if 0 <= xm < img.shape[1]:
            cv2.putText(img, c["name"], (max(0,xm-24), 18), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255,0,0), 1)
    # 放大 2 倍便于看清
    img2 = cv2.resize(img, (img.shape[1]*2, img.shape[0]*2), interpolation=cv2.INTER_NEAREST)
    p = OUT / f"hdr_{tag}_20261018.png"
    cv2.imwrite(str(p), img2)
    print("%s band=[%d,%d] 裁 x=[%d,%d] y=[%d,%d] -> %dx%d  %s" % (
        tag, b0, b1, x0, x1, y0, y1, img2.shape[1], img2.shape[0], p.name))
    return w

w23 = crop("钻孔柱状图1023", "1023")
w15 = crop("钻孔柱状图1015", "1015")
# 只裁 深度/层厚 两格的局部特写
def zoom2(stem, tag):
    w = json.loads((RECON/f"{stem}_表头映射.json").read_text(encoding="utf-8"))
    b0, b1 = w["band"]
    g = cv2.imread(str(paths.RAW_DIR/f"{stem}.JPG"), cv2.IMREAD_GRAYSCALE)
    cols = w["columns"]
    # 第3、4格 = 索引2、3
    x0 = int(cols[2]["x_in_band"][0]) - 10
    x1 = int(cols[3]["x_in_band"][1]) + 10
    y0, y1 = max(0, b0-15), min(g.shape[0], b1+15)
    img = cv2.cvtColor(g[y0:y1, x0:x1], cv2.COLOR_GRAY2BGR)
    for k, c in ((2,(0,0,255)),(3,(255,0,0))):
        xi = int(round(cols[k]["x_in_band"][0])) - x0
        if 0 <= xi < img.shape[1]:
            cv2.line(img, (xi, 0), (xi, img.shape[0]-1), (0,180,0), 1)
    img = cv2.resize(img, (img.shape[1]*4, img.shape[0]*4), interpolation=cv2.INTER_NEAREST)
    p = OUT / f"hdr_{tag}_34_20261018.png"
    cv2.imwrite(str(p), img)
    print("  %s 第3/4格特写 x=[%d,%d] -> %dx%d  %s" % (tag, x0, x1, img.shape[1], img.shape[0], p.name))

zoom2("钻孔柱状图1023", "1023")
zoom2("钻孔柱状图1015", "1015")
