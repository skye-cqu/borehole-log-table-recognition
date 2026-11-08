# -*- coding: utf-8 -*-
"""诊断出表两缺陷的病位(2026-10-28,约束9 先量化再动代码):
①desc格底字漏读(69补录格) ②dip列界渗漏(47含杂格)。
对每格查 还原.xlsx 带级值(=build_cells OCR 原始输出):
  带级已空 → 窗口漏读(病在 _crop_cell);带级有值整合却空 → 归因病(finalize)。
另记上/下邻带值,判断文字是否落错带。写 runs/tmp/diag_ocr_window.json + 摘要。
"""
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from src.core import paths  # noqa: E402
from src.table.agnes_era_blocks import OUT, chart_rows  # noqa: E402
from src.table.finalize_tables import column_roles  # noqa: E402
from openpyxl import load_workbook  # noqa: E402


def bnd(bmap, p, step):
    while 0 <= p < len(bmap) and bmap[p] is None:
        p += step
    return bmap[p] if 0 <= p < len(bmap) else None


def main():
    out = {"desc": [], "dip": [], "skip": []}
    for vp in sorted(OUT.glob("*/裁决.json")):
        stem = vp.parent.name
        try:
            g = chart_rows(stem)
        except Exception as e:  # noqa: BLE001
            out["skip"].append({"stem": stem, "err": repr(e)[:120]})
            continue
        bmap, roles_c = g["bmap"], g["roles"]
        wb = load_workbook(paths.REEMIT_DIR_20261023 / f"{stem}_还原.xlsx")
        xdata = list(wb.active.iter_rows(values_only=True))
        c_desc, c_dip = roles_c.get("desc"), roles_c.get("dip")

        def band_row(di):
            bi = bnd(bmap, di, -1)
            return None if bi is None else bi + 2   # 带li → xlsx行li+2(1基,行1=表头)

        def cell(di, c):
            r = band_row(di)
            if r is None or r >= len(xdata) or c is None or len(xdata[r]) <= c:
                return None
            v = xdata[r][c]
            return "" if v is None else str(v)

        for e in json.loads(vp.read_text(encoding="utf-8")).get("条目", []):
            d = e.get("依据", "")
            di = int(e["行"]) - 2
            k = e["角色"]
            hit = ("采Agnes成句" in d and k == "desc") or \
                  ("倾角词表" in d and k == "dip")
            if not hit:
                continue
            c = c_desc if k == "desc" else c_dip
            mine = cell(di, c)
            up = cell(di - 1, c)
            dn = cell(di + 1, c)
            rec = {"stem": stem, "行": e["行"], "原": e.get("原", ""),
                   "agnes": str(e.get("agnes", ""))[:60],
                   "带级现值": mine, "上带": up, "下带": dn}
            out[k].append(rec)
    p = paths.RUNS_DIR / "tmp" / "diag_ocr_window.json"
    p.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")

    for k in ("desc", "dip"):
        rs = out[k]
        band_empty = sum(1 for r in rs if not (r["带级现值"] or "").strip())
        band_has = len(rs) - band_empty
        # 整合层与带级一致性: 原 == 带级现值 → 归因无误传; 原≠带级 → finalize 改写/丢
        mismatch = sum(1 for r in rs
                       if (r["原"] or "").strip() != (r["带级现值"] or "").strip())
        print(f"{k}: {len(rs)}格  带级空{band_empty} 带级有值{band_has}  "
              f"整合原值≠带级值{mismatch}")
        for r in rs[:6]:
            print("  ", json.dumps(r, ensure_ascii=False)[:220])
    if out["skip"]:
        print("skip:", json.dumps(out["skip"], ensure_ascii=False))
    print("→", p)


if __name__ == "__main__":
    main()
