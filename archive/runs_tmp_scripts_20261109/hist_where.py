# -*- coding: utf-8 -*-
"""离墨采样落在表的哪一段：按横向位置分 10 档统计超差率。

若超差集中在某一段（如柱状图列、表右缘外），那是"期望错了"——那段本来没有横线；
若是沿程均匀散布，才是线本身歪。
用法: python runs/tmp/hist_where.py
"""
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "runs" / "tmp"))
from src.core import paths                                          # noqa: E402
import yardstick as Y                                               # noqa: E402

K = 10
tot = np.zeros(K)
off = np.zeros(K)
for p in sorted(paths.CANDIDATE_COORD_DIR.glob("*.json")):
    rd = json.loads((paths.RUNS_DIR / "table_reconstruct" /
                     f"{p.stem}_行判定.json").read_text(encoding="utf-8"))
    ruling, _ = Y.masks(p.stem)
    W = ruling.shape[1]
    tl, tr = rd["table_x"]
    bnd = float(np.median([r["boundary_x"] for r in rd["rows"]]))
    for r in rd["rows"]:
        x0, x1 = int(r["x"][0]), int(r["x"][1])
        for x in np.linspace(x0 + 10, min(x1 - 10, W - 2), Y.SAMPLE):
            y = Y.line_y(r, x)
            k = min(int((x - tl) / max(tr - tl, 1) * K), K - 1)
            k = max(k, 0)
            band = ruling[max(0, int(y) - Y.SEARCH):int(y) + Y.SEARCH, int(x)]
            idx = np.flatnonzero(band)
            tot[k] += 1
            if not len(idx) or np.abs(idx + max(0, int(y) - Y.SEARCH) - y).min() > 5:
                off[k] += 1
print(f"表宽 {tl:.0f}→{tr:.0f}，数值区右界(中位) {bnd:.0f}"
      f"；按横向 10 等分统计离墨采样率")
for k in range(K):
    x = tl + (tr - tl) * (k + 0.5) / K
    zone = "数值区" if x < bnd else "描述区"
    print(f"  第{k + 1}档 x≈{x:5.0f} ({zone}): 离墨 {off[k] / max(tot[k], 1) * 100:5.1f}%"
          f"  样本 {int(tot[k])}")
