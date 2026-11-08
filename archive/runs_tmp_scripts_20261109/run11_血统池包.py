# -*- coding: utf-8 -*-
"""run11:992 血统分叉剩余未判读 323 格判读包(run2 登记假设的剩余部分)。

问题=交付包值 vs 对比包值哪个=纸面(判读员只管看图转写,汇总做三向比对)。
裁片=v2 多边形几何;分派含两包值供判读员对照(明确告知两说均可疑)。
不动任何交付物;判读写值仍入第三表待批。
"""
import json
import sys
from pathlib import Path

ROOT = Path(r"D:\Skye\Documents\Work\高维智矿\7.13杂活")
PKG = ROOT / "runs/autoresearch_align/多源定级_20261106/血统分叉判读包_r11"
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "runs/tmp"))

import cv2  # noqa: E402

from src.core import paths  # noqa: E402
from src.handwriting.reread import ROLE_KEEP  # noqa: E402
from run5_pkg_v2 import row_ivs_stem, build  # noqa: E402

pool = json.loads((ROOT / "runs/tmp/fork992_未判读.json").read_text(encoding="utf-8"))
print("血统分叉未判读池:", len(pool))
PKG.mkdir(parents=True, exist_ok=True)
cache = {}
n_fail = 0
for e in pool:
    tag = f"{e['stem']}_行{e['row']}"
    stem = "钻孔柱状图" + e['stem']
    r = e['row']
    if stem not in cache:
        cache[stem] = (row_ivs_stem(stem),
                       cv2.imread(str(paths.RAW_DIR / f"{stem}.JPG"), cv2.IMREAD_GRAYSCALE),
                       json.load(open(paths.RUNS_DIR / "table_reconstruct" /
                                      f"{stem}_表头映射.json", encoding="utf-8")))
    (top_bot, ivs), gray, hm = cache[stem]
    if r - 2 not in ivs:
        print("跳过(无重放行):", tag)
        continue
    y0, y1 = ivs[r - 2]
    if r - 2 in top_bot:
        top_src, bot_src = top_bot[r - 2]
    else:
        top_src = bot_src = None
    keep = None
    for k in hm["keep"]:
        if k["name"] == ROLE_KEEP["desc"]:
            keep = sorted(k["x_in_band"])
    H, W = gray.shape[:2]
    x0 = max(0, int(keep[0]) - 8)
    x1 = min(W, int(keep[1]) + 8)
    try:
        cell, stripw = build(gray, x0, x1, top_src, y0, bot_src, y1)
    except Exception:
        n_fail += 1
        continue
    cv2.imwrite(str(PKG / f"{tag}_cell.png"), cell)
    cv2.imwrite(str(PKG / f"{tag}_strip.png"), stripw)
print("裁片完成, 失败:", n_fail)
BATCH = 15
nb = (len(pool) + BATCH - 1) // BATCH
for b in range(nb):
    part = pool[b * BATCH:(b + 1) * BATCH]
    (PKG / f"分派_血统_r11_{b}.json").write_text(
        json.dumps([dict(e, tag=f"{e['stem']}_行{e['row']}") for e in part],
                   ensure_ascii=False, indent=1), encoding="utf-8")
print(f"分派 {nb} 批")
