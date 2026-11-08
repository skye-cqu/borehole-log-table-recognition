# -*- coding: utf-8 -*-
"""30 张新旧层界对照表：旧 = rollback 快照，新 = 现行 行判定.json。

列：张 / 旧层界 / 新层界 / Δ / 旧子行 / 新子行 / 层厚数(交付表行数真值旁证) / 新层界-层厚数
末行合计。只读，不改任何产物。
"""
import json
import re
import sys
from pathlib import Path

from openpyxl import load_workbook

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from src.core import paths                                          # noqa: E402

OLD = ROOT / "rollback" / "行判定_旧判据_20260923"
DELIV = paths.PROJECT_ROOT / "outputs/Excel交付_最终_20260915"
NUM = re.compile(r"-?\d+(?:\.\d+)?")


def n_rows(p):
    d = json.loads(Path(p).read_text(encoding="utf-8"))
    return len(d["rows"]), len(d.get("sub_rows", [])), d.get("warnings", [])


def delivered(code):
    """交付表：数据行数 + 多值格数（口径同 audit_deliverable S3）+ 层厚数值个数(应有行数旁证)。"""
    p = DELIV / f"{code}_还原.xlsx"
    if not p.exists():
        return 0, 0, 0
    ws = load_workbook(p, read_only=True, data_only=True).active
    rows = list(ws.iter_rows(values_only=True))
    hdr = [str(h or "") for h in rows[0]]
    idx = [i for i, h in enumerate(hdr)
           if any(k in h for k in ("深度", "层厚", "采长", "真厚"))]
    multi = sum(1 for r in rows[1:] for i in idx
                if isinstance(r[i], str) and len(NUM.findall(r[i])) > 1)
    ti = [i for i, h in enumerate(hdr) if "层厚" in h or "真厚" in h]
    n_t = 0
    for i in ti:
        n_t = max(n_t, sum(len(NUM.findall(str(r[i]))) if isinstance(r[i], str)
                           else (1 if isinstance(r[i], (int, float)) else 0)
                           for r in rows[1:]))
    return len(rows) - 1, multi, n_t


def main():
    codes = sorted(p.name[5:9] for p in OLD.glob("*_行判定.json"))
    print(f"{'张':<6}{'旧层界':>7}{'新层界':>7}{'Δ':>6}{'旧子行':>7}{'新子行':>7}"
          f"{'应有行数':>9}{'新-应有':>8}{'交付多值格':>11}")
    tot = [0] * 6
    warn = []
    for c in codes:
        stem = f"钻孔柱状图{c}"
        o = n_rows(OLD / f"{stem}_行判定.json")
        fp = paths.RUNS_DIR / "table_reconstruct" / f"{stem}_行判定.json"
        if not fp.exists():
            print(f"{c:<6}{o[0]:>7}{'待生成':>7}")
            continue
        n = n_rows(fp)
        ndel, multi, n_t = delivered(c)
        tot[0] += o[0]; tot[1] += n[0]; tot[2] += o[1]; tot[3] += n[1]
        tot[4] += n_t; tot[5] += multi
        if n[2]:
            warn.append((c, n[2]))
        print(f"{c:<6}{o[0]:>7}{n[0]:>7}{n[0]-o[0]:>+6}{o[1]:>7}{n[1]:>7}"
              f"{n_t:>9}{n[0]-n_t:>+8}{multi:>11}")
    print(f"{'合计':<5}{tot[0]:>7}{tot[1]:>7}{tot[1]-tot[0]:>+6}{tot[2]:>7}"
          f"{tot[3]:>7}{tot[4]:>9}{tot[1]-tot[4]:>+8}{tot[5]:>11}")
    for c, w in warn:
        print(f"  ! {c}: {w}")


if __name__ == "__main__":
    main()
