# -*- coding: utf-8 -*-
"""二轮错数:打印目标行邻域(Δ互证),核对现值与预期旧值一致。"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from openpyxl import load_workbook

ROOT = Path(__file__).resolve().parents[2]
B = ROOT / "runs" / "table_reconstruct_重出_20261005_项④行线补全"

# (图号, xlsx行, 列索引, 预期旧值)
PATCH = [
    ("1027", 2, 2, "2904"), ("1035", 39, 2, "57.71"), ("1016", 105, 3, "0"),
    ("1020", 73, 2, "22923.0"), ("1020", 97, 2, "27282.0"),
    ("1020", 122, 2, "31592.0"), ("1030", 27, 2, "12445.0"),
    ("1044", 108, 2, "37683.0"), ("1034", 65, 3, "100.0"),
    ("1027", 71, 3, "1.78"), ("1027", 75, 3, "20.0"),
]
REGISTER = [
    ("1027", 6), ("1031", 54), ("1015", 6), ("1016", 106), ("1033", 46),
    ("1034", 118), ("1029", 58), ("1024", 51), ("1024", 114), ("1024", 119),
    ("1040", 78), ("1040", 79), ("1044", 90),
]
CACHE = {}

def sheet(stem):
    if stem not in CACHE:
        wb = load_workbook(B / f"钻孔柱状图{stem}_还原.xlsx", data_only=True)
        CACHE[stem] = list(wb.active.iter_rows(values_only=True))
    return CACHE[stem]

def num(v):
    try:
        return float(str(v))
    except Exception:
        return None

def show(stem, r, mark, ci=None, old=None):
    vals = sheet(stem)
    hdr = vals[0]
    cur = vals[r - 1][ci] if ci else vals[r - 1][2]
    okv = ""
    if old is not None:
        okv = " 旧值✓" if num(cur) == num(old) else f" 旧值✗现值={cur!r}"
    print(f"=== {stem} r{r} [{mark}] 现{ci列名(hdr, ci) if ci else '深度'}={cur!r}{okv}")
    for rr in range(max(1, r - 2), min(len(vals), r + 2) + 1):
        row = vals[rr - 1]
        tag = ">>" if rr == r else "  "
        print(f" {tag}r{rr}: {row[1]!r} | 深={row[2]!r} | 厚={row[3]!r} | 真={row[4] if len(row)>4 else ''!r} | 角={row[5] if len(row)>5 else ''!r}")
    d0, d1, d2 = num(vals[r-2][2]) if r >= 2 else None, num(vals[r-1][2]), num(vals[r][2]) if r < len(vals) else None
    t0, t1, t2 = num(vals[r-2][3]) if r >= 2 else None, num(vals[r-1][3]), num(vals[r][3]) if r < len(vals) else None
    if None not in (d0, d1):
        print(f"    Δ上行={round(d1-d0,3)} vs 上行层厚={t0}")
    if None not in (d1, d2):
        print(f"    Δ下行={round(d2-d1,3)} vs 本行层厚={t1} | 下行Δ={round(d2-d1,3)} vs 下行层厚={t2}")

def ci列名(hdr, ci):
    return f"c{ci}:{hdr[ci]}"

print("########## PATCH ##########")
for s, r, ci, old in PATCH:
    show(s, r, "PATCH", ci, old)
print("\n########## REGISTER ##########")
for s, r in REGISTER:
    show(s, r, "REGISTER")
