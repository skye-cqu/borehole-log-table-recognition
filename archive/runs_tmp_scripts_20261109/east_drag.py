# -*- coding: utf-8 -*-
"""要不要连"简易水文曲线"一起排除？先量，别照抄 6g。

门禁5 已把柱状带内的段删掉、数值区窗口收到带西缘。6g 当年同时删了柱状和简易水文曲线两列，
但 6c 的层界判据现在只在数值区里量覆盖率——水文曲线那一格在窗口以东很远，它的段进不了判据。
它只剩一条路能影响结果：线画出来之后东头被水纹拖离西头。下游按 row_y 在格子里取高度切单元格，
东头一拖就把岩性描述末段和水纹格子的行界切歪。

所以这把尺子量同一条层界两半的高度差：水文格西界以东 vs 以西，单位行高。
用法: python runs/tmp/east_drag.py [码 ...]     # 无参数 = 30 张
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from src.core import paths                                          # noqa: E402
from src.table import track_rows as tr                              # noqa: E402


def hydro_edge(stem):
    """6a 定稿 → 水文曲线西界（=岩性描述东界）折线 (y,x)；认不出返回 None。"""
    fp = paths.RUNS_DIR / "table_reconstruct" / f"{stem}_列结构定稿.json"
    if not fp.exists():
        return None
    cj = json.load(open(paths.CANDIDATE_COORD_DIR / f"{stem}.json", encoding="utf-8"))
    seg = {s["id"]: s for s in cj["lines"]
           if s["direction"] == "vertical" and s["label"] == "high"}
    cols = sorted(json.load(open(fp, encoding="utf-8"))["columns"], key=lambda c: c["x_at_mid"])
    xs = [c["x_at_mid"] for c in cols]
    _, k = max((b - a, i) for i, (a, b) in enumerate(zip(xs, xs[1:])))   # k..k+1 = 岩性描述
    if k + 1 >= len(cols):
        return None
    return tr.load_chain({"segment_ids": cols[k + 1]["segment_ids"]}, seg)[0]


def main(codes):
    print(f"{'图':<6}{'层界':>6}{'两半都有':>9}{'占比':>6}{'拖>0.35':>9}{'最大拖':>8}{'中位拖':>8}")
    tot = dict(n=0, reach=0, drag=0)
    worst = []
    for code in codes:
        stem = f"钻孔柱状图{code}"
        fp = paths.RUNS_DIR / "table_reconstruct" / f"{stem}_行判定.json"
        hx = hydro_edge(stem)
        if not fp.exists() or hx is None:
            print(f"{code:<6}  跳过（无行判定/无岩性东界）")
            continue
        d = json.load(open(fp, encoding="utf-8"))
        row_h = float(d["row_h"]) or 1.0
        ds, reach = [], 0
        for r in d["rows"]:
            p = np.asarray(r["poly"], float)                       # (x, y)
            xe = float(tr.x_at(hx, float(np.median(p[:, 1]))))     # 该高度处水文格西界
            e = p[:, 0] >= xe
            if e.sum() <= 3 or (~e).sum() <= 3:
                continue                                           # 只有一头，无从比高
            ds.append((float(np.median(p[e][:, 1])) - float(np.median(p[~e][:, 1]))) / row_h)
            reach += 1
        a = np.abs(np.array(ds))
        big = int((a > 0.35).sum())
        tot["n"] += len(d["rows"]); tot["reach"] += reach; tot["drag"] += big
        worst.append((code, float(a.max()) if a.size else 0.0))
        print(f"{code:<6}{len(d['rows']):>7}{reach:>9}{100 * reach / max(len(d['rows']), 1):>8.0f}%"
              f"{big:>10}{a.max() if a.size else 0:>9.2f}{np.median(a) if a.size else 0:>8.2f}")
    print(f"\n合计: 层界{tot['n']} 两半都可比{tot['reach']} 东头拖>0.35行高{tot['drag']}")
    print("最大拖的 5 张: " + "  ".join(f"{c}={m:.2f}" for c, m in sorted(worst, key=lambda t: -t[1])[:5]))


if __name__ == "__main__":
    codes = [a for a in sys.argv[1:] if a.isdigit()] or \
        sorted(p.stem[-4:] for p in paths.CANDIDATE_COORD_DIR.glob("*.json"))
    main(codes)
