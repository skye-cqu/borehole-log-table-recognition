# -*- coding: utf-8 -*-
"""项④核验包:对每张图新补全的行(complete_from_sub=True)渲染 1:1 裁片。

红=上下邻行界(既有) 蓝=补全行折线 绿=墨锚点 黄=Hermite桥段 橙=原sub折线(审计线)。
裁片窗 x=[tab_l−40, table_x[1]], y=补全行±80;2×放大。输出 runs/tmp/项④核验包_20261005/。
"""
import csv
import json
import sys
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from src.core import paths
from src.table.track_rows import _chord_in_band

OUT = paths.RUNS_DIR / "tmp" / "项④核验包_20261005"
OUT.mkdir(parents=True, exist_ok=True)

stems = sorted(p.stem for p in paths.CANDIDATE_COORD_DIR.glob("*.json"))
index = []
for stem in stems:
    fp = paths.RUNS_DIR / "table_reconstruct" / f"{stem}_行判定.json"
    out = json.load(open(fp, encoding="utf-8"))
    comp = [r for r in out["rows"] if r.get("complete_from_sub")]
    if not comp:
        continue
    gray = cv2.imread(str(paths.RAW_DIR / f"{stem}.JPG"), cv2.IMREAD_GRAYSCALE)
    W, E, _ = __import__("src.table.track_rows", fromlist=["content_band"]).content_band(stem)
    tab_l, tab_r = out["table_x"]
    ys_all = np.asarray([r["y_at_mid"] for r in out["rows"]], float)
    num = stem.replace("钻孔柱状图", "")
    for r in comp:
        y_mid = r["y_at_mid"]
        i = int(np.searchsorted(ys_all, y_mid))
        top = out["rows"][max(0, i - 2)]["poly"]
        bot = out["rows"][min(len(out["rows"]) - 1, i + 1)]["poly"]
        y0, y1 = int(y_mid) - 80, int(y_mid) + 80
        x0, x1 = max(0, tab_l - 40), min(gray.shape[1], tab_r + 10)
        viz = cv2.cvtColor(gray[y0:y1, x0:x1], cv2.COLOR_GRAY2BGR)
        for poly, color, th in ((top, (0, 0, 255), 2), (bot, (0, 0, 255), 2),
                                (r["poly"], (255, 0, 0), 2)):
            pts = np.asarray(poly, float)
            for a, b in zip(pts[:-1], pts[1:]):
                cv2.line(viz, (int(a[0]) - x0, int(a[1]) - y0),
                         (int(b[0]) - x0, int(b[1]) - y0), color, th, cv2.LINE_AA)
        for seg in r.get("complete_bridge_segs", []):     # 桥段黄罩
            cv2.rectangle(viz, (seg[0] - x0, 0), (seg[1] - x0, y1 - y0 - 1), (0, 255, 255), 1)
        # 原 sub(审计):按 segment_ids 找回
        for s in out["sub_rows"]:
            if s["segment_ids"] == r["segment_ids"] and abs(s["y_at_mid"] - y_mid) < 5:
                pts = np.asarray(s["poly"], float)
                for a, b in zip(pts[:-1], pts[1:]):
                    cv2.line(viz, (int(a[0]) - x0, int(a[1]) - y0),
                             (int(b[0]) - x0, int(b[1]) - y0), (0, 165, 255), 1, cv2.LINE_AA)
                break
        viz = cv2.resize(viz, (viz.shape[1] * 2, viz.shape[0] * 2),
                         interpolation=cv2.INTER_NEAREST)
        name = f"{num}_y{int(y_mid)}.png"
        cv2.imwrite(str(OUT / name), viz)
        index.append([num, int(y_mid), r["span"], r["complete_anchor"],
                      r["complete_walked_num"], r["cov_num"],
                      r.get("complete_bridge_px", 0), name])

with open(OUT / "索引.csv", "w", newline="", encoding="utf-8-sig") as f:
    w = csv.writer(f)
    w.writerow(["图号", "补全行y", "跨度", "数值区锚px", "数值区走查px", "cov_num", "桥px", "文件"])
    w.writerows(index)
print(f"核验包 {len(index)} 张 → {OUT}")
