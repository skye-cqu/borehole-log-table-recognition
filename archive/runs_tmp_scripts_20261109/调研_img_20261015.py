# -*- coding: utf-8 -*-
import cv2, json
from pathlib import Path
R = Path(r"D:\Skye\Documents\Work\高维智矿\7.13杂活")
RAW = R / "data" / "raw_images"
print("raw files:", len(list(RAW.glob("*.JPG"))), len(list(RAW.glob("*.jpg"))))
for stem in ["钻孔柱状图1032", "钻孔柱状图1042", "钻孔柱状图1033", "钻孔柱状图1019"]:
    p = RAW / f"{stem}.JPG"
    if not p.exists():
        cands = list(RAW.glob(f"{stem}*"))
        print(stem, "->", [c.name for c in cands]); continue
    img = cv2.imread(str(p), cv2.IMREAD_GRAYSCALE)
    print(stem, img.shape, "mean", round(float(img.mean()),1), "min", int(img.min()), "max", int(img.max()))
# 行判定:每图行数
TR = R / "runs" / "table_reconstruct"
for stem in ["钻孔柱状图1032", "钻孔柱状图1042", "钻孔柱状图1033", "钻孔柱状图1019"]:
    rd = json.load(open(TR / f"{stem}_行判定.json", encoding="utf-8"))
    rows = rd["rows"]
    print(f"--- {stem}: rows={len(rows)} table_x={rd.get('table_x')} keys={list(rd.keys())[:12]}")
    for r in rows[:4]:
        poly = r.get("poly") or []
        xs = [p[0] for p in poly]; ys = [p[1] for p in poly]
        print(f"    row id={r.get('id')} n_poly={len(poly)} x=[{min(xs) if xs else None},{max(xs) if xs else None}] y=[{min(ys) if ys else None},{max(ys) if ys else None}] sub={r.get('sub')} n_chains={r.get('n_chains')}")
