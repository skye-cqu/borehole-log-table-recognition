# -*- coding: utf-8 -*-
"""把某一档门禁的 行判定.json 落到单独目录，用同一把尺子量（不碰 runs/ 正式产物）。

用法: python runs/tmp/emit_split.py <档名> [code...]     # 无参数=30 张
量它：YARD_SRC=runs/tmp/ab/<档名> python runs/tmp/yardstick.py
     SRC=runs/tmp/ab/<档名>      python runs/tmp/diag_missed.py
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from src.core import paths                                          # noqa: E402
from src.table import track_rows as tr                              # noqa: E402

# 档名 → (skew, split, SKEW_BAND)；None = 模块默认，0 = 关掉这一道
CONFIGS = {"门禁前": (9.0, 0.0, None), "只形状闸": (None, 0.0, None), "定稿": (None, None, None),
           "切分0.5": (None, 0.5, None), "切分1.0": (None, 1.0, None),
           "全表参照": (None, None, 0.0)}

tag = sys.argv[1]
skew, split, band = CONFIGS[tag]
if band is not None:
    tr.SKEW_BAND = band
out = ROOT / "runs" / "tmp" / "ab" / tag
out.mkdir(parents=True, exist_ok=True)
codes = [a for a in sys.argv[2:] if a.isdigit()] or \
        sorted(p.stem[-4:] for p in paths.CANDIDATE_COORD_DIR.glob("*.json"))
for code in codes:
    stem = f"钻孔柱状图{code}"
    o = tr.assemble(tr.load_chains(stem), skew, split)
    (out / f"{stem}_行判定.json").write_text(
        json.dumps(o, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{code}: 层界{len(o['rows'])} 剔线{o['n_lines_offgrid']} "
          f"切开{o['n_chains_split']}条链→{o['n_pieces']}段")
