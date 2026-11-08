# -*- coding: utf-8 -*-
"""final X条重裁拼图 v2(2026-11-09):非数值列(时代/层号/描述)违例格固定宽窗。

缺陷复盘:主判_X 裁窗沿用数值区;X2 重裁用表头映射坐标,但 1019 映射 x 整体右偏
~85px(深度实区≈340-490,映射 449-573),时代/层号仍被切。
v2:era/mark 固定 x∈[100,700](时代+层号+深度锚全包容,与映射坐标无关);
   desc 用映射列范围 ±150px(宽列偏移不敏感),缩放 880。
输出:裁片 runs/autoresearch_align/多源定级_20261106/X门禁裁片_20261109/
     拼图 runs/tmp/_主判X2_*.png
"""
import json
import sys
from pathlib import Path

ROOT = Path(r"D:\Skye\Documents\Work\高维智矿\7.13杂活")
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "archive/runs_tmp_scripts_20261109"))

import cv2  # noqa: E402
import numpy as np  # noqa: E402

from src.core import paths  # noqa: E402
from run5_pkg_v2 import row_ivs_stem  # noqa: E402

IDX = json.load(open(ROOT / "runs/tmp/_主判索引.json", encoding="utf-8"))
XS = [x for x in IDX if x["no"] > 187]
OUTD = ROOT / "runs/autoresearch_align/多源定级_20261106/X门禁裁片_20261109"
OUTD.mkdir(parents=True, exist_ok=True)

TAG = {"地质时代": "era", "煤层标志层号": "mark", "岩性描述": "desc"}
cache = {}


def chart(stem0):
    if stem0 not in cache:
        stem = "钻孔柱状图" + stem0
        cache[stem0] = (row_ivs_stem(stem),
                        cv2.imread(str(paths.RAW_DIR / f"{stem}.JPG"), cv2.IMREAD_GRAYSCALE),
                        json.load(open(paths.RUNS_DIR / "table_reconstruct" /
                                       f"{stem}_表头映射.json", encoding="utf-8")))
    return cache[stem0]


def col_ranges(hm):
    out = {}
    for c in hm["keep"]:
        xs = sorted(c["x_in_band"])
        out[c["name"]] = (xs[0], xs[-1])
    return out


items = []
for x in XS:
    stem0 = x["图"]
    (tb, ivs), gray, hm = chart(stem0)
    cr = col_ranges(hm)
    tcol = x["列"][0]
    if tcol == "岩性描述":
        tx = cr.get(tcol) or cr.get(next((k for k in cr if "描述" in k)))
        if tx is None:
            print("无列", stem0, tcol, list(cr))
            continue
        x0, x1 = tx[0] - 150, tx[1] + 150
    else:
        x0, x1 = 100, 700          # 固定宽窗:时代+层号+深度锚,不依赖映射坐标
    k = x["xlsx行"] - 2
    y0, y1 = ivs.get(k, (0, 0))
    h = max(1, int(y1 - y0))
    ya, yb = max(0, int(y0) - h), min(gray.shape[0], int(y1) + h)
    win = gray[ya:yb, max(0, int(x0)):min(gray.shape[1], int(x1))]
    if win.size == 0:
        print("空窗", x["no"])
        continue
    scale = min(1.0, 880.0 / win.shape[1])
    if scale < 1.0:
        win = cv2.resize(win, None, fx=scale, fy=scale)
    fn = f"{stem0}_r{x['xlsx行']}_{TAG.get(tcol, tcol)}.png"
    cv2.imwrite(str(OUTD / fn), win)
    cur = x["现值"].get(tcol, "")
    lab = f"{x['no']}# {stem0} r{x['xlsx行']} {TAG.get(tcol,tcol)} cur={cur!r}"
    bar = np.full((36, win.shape[1]), 235, np.uint8)
    cv2.putText(bar, lab.encode("ascii", "ignore").decode(), (8, 26),
                cv2.FONT_HERSHEY_SIMPLEX, 0.62, 30, 2)
    items.append((x["no"], np.vstack([bar, win])))

items.sort(key=lambda t: t[0])
PER = 9
for bi in range(0, len(items), PER):
    grp = [t[1] for t in items[bi:bi + PER]]
    w = max(g.shape[1] for g in grp)
    grp = [np.pad(g, ((0, 14), (0, w - g.shape[1])), constant_values=255) for g in grp]
    cv2.imwrite(str(ROOT / f"runs/tmp/_主判X2_{bi // PER + 1}.png"), np.vstack(grp))

json.dump({str(no): f"{x['图']}_r{x['xlsx行']}_{TAG.get(x['列'][0], x['列'][0])}.png"
           for no, x in ((t[0], next(y for y in XS if y['no'] == t[0])) for t in items)},
          open(ROOT / "runs/tmp/_X重裁映射.json", "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)
print(f"X条重裁 {len(items)}/{len(XS)} 格 -> {OUTD.name},拼图 {len(items) // PER + 1} 张")
