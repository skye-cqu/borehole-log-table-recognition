# -*- coding: utf-8 -*-
"""final 门禁违例批量裁片+分派(2026-11-09):288 格数值区宽窗,子代理抄录纸面值。

每格裁 x=深度列左缘-40..真厚列右缘+40, y=行带±1 行高(折线偏差容差),
统一高 900px 宽。分派 json:每批 18 格,含现值与门禁违例类型。
"""
import json
import sys
from pathlib import Path

ROOT = Path(r"D:\Skye\Documents\Work\高维智矿\7.13杂活")
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "archive/runs_tmp_scripts_20261109"))

import cv2  # noqa: E402

from src.core import paths  # noqa: E402
from run5_pkg_v2 import row_ivs_stem  # noqa: E402

VIOL = json.load(open(ROOT / "runs/autoresearch_align/多源定级_20261106/列域门禁_20261109.json",
                      encoding="utf-8"))
OUTD = ROOT / "runs/autoresearch_align/多源定级_20261106/数值门禁裁片_20261109"
OUTD.mkdir(parents=True, exist_ok=True)

# 每图数值区 x 范围与列角色
cache = {}
items = []
for x in VIOL:
    stem0 = x["图"]
    stem = "钻孔柱状图" + stem0
    if stem not in cache:
        cache[stem] = (row_ivs_stem(stem),
                       cv2.imread(str(paths.RAW_DIR / f"{stem}.JPG"), cv2.IMREAD_GRAYSCALE),
                       json.load(open(paths.RUNS_DIR / "table_reconstruct" /
                                      f"{stem}_表头映射.json", encoding="utf-8")))
    (tb, ivs), gray, hm = cache[stem]
    cols = {c["name"]: sorted(c["x_in_band"]) for c in hm["keep"]}
    numcols = [cols[k] for k in ("深度", "层厚", "采长", "倾角", "真厚") if k in cols]
    if not numcols:
        continue
    x0 = min(c[0] for c in numcols) - 40
    x1 = max(c[-1] for c in numcols) + 40
    k = x["xlsx行"] - 2
    y0, y1 = ivs.get(k, (0, 0))
    h = max(1, int(y1 - y0))
    ya, yb = max(0, int(y0) - h), min(gray.shape[0], int(y1) + h)
    win = gray[ya:yb, max(0, int(x0)):min(gray.shape[1], int(x1))]
    if win.size == 0:
        continue
    scale = min(1.0, 900.0 / win.shape[1])
    if scale < 1.0:
        win = cv2.resize(win, None, fx=scale, fy=scale)
    fn = f"{stem0}_r{x['xlsx行']}_{x['列']}.png"
    cv2.imwrite(str(OUTD / fn), win)
    items.append({"图": stem0, "xlsx行": x["xlsx行"], "列": x["列"],
                  "现值": x["值"], "img": fn})

BATCH = 18
batches = [items[i:i + BATCH] for i in range(0, len(items), BATCH)]
for bi, b in enumerate(batches):
    json.dump(b, open(ROOT / f"runs/tmp/_数值判读分派_{bi}.json", "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
print(f"裁片 {len(items)} 格,{len(batches)} 批 -> {OUTD.name}")
