# -*- coding: utf-8 -*-
"""带映射对账(2026-10-28):整合数据行 ↔ 还原.xlsx带 的位移体检。
不依赖 bmap,直接逐图比对 desc/dip 整列在位移 -1/0/+1 下的相等率,
确定 bmap 映射是否偏移;并统计 desc 空(带级有值)的真实规模。
"""
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from src.core import paths  # noqa: E402
from src.table.agnes_era_blocks import OUT  # noqa: E402
from src.table.finalize_tables import column_roles  # noqa: E402
from openpyxl import load_workbook  # noqa: E402


def col_of(xdata, roles, key):
    c = roles.get(key)
    return [("" if (len(r) <= c or r[c] is None) else str(r[c]).strip())
            for r in xdata[1:]] if c is not None else None


def main():
    rep = {}
    for vp in sorted(OUT.glob("*/裁决.json")):
        stem = vp.parent.name
        wrb = load_workbook(paths.REEMIT_DIR_20261023 / f"{stem}_还原.xlsx")
        band = list(wrb.active.iter_rows(values_only=True))
        fin = load_workbook(paths.FINALIZE_FULL_DIR / f"{stem}_整合.xlsx")
        finw = list(fin.active.iter_rows(values_only=True))
        rb = column_roles(band[0])
        rf = column_roles(finw[0])
        rec = {"n_band": len(band) - 1, "n_fin": len(finw) - 1}
        for key in ("desc", "dip"):
            b, f = col_of(band, rb, key), col_of(finw, rf, key)
            if b is None or f is None:
                continue
            n = min(len(b), len(f))
            eq = {}
            for off in (-1, 0, 1):
                eq[off] = sum(1 for i in range(n)
                              if 0 <= i + off < len(b) and b[i + off] == f[i])
            f_empty_band_has = sum(1 for i in range(n)
                                   if not f[i] and i < len(b) and b[i])
            rec[key] = {"eq": eq, "fin空带值有": f_empty_band_has,
                        "fin空": sum(1 for v in f if not v)}
        rep[stem] = rec
    p = paths.RUNS_DIR / "tmp" / "diag_band_offset.json"
    p.write_text(json.dumps(rep, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{'图':<14}{'带/行':>9}  desc eq(-1/0/+1)  空格(带值有)   dip eq(-1/0/+1)")
    tot = {}
    for s, r in rep.items():
        d, dp = r.get("desc", {}), r.get("dip", {})
        if d:
            e = d["eq"]
            print(f"{s.replace('钻孔柱状图', ''):<14}{r['n_band']:>4}/{r['n_fin']:<4}"
                  f"  {e[-1]:>4}/{e[0]:>4}/{e[1]:<4}  空{d['fin空']:>3}(带值有{d['fin空带带'] if 'fin空带带' in d else d['fin空带值有']:>3})"
                  f"   {dp['eq'][-1]:>4}/{dp['eq'][0]:>4}/{dp['eq'][1]:<4}" if dp else "")
    print("→", p)


if __name__ == "__main__":
    main()
