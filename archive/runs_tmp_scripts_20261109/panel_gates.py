# -*- coding: utf-8 -*-
"""门禁效果对比片：挑"台阶最大"的几条旧线，把 原图 / 门禁前画的线 / 门禁后画的线 并排。

门禁前快照 = rollback/行判定_门禁前_20260924（折线表征已上、三道门禁未上）。
每行 3 格同一窗口：① 只有原图；② 叠旧层界(红)；③ 叠新线(红=层界 橙=子行线 蓝=门禁2剔掉的链)。
红线走的地方图上有没有横线墨、绿线是不是贴着墨走，一眼能对得上。

用法: python runs/tmp/panel_gates.py [1027 1040 ...]
产物: runs/tmp/门禁对比_<code>.png
"""
import json
import os
import sys
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from src.core import paths                                          # noqa: E402
from src.table.track_rows import row_y, step_of                     # noqa: E402

OLD = Path(os.environ.get("SRC", ROOT / "rollback" / "行判定_门禁前_20260924"))
NEW = paths.RUNS_DIR / "table_reconstruct"
WX, WY = 700, 240          # 窗口半宽/半高(px)
N_BEST = 4


def load(d, stem):
    return json.loads((d / f"{stem}_行判定.json").read_text(encoding="utf-8"))


def draw(gray, lines, off):
    """窗口灰度图 + [(颜色BGR, 线宽, 全图坐标点列)] → 彩图（点列平移到窗口坐标）。"""
    v = cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)
    for color, w, poly in lines:
        pts = np.asarray(poly, float)
        if not len(pts) or pts.shape[1] < 2:
            continue
        pts = np.rint(pts[:, :2] - np.array(off)).astype(np.int32).reshape(-1, 1, 2)
        cv2.polylines(v, [pts], False, color, w, cv2.LINE_AA)
    return v


def tag(img, txt):
    cv2.rectangle(img, (0, 0), (28 + 21 * len(txt), 36), (255, 255, 255), -1)
    cv2.putText(img, txt, (10, 26), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 0), 2)
    return img


def in_win(rd, key, pts_key, lo, hi):
    """落在窗口竖向范围内的线 → draw() 要的 (颜色, 线宽, 点列)。"""
    col = {"rows": ((0, 0, 255), 3), "sub_rows": ((0, 140, 255), 2),
           "rejected": ((255, 0, 0), 2)}[key]
    return [(*col, r[pts_key]) for r in rd.get(key, [])
            if lo <= (r["y_at_mid"] if pts_key == "poly" else r["y"]) <= hi]


def main(codes):
    for code in codes:
        stem = f"钻孔柱状图{code}"
        gray = cv2.imread(str(paths.RAW_DIR / f"{stem}.JPG"), cv2.IMREAD_GRAYSCALE)
        old, new = load(OLD, stem), load(NEW, stem)
        worst = sorted(old["rows"], key=lambda r: -step_of(np.asarray(r["poly"], float)))
        panels = []
        for r in worst[:N_BEST]:
            st = step_of(np.asarray(r["poly"], float))
            if st < 30:
                break
            cx = (r["x"][0] + r["x"][1]) / 2
            cy = row_y(r, cx)
            x0, x1 = int(max(0, cx - WX)), int(min(gray.shape[1], cx + WX))
            y0, y1 = int(max(0, cy - WY)), int(min(gray.shape[0], cy + WY))
            g = gray[y0:y1, x0:x1]
            lo, hi = y0 - 40, y1 + 40
            nl = (in_win(new, "rows", "poly", lo, hi) +
                  in_win(new, "sub_rows", "poly", lo, hi) +
                  in_win(new, "rejected", "pts", lo, hi))
            panels.append(np.hstack([
                tag(draw(g, [], (x0, y0)), "RAW"),
                tag(draw(g, [((0, 0, 255), 3, r["poly"])], (x0, y0)),
                    f"OLD y={r['y_at_mid']:.0f} step={st:.0f}px"),
                tag(draw(g, nl, (x0, y0)), f"NEW lines={len(nl)}")]))
        if not panels:
            print(f"{code}: 门禁前已无 >30px 台阶的线，不出片")
            continue
        h = max(p.shape[0] for p in panels)
        w = max(p.shape[1] for p in panels)
        out = np.vstack([cv2.copyMakeBorder(p, 0, h - p.shape[0], 0, w - p.shape[1],
                                           cv2.BORDER_CONSTANT, value=(255, 255, 255))
                         for p in panels])
        p = ROOT / "runs" / "tmp" / f"门禁对比_{code}.png"
        cv2.imwrite(str(p), out, [cv2.IMWRITE_PNG_COMPRESSION, 3])
        print(f"{code}: {len(panels)} 组窗口 每窗 {panels[0].shape[1]}x{panels[0].shape[0]} -> {p}")


if __name__ == "__main__":
    main([a for a in sys.argv[1:] if a.isdigit()] or ["1027", "1040"])
