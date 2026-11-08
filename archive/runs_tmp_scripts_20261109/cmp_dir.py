# -*- coding: utf-8 -*-
"""两个 行判定.json 目录逐张对表：层界/子行/其余/切开/走偏，只点变化大的那张。

用法: python runs/tmp/cmp_dir.py <A目录> <B目录>   （A=基线，B=新档）
"""
import json
import sys
from pathlib import Path

A, B = Path(sys.argv[1]), Path(sys.argv[2])
print(f"{'图':<6}{'层界A':>6}{'层界B':>6}{'Δ':>4}{'子行A':>6}{'子行B':>6}"
      f"{'链数A':>6}{'段数B':>6}{'切开B':>6}{'剔A':>4}{'剔B':>4}")
ta = tb = 0
for pa in sorted(A.glob("*_行判定.json")):
    pb = B / pa.name
    if not pb.exists():
        print(f"{pa.stem[:8]:<6} 缺 {pb}")
        continue
    a, b = (json.loads(p.read_text(encoding="utf-8")) for p in (pa, pb))
    ta += len(a["rows"])
    tb += len(b["rows"])
    if len(a["rows"]) == len(b["rows"]) and a["others_n"] == b["others_n"]:
        continue                                   # 只点变化大的，全量表另算总账
    print(f"{pa.stem[-8:-4]:<6}{len(a['rows']):>6}{len(b['rows']):>6}"
          f"{len(b['rows']) - len(a['rows']):>4}"
          f"{len(a['sub_rows']):>6}{len(b['sub_rows']):>6}"
          f"{a['n_chains']:>6}{b['n_pieces']:>6}{b['n_chains_split']:>6}"
          f"{a['n_lines_offgrid']:>4}{b['n_lines_offgrid']:>4}")
print(f"{'合计':<6}{ta:>6}{tb:>6}{tb - ta:>4}{'':>24}")
