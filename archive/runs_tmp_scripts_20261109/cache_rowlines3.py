# -*- coding: utf-8 -*-
"""缓存 v3:只存"原始事实",取界规则留到扫描时再定(规则改动不再重建链,秒级比三种取界)。

每条 y 簇存:链的原始 x 覆盖区间(只裁到表格左右缘)+ 锚定列线(岩性描述左界)的 (y,x) 点列。
锚点列线可能混入别的线的碎片(实测 1035: x 从 982 抖到 287),所以取界规则必须能各自处理:
  A 常数     —— 用定稿的 x_at_mid(视觉核验过的那张图上标的就是它)
  B 逐条插值 —— x_at(链, y)
  C 邻域中位 —— 锚线在 y±WIN 内的 x 中位数(抗碎片串线)
产物 runs/tmp/行链3_<code>.json
"""
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "runs/tmp"))
from src.core import paths                                        # noqa: E402
from src.table.track_columns import load_chain                    # noqa: E402
from src.table import track_rows                                  # noqa: E402
from probe_rows2 import chains                                    # noqa: E402

TOL = 25
SUB = 20                      # 锚线点列按 y 每 20px 抽稀,缓存不存全点


def anchor(stem):
    """列结构定稿 → 岩性描述左界列线: (x_at_mid, [(y,x)...])。锚点=相邻列线间距最大格的左界。"""
    cj = json.loads((paths.CANDIDATE_COORD_DIR / f"{stem}.json").read_text(encoding="utf-8"))
    seg = {s["id"]: s for s in cj["lines"] if s["direction"] == "vertical" and s["label"] == "high"}
    st = json.loads((paths.RUNS_DIR / "table_reconstruct" / f"{stem}_列结构定稿.json")
                    .read_text(encoding="utf-8"))
    cols = sorted(st["columns"], key=lambda c: c["x_at_mid"])
    xs = [c["x_at_mid"] for c in cols]
    w, k = max((b - a, i) for i, (a, b) in enumerate(zip(xs, xs[1:])))
    pick = cols[k]
    pts, _ = load_chain({"segment_ids": pick["segment_ids"]}, seg)   # (y, x) 已按 y 排序
    idx = list(range(0, len(pts), SUB))
    if idx[-1] != len(pts) - 1:
        idx.append(len(pts) - 1)
    return float(pick["x_at_mid"]), w, [[round(float(pts[i, 0]), 1), round(float(pts[i, 1]), 1)]
                                        for i in idx]


def collect(stem):
    groups, tab_l, tab_r, _ = chains(stem)
    ax, aw, apts = anchor(stem)
    items = sorted((track_rows.x_at_mid(g), max(g["y0"], tab_l), min(g["y1"], tab_r))
                   for g in groups)
    lines = []
    for y, a, b in items:
        if lines and y - lines[-1][1] <= TOL:
            lines[-1][2].append((a, b))
            lines[-1][1] = y
        else:
            lines.append([y, y, [(a, b)]])
    return {"tab_l": tab_l, "tab_r": tab_r, "anchor_x": ax, "anchor_w": aw,
            "anchor_pts": apts, "n_chains": len(groups),
            "lines": [[round(r[0], 1), r[2]] for r in lines]}


def main():
    codes = [a for a in sys.argv[1:] if a.isdigit()] or [str(n) for n in range(1015, 1045)]
    for code in codes:
        out = paths.RUNS_DIR / "tmp" / f"行链3_{code}.json"
        if out.exists():
            print(f"{code}: 已有缓存")
            continue
        d = collect(f"钻孔柱状图{code}")
        out.write_text(json.dumps(d, ensure_ascii=False), encoding="utf-8")
        print(f"{code}: 链 {d['n_chains']} → 线 {len(d['lines'])} 锚 {d['anchor_x']:.0f}"
              f"({d['anchor_w']:.0f}px) 锚点列 {len(d['anchor_pts'])}", flush=True)


if __name__ == "__main__":
    main()
