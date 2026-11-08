# -*- coding: utf-8 -*-
"""缓存 v2:数值/描述分界不再取自 6b 表头映射,而是阶段5 列判定的分隔线,且逐条线插值。

改动理由(实测):
  - 6b 与列判定给的数值区右界在 22/30 张上差 >25px(最大 73px),正好落在判据临界带;
  - 表是弯的,分隔线 x 随 y 变,全局常数右界是近似 → 改为每条横线在自己的 y 上插值右界。
锚点:相邻分隔线间距最大的一格 = 岩性描述(宽 ~1300px);其左界即数值区右界。
  最宽间距 <400px(如 1020 描述列长线漏检)→ 回退取最右分隔线。
产物 runs/tmp/行链2_<code>.json: {tab_l, tab_r, lines:[[y, 右界xb, 数值区间[], 描述区间[]]]}
"""
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "runs/tmp"))
from src.core import paths                                        # noqa: E402
from src.table.track_columns import load_chain, x_at                # noqa: E402
from src.table import track_rows                                  # noqa: E402
from probe_rows2 import chains                                    # noqa: E402

TOL = 25
ANCHOR_MIN = 400.0


def desc_boundary_chain(stem):
    """列结构定稿(6a,编号已视觉核验)→ 岩性描述左界那条列线的 (y,x) 折线。

    锚点 = 定稿列线相邻间距最大的一格(岩性描述,实测 1300~1500px,独一无二);
    其左界列线即数值区右界。5 张有列名的(1018/1042 等)实测与该锚点一致。
    """
    cj = json.loads((paths.CANDIDATE_COORD_DIR / f"{stem}.json").read_text(encoding="utf-8"))
    seg = {s["id"]: s for s in cj["lines"] if s["direction"] == "vertical" and s["label"] == "high"}
    st = json.loads((paths.RUNS_DIR / "table_reconstruct" / f"{stem}_列结构定稿.json")
                    .read_text(encoding="utf-8"))
    cols = sorted(st["columns"], key=lambda c: c["x_at_mid"])
    w, k = max((b - a, i) for i, (a, b) in
               enumerate(zip([c["x_at_mid"] for c in cols],
                             [c["x_at_mid"] for c in cols[1:]])))
    pick = cols[k]
    pts, _ = load_chain({"segment_ids": pick["segment_ids"]}, seg)
    return pts, float(pick["x_at_mid"]), w


def collect(stem):
    groups, tab_l, tab_r, _ = chains(stem)
    bpts, bx, w = desc_boundary_chain(stem)
    items = []
    for g in groups:
        y = track_rows.x_at_mid(g)
        xb = float(np.clip(x_at(bpts, y), tab_l + 60, tab_r - 60))
        items.append((y, max(g["y0"], tab_l), min(g["y1"], xb),
                      max(g["y0"], xb), min(g["y1"], tab_r), xb))
    items.sort()
    lines = []
    for y, nl, nr, dl, dr, xb in items:
        if nl >= nr and dl >= dr:
            continue
        if lines and y - lines[-1][3] <= TOL:
            last = lines[-1]
            last[1] += [(nl, nr)]
            last[2] += [(dl, dr)]
            last[3] = y
            last[4] = max(last[4], xb)
        else:
            lines.append([y, [(nl, nr)], [(dl, dr)], y, xb])
    return {"tab_l": tab_l, "tab_r": tab_r, "anchor_x": bx, "anchor_w": w,
            "n_chains": len(groups),
            "lines": [[round(r[0], 1), round(r[4], 1), r[1], r[2]] for r in lines]}


def main():
    codes = [a for a in sys.argv[1:] if a.isdigit()] or [str(n) for n in range(1015, 1045)]
    for code in codes:
        out = paths.RUNS_DIR / "tmp" / f"行链2_{code}.json"
        if out.exists():
            print(f"{code}: 已有缓存")
            continue
        stem = f"钻孔柱状图{code}"
        d = collect(stem)
        out.write_text(json.dumps(d, ensure_ascii=False), encoding="utf-8")
        print(f"{code}: 链 {d['n_chains']} → 线 {len(d['lines'])} 锚 {d['anchor_x']:.0f}",
              flush=True)


if __name__ == "__main__":
    main()
