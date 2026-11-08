# -*- coding: utf-8 -*-
"""丢了哪 31 条：门禁前基线的层界，逐条到当前产物里找下落。

每条基线层界按 y±12 找当前 层界/子行线/走偏线/被剔链，报"去哪了"：
  没了(没进任何簇) / 降级成子行线(数值区覆盖率不够) / 落 off_grid(线级形状闸) /
  成员链整条被剔(链级闸) / 并入更远的线(簇合并)。
用法: python runs/tmp/diag_lost.py 1027 "runs/tmp/ab/xxx.json"
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "rollback" / "行判定_门禁前_20260924"
TOL = 12.0


def near(ents, y):
    return min(ents, key=lambda e: abs(e["y_at_mid"] - y)) if ents else None


def at(e, y):
    return e is not None and abs(e["y_at_mid"] - y) <= TOL


def main(code, cur_path):
    b = json.load(open(BASE / f"钻孔柱状图{code}_行判定.json", encoding="utf-8"))
    c = json.load(open(cur_path, encoding="utf-8"))
    used = set()
    rows = c["rows"]
    print(f"{code}: 基线 {len(b['rows'])} → 当前 {len(rows)} 层界"
          f"（子行线 {len(c['sub_rows'])}，off_grid {len(c['off_grid'])}，"
          f"剔链 {c['n_chains_stepped']}）")
    print(f"{'基线y':>8}{'x跨度':>14}{'台阶':>7}{'去向':>18}{'当前y':>9}{'差':>6}{'cov':>6}")
    n = 0
    for r in b["rows"]:
        y = r["y_at_mid"]
        hit = next((i for i, e in enumerate(rows)
                    if i not in used and abs(e["y_at_mid"] - y) <= TOL), None)
        if hit is not None:
            used.add(hit)
            continue
        n += 1
        sub = near(c["sub_rows"], y)
        off = near(c["off_grid"], y)
        rej = min(c["rejected"], key=lambda e: abs(e["y"] - y)) if c["rejected"] else None
        if rej and abs(rej["y"] - y) <= TOL and (sub is None or not at(sub, y)):
            where, wy, cov = "整链被剔", rej["y"], ""
        elif off and abs(off["y_at_mid"] - y) <= TOL:
            where, wy, cov = "落off_grid", off["y_at_mid"], f"{off['cov_num']:.2f}"
        elif sub and abs(sub["y_at_mid"] - y) <= TOL:
            where, wy, cov = "降级子行线", sub["y_at_mid"], f"{sub['cov_num']:.2f}"
        else:
            nxt = min(rows, key=lambda e: abs(e["y_at_mid"] - y)) if rows else None
            if nxt and abs(nxt["y_at_mid"] - y) <= 30:
                where, wy, cov = "并入邻线", nxt["y_at_mid"], f"{nxt['cov_num']:.2f}"
            else:
                where, wy, cov = "消失了", float("nan"), ""
        print(f"{y:>8.0f}{r['x'][0]:>6.0f}-{r['x'][1]:<7.0f}{r['step']:>7.0f}"
              f"{where:>18}{wy:>9.0f}{wy - y:>6.0f}{cov:>6}")
    print(f"共丢 {n} 条")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
