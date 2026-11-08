# -*- coding: utf-8 -*-
"""项④阈值标定 v3:complete_row_lines(apply=False) 对 30 张全 sub 走查量测。

正样本 = 疑漏带判读_20261005.csv 判"真漏线A"带内的 sub
        + 四例裁片/几何实锤的 triage 漏报(1020 y17286 / 1042 y8214 / 1033 y9632 /
          1037 y10943:轨迹锚出巨带内真边界,I2 门禁对 jumble 字符串静默漏报,
          见 runs/tmp/项④反例_20261005/)。
负样本 = 其余全部 sub。验收尺 = 数值区[x_w,bx)的 run_num + frac_n。
"""
import csv
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from src.core import paths
from src.table import track_rows

EXTRA_POS = {("1020", 17286.0), ("1042", 8214.0),
             ("1033", 9632.0), ("1037", 10943.0),
             ("1017", 3143.0), ("1017", 3249.5),
             ("1031", 15310.0)}   # 裁片/几何实锤的 triage 漏报

stems = sorted(p.stem for p in paths.CANDIDATE_COORD_DIR.glob("*.json"))
pos = {}
with open(paths.RUNS_DIR / "tmp" / "疑漏带判读_20261005.csv", encoding="utf-8-sig") as f:
    for r in csv.DictReader(f):
        if "真漏线A" in r["判读(助手弱档)"]:
            pos.setdefault(r["图号"], []).append((float(r["带y0"]), float(r["带y1"])))
n_pos_band = sum(len(v) for v in pos.values())
print(f"正样本带: {n_pos_band} 条 / {len(pos)} 图 (+裁片实锤漏报 {len(EXTRA_POS)})")

rows_out = []
for stem in stems:
    num = stem.replace("钻孔柱状图", "")
    fp = paths.RUNS_DIR / "table_reconstruct" / f"{stem}_行判定.json"
    if not fp.exists():
        continue
    out = json.load(open(fp, encoding="utf-8"))
    if not out.get("sub_rows"):
        continue
    track_rows.complete_row_lines(stem, out, apply=False)
    bands = pos.get(num, [])
    for s in out.get("complete_stats", []):
        y = s["y"]
        if any(a - 5 <= y <= b + 5 for a, b in bands) or (num, y) in EXTRA_POS:
            lab = "P"
        else:
            lab = "N"
        rows_out.append((num, lab, y, s.get("frac_n", -1), s.get("run_num", -1),
                         s.get("walked_num", -1), s.get("n_num", -1), s.get("why")))

with open(paths.RUNS_DIR / "tmp" / "补全标定_20261005.csv", "w", newline="",
          encoding="utf-8-sig") as f:
    w = csv.writer(f)
    w.writerow(["图号", "正负", "sub_y", "frac_n", "run_num", "walked_num", "num锚", "why"])
    w.writerows(rows_out)

P = [r for r in rows_out if r[1] == "P"]
N = [r for r in rows_out if r[1] == "N"]
print(f"P={len(P)}  N={len(N)}")
for name, G in (("正(P)", P), ("负(N)", N)):
    fr = [r[3] for r in G if r[3] >= 0]
    rw = [r[4] for r in G if r[4] >= 0]
    if fr:
        print(f"{name}: n={len(G)}")
        print(f"  frac_n  p0/p10/p25/p50/p75/p90/p100 = "
              f"{np.percentile(fr, [0, 10, 25, 50, 75, 90, 100]).round(3)}")
        print(f"  run_num 分位 = {np.percentile(rw, [0, 10, 25, 50, 75, 90, 100]).round(1)}")
        miss = [r for r in G if r[3] < 0]
        if miss:
            from collections import Counter
            print(f"  未走到走查就被拒 {len(miss)} 条: "
                  f"{Counter(r[7] for r in miss).most_common()}")
print("--- 分界试算(run_num & frac_n 双门) ---")
for cw in (40, 50, 60):
    for cf in (0.1, 0.15, 0.2, 0.3):
        tp = sum(1 for r in P if r[4] >= cw and r[3] >= cf)
        fp_ = sum(1 for r in N if r[4] >= cw and r[3] >= cf)
        print(f"run_num>={cw} & frac_n>={cf}: 正 {tp}/{len(P)}  负过门 {fp_}/{len(N)}")
