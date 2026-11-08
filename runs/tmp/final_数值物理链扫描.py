# -*- coding: utf-8 -*-
"""final 数值物理链扫描:全量 30 张终值表,甄别数值列 OCR 丢点/误读/尾缀。

物理链(图纸铁约束):
  A 深度单调: depth[i] = depth[i-1] + thick[i]  (层厚=底深差)
  B 真厚:     true_thick[i] ≈ thick[i] * cos(倾角)   (±0.06 笔差容差)
甄别档:
  fixable  — 现值纯大数/带尾缀,插小数点或剥缀后与物理链唯一定位吻合 → 建议修
  ok       — 现值过物理链(深度整数等)= 纸面真值,不动
  manual   — 物理链定位不出 → 裁片人工核
"""
import glob
import json
import math
import re
import sys
from pathlib import Path

ROOT = Path(r"D:\Skye\Documents\Work\高维智矿\7.13杂活")
sys.path.insert(0, str(ROOT))
from openpyxl import load_workbook  # noqa: E402

SRC = ROOT / "outputs/Excel交付_终版_20261109"
OUT = ROOT / "runs/autoresearch_align/多源定级_20261106/数值物理链扫描_20261109.json"
import sys as _s
if len(_s.argv) > 1:                      # 可选:传入目录只析不覆盖基线清单
    SRC = Path(_s.argv[1])
    OUT = ROOT / "runs/tmp/_物理链_candidate.json"
TAIL = re.compile(r"^(\d+(?:\.\d+)?)[A-Za-zＥＥ]$")
INT_BIG = re.compile(r"^\d{2,}$")


def num(s):
    try:
        return float(str(s).strip())
    except (TypeError, ValueError):
        return None


def col_of(hdr, *names):
    for j, h in enumerate(hdr):
        if h:
            hs = str(h)
            for n in names:
                if n in hs:
                    return j
    return None


def tries(v):
    """纯大数/尾缀值的候选修复:插小数点各位置/剥缀。"""
    s = str(v).strip()
    cands = []
    m = TAIL.match(s)
    if m:
        cands.append(("剥缀", m.group(1)))
        s = m.group(1)
    if INT_BIG.match(s) and "." not in s:
        for k in range(1, len(s)):
            cands.append(("插点", s[:k] + "." + s[k:]))
    return cands


res = []
for p in sorted(glob.glob(str(SRC / "*_整合.xlsx"))):
    stem = Path(p).name.split("_")[0].replace("钻孔柱状图", "")
    wb = load_workbook(p, rich_text=True)
    ws = wb.active
    hdr = [c.value for c in ws[1]]
    cD = col_of(hdr, "深度")
    cT = col_of(hdr, "层厚")
    cTT = col_of(hdr, "真厚")
    cA = col_of(hdr, "倾角")
    if cD is None or cT is None:
        continue
    rows = list(ws.iter_rows(min_row=2, values_only=True))
    for i in range(len(rows)):
        r = i + 2
        d = num(rows[i][cD]) if cD is not None else None
        t = num(rows[i][cT]) if cT is not None else None
        tt = num(rows[i][cTT]) if cTT is not None else None
        raw_t = rows[i][cT] if cT is not None else None
        raw_tt = rows[i][cTT] if cTT is not None else None
        raw_d = rows[i][cD] if cD is not None else None
        ang = None
        if cA is not None:
            m = re.search(r"(\d+(?:\.\d+)?)", str(rows[i][cA] or ""))
            ang = float(m.group(1)) if m else None
        # --- A 深度差链:thick[i] 应≈ d[i]-d[i-1] ---
        if t is not None and i > 0 and num(rows[i-1][cD]) is not None and d is not None:
            gap = d - num(rows[i-1][cD])
            if abs(t - gap) > 0.021:
                fixed = None
                for kind, cand in tries(raw_t):
                    cv = num(cand)
                    if cv is not None and abs(cv - gap) <= 0.021:
                        fixed = (kind, cand)
                        break
                res.append({"图": stem, "xlsx行": r, "列": "层厚", "现值": str(raw_t),
                            "深度差": round(gap, 3), "建议": fixed, "档": "fixable" if fixed else "manual"})
        # --- A' 深度自身:5位大数试插点(与上一深度+本层厚吻合) ---
        if d is not None and INT_BIG.match(str(raw_d).strip()) and "." not in str(raw_d):
            prev_d = num(rows[i-1][cD]) if i > 0 else None
            fixed = None
            for kind, cand in tries(raw_d):
                cv = num(cand)
                ok = (prev_d is not None and t is not None
                      and abs(prev_d + t - cv) <= 0.021)
                if ok:
                    fixed = (kind, cand)
                    break
            res.append({"图": stem, "xlsx行": r, "列": "深度", "现值": str(raw_d),
                        "建议": fixed, "档": "fixable" if fixed else "manual"})
        # --- B 真厚链 ---
        if tt is not None and t is not None and t < 60:
            exp = t * math.cos(math.radians(ang)) if ang is not None else None
            if exp is not None and abs(tt - exp) > 0.06:
                fixed = None
                for kind, cand in tries(raw_tt):
                    cv = num(cand)
                    if cv is not None and abs(cv - exp) <= 0.06:
                        fixed = (kind, cand)
                        break
                res.append({"图": stem, "xlsx行": r, "列": "真厚", "现值": str(raw_tt),
                            "期望cos": round(exp, 3), "建议": fixed,
                            "档": "fixable" if fixed else "manual"})
        # --- 尾缀字母(任意数值列) ---
        for cname, raw in (("深度", raw_d), ("层厚", raw_t), ("真厚", raw_tt)):
            if raw is not None and TAIL.match(str(raw).strip()):
                res.append({"图": stem, "xlsx行": r, "列": cname, "现值": str(raw),
                            "档": "尾缀", "建议": None})

json.dump(res, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
from collections import Counter
c = Counter((x["档"], x["列"]) for x in res)
print("总计", len(res), dict(c))
fx = [x for x in res if x.get("建议")]
print("可自动修(fixable+建议):", len(fx))
for x in fx[:40]:
    print(" ", x["图"], "行", x["xlsx行"], x["列"], x["现值"], "->", x["建议"][1])
mn = [x for x in res if x["档"] == "manual"]
print("需人工:", len(mn))
for x in mn[:20]:
    print(" ", x["图"], "行", x["xlsx行"], x["列"], x["现值"])
print("->", OUT)
