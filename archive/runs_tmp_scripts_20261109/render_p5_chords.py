# -*- coding: utf-8 -*-
"""P5 五条跨带弦的修复前后 1:1 对比裁片(项③视觉门禁)。

五行(09-30 P5 定性):1020 y=10074、1027 y=3142/y=11412、1037 y=22128、1043 y=3671。
每弦两面板竖排:上=修复前折线(蓝)压灰度原图,下=修复后(红=锚定/贴墨段,黄=曲率桥)。
输出 runs/tmp/项③弦裁片_20261002/{stem}_y{y}_弦对比.png。
"""
import sys
import warnings

warnings.filterwarnings("ignore")
sys.path.insert(0, ".")
import json
from pathlib import Path

import cv2
import numpy as np

from src.core import paths
from src.table import track_rows as tr

OUT = paths.RUNS_DIR / "tmp" / "项③弦裁片_20261002"
BAK = paths.PROJECT_ROOT / "rollback" / "era_ext_行判定_备份_20261001"
FIVE = [("钻孔柱状图1020", 10074), ("钻孔柱状图1027", 3142), ("钻孔柱状图1027", 11412),
        ("钻孔柱状图1037", 22128), ("钻孔柱状图1043", 3671)]
PADX, PADY = 130, 130


def find_row(rows, y_target):
    return min(rows, key=lambda r: abs(r["y_at_mid"] - y_target))


def render(stem, y_t):
    new = json.loads((paths.RUNS_DIR / "table_reconstruct" / f"{stem}_行判定.json")
                     .read_text(encoding="utf-8"))
    old = json.loads((BAK / f"{stem}_行判定.json").read_text(encoding="utf-8"))
    rn = find_row(new["rows"], y_t)
    ro = find_row(old["rows"], y_t)
    segs = rn.get("chord_bridge_segs") or []
    if segs:
        bx0, bx1 = min(s[0] for s in segs), max(s[1] for s in segs)
    else:
        p = np.asarray(rn["poly"], float)
        k = int(np.argmax(np.diff(p[:, 0])))
        bx0, bx1 = int(p[k, 0]), int(p[k + 1, 0])
    gray = cv2.imread(str(paths.RAW_DIR / f"{stem}.JPG"), cv2.IMREAD_GRAYSCALE)
    H, Wd = gray.shape
    x0 = max(bx0 - PADX, 0)
    x1 = min(bx1 + PADX, Wd)
    ya = min(np.asarray(rn["poly"], float)[:, 1].min(), np.asarray(ro["poly"], float)[:, 1].min())
    yb = max(np.asarray(rn["poly"], float)[:, 1].max(), np.asarray(ro["poly"], float)[:, 1].max())
    y0 = max(int(ya) - PADY, 0)
    y1 = min(int(yb) + PADY, H)

    def panel(poly_pts, bridges, color_main):
        viz = cv2.cvtColor(gray[y0:y1, x0:x1], cv2.COLOR_GRAY2BGR)
        tr._draw_poly(viz, [[px - x0, py - y0] for px, py in poly_pts], color_main, 2)
        for a, b in bridges or []:
            idx = [k for k, pt in enumerate(poly_pts) if a <= pt[0] <= b]
            if idx:
                lo, hi = max(0, min(idx) - 1), min(len(poly_pts) - 1, max(idx) + 1)
                tr._draw_poly(viz, [[px - x0, py - y0] for px, py in poly_pts[lo:hi + 1]],
                              (0, 255, 255), 2)
        return viz

    top = panel(ro["poly"], None, (255, 80, 0))
    bot = panel(rn["poly"], segs, (0, 0, 255))
    w = max(top.shape[1], bot.shape[1])
    tag = cv2.putText(top.copy(), f"{stem} y={rn['y_at_mid']}  BEFORE (chord {bx0}-{bx1})",
                      (8, 24), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 2)
    sep = np.full((6, w, 3), 60, np.uint8)
    m = np.vstack([c if c.shape[1] == w else np.pad(c, ((0, 0), (0, w - c.shape[1]), (0, 0)),
                                                   constant_values=255) for c in (top, sep, bot)])
    m = cv2.putText(m, f"{stem} y={rn['y_at_mid']}  AFTER (red=ink-anchored, yellow=curvature bridge)",
                    (8, 26), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 120, 0), 2)
    fp = OUT / f"{stem}_y{int(rn['y_at_mid'])}_弦对比.png"
    cv2.imwrite(str(fp), m)
    return fp, bx0, bx1


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    for stem, y in FIVE:
        fp, bx0, bx1 = render(stem, y)
        print(f"{stem} y={y} 弦区 [{bx0},{bx1}] -> {Path(fp).name}")
    print("\n判读: 上=修复前(蓝弦), 下=修复后(红=墨迹锚定, 黄=曲率桥); 台阶应变为连续过渡。")
