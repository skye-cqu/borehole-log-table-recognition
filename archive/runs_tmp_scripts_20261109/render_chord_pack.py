# -*- coding: utf-8 -*-
"""项③ 视觉门禁包:每图取弦修复(桥长)最大的 2 行,修复前后 1:1 对比裁片。

上=修复前折线(蓝,=v9 备份), 下=修复后(红=墨迹锚定/贴墨段, 黄=曲率桥 chord_bridge_segs)。
输出 runs/tmp/项③弦包_20261005/{stem}_y{y}_弦对比.png(每图至多 2 张)。
判读口径:助手渲染供用户核验;黄桥=原图无墨段(段间桥接),红段=锚在原图墨上。
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

OUT = paths.RUNS_DIR / "tmp" / "项③弦包_20261005"
BAK = paths.PROJECT_ROOT / "rollback" / "era_ext_行判定_备份_20261001"
PER_CHART = 2
PADX, PADY = 130, 130


def render(stem, rows_pair):
    rn, ro = rows_pair
    segs = rn.get("chord_bridge_segs") or []
    p = np.asarray(rn["poly"], float)
    if segs:
        bx0, bx1 = min(s[0] for s in segs), max(s[1] for s in segs)
    else:
        k = int(np.argmax(np.diff(p[:, 0])))
        bx0, bx1 = int(p[k, 0]), int(p[k + 1, 0])
    gray = cv2.imread(str(paths.RAW_DIR / f"{stem}.JPG"), cv2.IMREAD_GRAYSCALE)
    H, Wd = gray.shape
    x0, x1 = max(bx0 - PADX, 0), min(bx1 + PADX, Wd)
    ya = min(p[:, 1].min(), np.asarray(ro["poly"], float)[:, 1].min())
    yb = max(p[:, 1].max(), np.asarray(ro["poly"], float)[:, 1].max())
    y0, y1 = max(int(ya) - PADY, 0), min(int(yb) + PADY, H)

    def panel(poly_pts, bridges, color):
        viz = cv2.cvtColor(gray[y0:y1, x0:x1], cv2.COLOR_GRAY2BGR)
        tr._draw_poly(viz, [[px - x0, py - y0] for px, py in poly_pts], color, 2)
        for a, b in bridges or []:
            idx = [k for k, pt in enumerate(poly_pts) if a <= pt[0] <= b]
            if idx:
                lo, hi = max(0, min(idx) - 1), min(len(poly_pts) - 1, max(idx) + 1)
                tr._draw_poly(viz, [[px - x0, py - y0] for px, py in poly_pts[lo:hi + 1]],
                              (0, 255, 255), 2)
        return viz

    top = cv2.putText(panel(ro["poly"], None, (255, 80, 0)),
                      f"{stem} y={rn['y_at_mid']} BEFORE", (8, 24),
                      cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 2)
    bot = cv2.putText(panel(rn["poly"], segs, (0, 0, 255)),
                      "AFTER  red=ink-anchored  yellow=curvature-bridge", (8, 24),
                      cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 120, 0), 2)
    w = max(top.shape[1], bot.shape[1])
    pad = lambda c: c if c.shape[1] == w else np.pad(
        c, ((0, 0), (0, w - c.shape[1]), (0, 0)), constant_values=255)
    m = np.vstack([pad(top), np.full((6, w, 3), 60, np.uint8), pad(bot)])
    fp = OUT / f"{stem}_y{int(rn['y_at_mid'])}_弦对比.png"
    cv2.imwrite(str(fp), m)
    return fp


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    n = 0
    for f in sorted(BAK.glob("钻孔柱状图*_行判定.json")):
        stem = f.name[:-9]
        new = json.loads((paths.RUNS_DIR / "table_reconstruct" / f"{stem}_行判定.json")
                         .read_text(encoding="utf-8"))
        old = json.loads(f.read_text(encoding="utf-8"))
        cand = [(r.get("chord_bridge_px") or 0, i) for i, r in enumerate(new["rows"])]
        cand.sort(reverse=True)
        picked = [i for bpx, i in cand[:PER_CHART] if bpx > 0]
        if not picked:
            print(f"{stem} 无桥接行,跳过")
            continue
        for i in picked:
            fp = render(stem, (new["rows"][i], old["rows"][i]))
            n += 1
        print(f"{stem} -> {len(picked)} 张 (桥长 top: {[new['rows'][i].get('chord_bridge_px') for i in picked]})")
    print(f"\n共 {n} 张 -> {OUT}")
    print("判读: 上蓝=修复前(v9), 下红/黄=修复后; 黄桥=原图无墨(段间桥接),应平顺过渡不切角不跳行。")
