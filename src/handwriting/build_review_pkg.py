# -*- coding: utf-8 -*-
"""疑错人审包生成:可信(双族)级矛盾格,每格出 单元格裁窗+行带窗 两张裁片。

包 = runs/autoresearch_align/多源定级_20261106/疑错人审包/
  {stem}_行{r}_cell.png / _strip.png + 索引.md(三方读文对照表)。
零改动值;用户逐格判"现值对/众读对/都错"即可。
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import numpy as np

from src.core import paths
from src.handwriting.cellcrop import crop_window
from src.handwriting.multisource_grade import OD
from src.handwriting.reread import ROLE_KEEP

PKG = OD / "疑错人审包"
MY = 8


def main():
    d = json.loads((OD / "定级.json").read_text(encoding="utf-8"))
    cells = d["可信级矛盾"]
    # 单族双几何级矛盾:同引擎两几何+≥3票,证据低一档,单独列出
    prov = [e for e in d["cells"]
            if e["级"] == "可信(单族双几何)" and e["现值关系"] == "矛盾现值"]
    if not cells and not prov:
        print("无疑错格")
        return
    import cv2
    PKG.mkdir(exist_ok=True)
    cache = json.loads(paths.AUTORESEARCH_ROWCACHE.read_text(encoding="utf-8"))
    need = {}
    for e in cells + prov:
        e["_档"] = "双族" if e in cells else "单族双几何"
        need.setdefault(e["stem"], []).append(e["行"])
    lines = ["# 疑错人审包(多源定级矛盾)", "",
             f"双族级 {len(cells)} 格(两引擎族+≥3票同文,证据最硬);"
             f"单族双几何级 {len(prov)} 格(同引擎两几何,证据低一档)。",
             "判定口径:每格看两张裁片(单元格裁窗/行带窗),在三者中择一:",
             "现值对 / 众读对 / 都不对(写正确文本)。", "",
             "| 档 | 图/行 | 现值 | 众读(票) | 次读(票) | 行带读 | 判定 |",
             "|---|---|---|---|---|---|---|"]
    for stem, rows_ in sorted(need.items()):
        hm = json.load(open(paths.RUNS_DIR / "table_reconstruct" /
                            f"{stem}_表头映射.json", encoding="utf-8"))
        keep = None
        for k in hm["keep"]:
            if k["name"] == ROLE_KEEP["desc"]:
                keep = sorted(k["x_in_band"])
        if not keep:
            continue
        x0, x1 = int(keep[0]), int(keep[1])
        ivs = {int(k2): tuple(float(a) for a in v)
               for k2, v in cache[stem]["ivs"].items()}
        gray = cv2.imread(str(paths.RAW_DIR / f"{stem}.JPG"),
                          cv2.IMREAD_GRAYSCALE)
        W, H = gray.shape[1], gray.shape[0]
        byrow = {e["行"]: e for e in cells + prov
                 if e["stem"] == stem}
        for r in rows_:
            e = byrow[r]
            if r - 2 not in ivs:
                continue
            y0, y1 = (int(v) for v in ivs[r - 2])
            win = crop_window(gray, x0, x1, y0, y1, pad_l=8, pad_r=8)
            strip = gray[max(0, y0 - MY):min(H, y1 + MY),
                         max(0, x0 - 150):min(W, x1 + 150)]
            tag = f"{stem[5:]}_行{r}"
            if win is not None and win.size:
                cv2.imwrite(str(PKG / f"{tag}_cell.png"), win)
            if strip.size:
                cv2.imwrite(str(PKG / f"{tag}_strip.png"), strip)
            verdict = "□现值对 □众读对 □都不对:"
            lines.append(
                f"| {e['_档']} | {stem[5:]}/行{r} | {e['现值n'][:26]} | "
                f"{e['众读n'][:26]} ({e['众读票']}票) | "
                f"{e['次读n'][:16]} ({e['次读票']}) | "
                f"{e['行带读n'][:26] or '∅'} | {verdict} |")
    (PKG / "索引.md").write_text("\n".join(lines), encoding="utf-8")
    n_png = len(list(PKG.glob("*.png")))
    print(f"包完成: 双族{len(cells)}+单族{len(prov)} 格, {n_png} 张裁片 → {PKG}")


if __name__ == "__main__":
    main()
