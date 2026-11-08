# -*- coding: utf-8 -*-
"""生产代码改完了：逐张比对 track_rows 现在的输出 vs A/B 档 runs/tmp/ab/框内/，两边必须一模一样。

只算不写盘（determine_rows 会覆盖正式行判定，这里不碰）。
用法: python runs/tmp/chk_prod.py [1018 1020 1034]
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from src.core import paths                                          # noqa: E402
from src.table import track_rows as tr                              # noqa: E402

AB = ROOT / "runs" / "tmp" / "ab" / "框内"
codes = [a for a in sys.argv[1:] if a.isdigit()] or ["1018", "1020", "1034", "1032"]
for code in codes:
    stem = f"钻孔柱状图{code}"
    a = json.loads((AB / f"{stem}_行判定.json").read_text(encoding="utf-8"))
    b = tr.assemble(tr.load_chains(stem))
    ya = [r["y_at_mid"] for r in a["rows"]]
    yb = [r["y_at_mid"] for r in b["rows"]]
    same = ya == yb and a["table_x"] == b["table_x"]
    print(f"{code}: A/B 层界{len(ya):>4} 生产{len(yb):>4}  表宽 {a['table_x']} vs {b['table_x']}  "
          f"{'一致' if same else '不一致 差集 ' + str(sorted(set(ya) ^ set(yb))[:6])}"
          f"  告警{b['warnings']}")
