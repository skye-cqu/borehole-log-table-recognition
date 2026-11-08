# -*- coding: utf-8 -*-
"""30 图客观审计:表头映射 vs 原图竖墨;时代列状态;行数。"""
import cv2, json
import numpy as np
from pathlib import Path
R = Path(r"D:\Skye\Documents\Work\高维智矿\7.13杂活")
RAW = R / "data" / "raw_images"; TR = R / "runs" / "table_reconstruct"
CANON = ["地质时代", "煤层标志层号", "深度", "层厚", "采长", "倾角", "真厚", "岩性描述"]

def vpeaks(gray, y0, y1, th=0.55, minsep=8):
    band = gray[int(y0):int(y1)]
    if band.shape[0] < 4: return []
    frac = (band < 150).mean(axis=0)
    idx = [i for i in range(2, len(frac)-2) if frac[i] >= th and frac[i] == frac[max(0,i-3):i+4].max()]
    out = []
    for i in idx:
        if out and i - out[-1][0] <= minsep:
            if frac[i] > frac[out[-1][0]]: out[-1] = (i, float(frac[i]))
        else: out.append((i, float(frac[i])))
    return out

rows_out = []
for k in range(1015, 1045):
    stem = f"钻孔柱状图{k}"
    hm = json.load(open(TR / f"{stem}_表头映射.json", encoding="utf-8"))
    rd = json.load(open(TR / f"{stem}_行判定.json", encoding="utf-8"))
    keep = [c["name"] for c in hm["keep"]]
    gray = cv2.imread(str(RAW / f"{stem}.JPG"), cv2.IMREAD_GRAYSCALE)
    b0, b1 = hm["band"]
    # 数据区:取表头下 200..1200px 的多行带,量竖墨
    y0, y1 = b1 + 200, min(gray.shape[0]-10, b1 + 1400)
    pk = [x for x, _ in vpeaks(gray, y0, y1)]
    seps = [round(float(v), 1) for v in hm["sep_x_band"]]
    # 每条映射 sep 是否落在真墨附近(±6px)
    def near(x):
        return min((abs(x - p) for p in pk), default=999)
    sep_dev = [round(near(s), 1) for s in seps]
    # 真墨里未被映射覆盖的峰(数据区,排除柱状/水文区 x>某值 的图案线先不排)
    unmatched = [p for p in pk if min((abs(p - s) for s in seps), default=999) > 6]
    rows_out.append({
        "图": k, "keep": keep, "keep_ok": keep == [c for c in CANON if c in keep],
        "ok": hm["ok"], "warn": len(hm["warnings"]),
        "sep_dev_max": max(sep_dev) if sep_dev else None,
        "sep_dev_gt6": sum(1 for d in sep_dev if d > 6),
        "unmatched_peaks": len(unmatched),
        "unmatched_x": unmatched[:12],
        "n_rows": len(rd["rows"]),
        "w": gray.shape[1],
    })

print(f"{'图':>5} {'ok':>5} {'warn':>4} {'行数':>4} {'宽':>5} {'sep偏差>6':>9} {'未映射峰':>8}  keep")
for r in rows_out:
    print(f"{r['图']:>5} {str(r['ok']):>5} {r['warn']:>4} {r['n_rows']:>4} {r['w']:>5} {r['sep_dev_gt6']:>9} {r['unmatched_peaks']:>8}  {r['keep']}")
json.dump(rows_out, open(R/"runs"/"tmp"/"审计_表头映射_20261015.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("\n-- 非标准 keep 顺序 --")
for r in rows_out:
    if not r["keep_ok"]:
        print(f"  {r['图']}: {r['keep']}")
print("\n-- sep 有偏差的图 --")
for r in rows_out:
    if r["sep_dev_gt6"] or r["unmatched_peaks"]:
        print(f"  {r['图']}: sep偏差>6px {r['sep_dev_gt6']} 条, 未映射真墨峰 {r['unmatched_peaks']} 处 {r['unmatched_x']}")
