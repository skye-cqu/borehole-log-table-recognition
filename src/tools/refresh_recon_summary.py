# -*- coding: utf-8 -*-
"""按 xlsx 现值重算 对账汇总.json 的 QC 段(不重跑 OCR/Agnes,不动处置字段)。

为什么需要:对账汇总.json 由 reconcile 阶段生成,后续伪差修复与视觉判读回写都
改了格值,该文件的 QC 数字就陈旧了(实测停在 458 格口径)。README 分级表的
"真厚互证对"列直接取它,不刷新就会与交付 xlsx 自相矛盾。
"""
from __future__ import annotations

import json
import math
import re
import sys
from pathlib import Path

from openpyxl import load_workbook

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.core import paths  # noqa: E402

RUNS = paths.RUNS_DIR / "table_reconstruct"
STEMS4 = ("钻孔柱状图1018", "钻孔柱状图1030", "钻孔柱状图1032", "钻孔柱状图1042")


def last_num(v):
    if v is None:
        return None
    m = re.findall(r"\d+\.?\d*", str(v))
    return float(m[-1]) if m else None


def main():
    fp = RUNS / "对账汇总.json"
    old = json.loads(fp.read_text(encoding="utf-8")) if fp.exists() else {}
    for stem in STEMS4:
        ws = load_workbook(RUNS / f"{stem}_还原_补产终版.xlsx", read_only=True).active
        head = [c.value for c in next(ws.iter_rows(min_row=1, max_row=1))]
        col = {n: i for i, n in enumerate(head)}
        rows = list(ws.iter_rows(min_row=2, values_only=True))
        prev_depth, mono_ok, pairs, hits = None, True, 0, 0
        for r in rows:
            def g(name):
                return r[col[name]] if name in col and col[name] < len(r) else None
            d = last_num(g("深度"))
            if d is not None and prev_depth is not None and d <= prev_depth:
                mono_ok = False
            if d is not None:
                prev_depth = d
            th, inc, true_t = (last_num(g("层厚")), last_num(g("倾角")),
                               last_num(g("真厚")))
            if None in (th, inc, true_t):
                continue
            pairs += 1
            if abs(true_t - th * math.cos(math.radians(inc))) <= 0.02:
                hits += 1
        qc = {"行数": len(rows), "深度递增": mono_ok, "真厚互证对": pairs,
              "互证≤0.02m": hits,
              "互证率": round(hits / pairs, 3) if pairs else 0.0}
        old.setdefault(stem, {})
        old[stem]["QC"] = qc
        print(f"{stem[-4:]}: 行{qc['行数']} 深度递增={qc['深度递增']} "
              f"可核{pairs}对 互证{hits}对 互证率{qc['互证率']:.1%}")
    fp.write_text(json.dumps(old, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"已刷新 {fp.name} 的 QC 段(处置相关字段未动)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
