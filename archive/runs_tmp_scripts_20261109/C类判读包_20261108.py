# -*- coding: utf-8 -*-
"""C类池(858格)判读包生成:单元格裁窗+行带窗 裁片 + 分批分派 + 索引。

包 = runs/autoresearch_align/多源定级_20261106/C类判读包_20261108/
  {tag}_cell.png / {tag}_strip.png + 分派_C类_{i}.json + 索引.md。
裁片几何与 build_review_pkg(98格包)同款:desc 列 x界 × 行带 y界,strip ±150/±8。
分派增强:众读/次读/行带读 + 桶(1-2字差/3-5字差/大段差) + 偏向(众读偏我方/偏参考/无读)。
"""
import json
import sys
from collections import Counter
from difflib import SequenceMatcher
from pathlib import Path

sys.path.insert(0, r"D:\Skye\Documents\Work\高维智矿\7.13杂活")
import cv2  # noqa: E402

from src.core import paths  # noqa: E402
from src.handwriting.cellcrop import crop_window  # noqa: E402
from src.handwriting.normalizers import norm_desc  # noqa: E402
from src.handwriting.reread import ROLE_KEEP  # noqa: E402

OD = paths.AUTORESEARCH_DIR / "多源定级_20261106"
PKG = OD / "C类判读包_20261108"
MY = 8
CAP = 15  # 每批格数


def bucket(cand, ref):
    d = abs(len(norm_desc(cand)) - len(norm_desc(ref)))
    if d <= 2:
        return "1-2字差"
    if d <= 5:
        return "3-5字差"
    return "大段差"


def lean(众读, cand, ref):
    if not 众读:
        return "无读"
    sc, sr = (SequenceMatcher(None, 众读, norm_desc(x)).ratio() for x in (cand, ref))
    if abs(sc - sr) < 0.02:
        return "居中"
    return "偏我方" if sc > sr else "偏参考"


def main():
    pool = json.loads((OD / "C类池_重推_20261108.json").read_text(encoding="utf-8"))
    cells = {(c["stem"], c["行"]): c for c in
             json.loads((OD / "定级.json").read_text(encoding="utf-8"))["cells"]}
    cache = json.loads(paths.AUTORESEARCH_ROWCACHE.read_text(encoding="utf-8"))
    PKG.mkdir(exist_ok=True)

    items, skip = [], []
    for e in pool:
        stem, r = e["stem"], e["row"]
        ivs = {int(k): v for k, v in cache.get(stem, {}).get("ivs", {}).items()}
        if r - 2 not in ivs:
            skip.append(f"{e['tag']}: 无行带几何")
            continue
        keep = None
        hm = paths.RUNS_DIR / "table_reconstruct" / f"{stem}_表头映射.json"
        for k in json.loads(hm.read_text(encoding="utf-8"))["keep"]:
            if k["name"] == ROLE_KEEP["desc"]:
                keep = sorted(k["x_in_band"])
        if not keep:
            skip.append(f"{e['tag']}: 无desc列几何")
            continue
        g = cells.get((stem, r), {})
        众, 次, 带 = g.get("众读n", ""), g.get("次读n", ""), g.get("行带读n", "")
        x0, x1 = int(keep[0]), int(keep[1])
        y0, y1 = (int(v) for v in ivs[r - 2])
        gray = cv2.imread(str(paths.RAW_DIR / f"{stem}.JPG"), cv2.IMREAD_GRAYSCALE)
        H, W = gray.shape[:2]
        win = crop_window(gray, x0, x1, y0, y1, pad_l=8, pad_r=8)
        strip = gray[max(0, y0 - MY):min(H, y1 + MY),
                     max(0, x0 - 150):min(W, x1 + 150)]
        if win is None or not win.size or not strip.size:
            skip.append(f"{e['tag']}: 空裁片")
            continue
        cv2.imwrite(str(PKG / f"{e['tag']}_cell.png"), win)
        cv2.imwrite(str(PKG / f"{e['tag']}_strip.png"), strip)
        items.append({
            "tag": e["tag"],
            "cell": f"{PKG.relative_to(paths.PROJECT_ROOT).as_posix()}/{e['tag']}_cell.png",
            "strip": f"{PKG.relative_to(paths.PROJECT_ROOT).as_posix()}/{e['tag']}_strip.png",
            "桶": bucket(e["cand"], e["ref"]),
            "偏向": lean(众, e["cand"], e["ref"]),
            "现值": e["cand"], "参考": e["ref"],
            "众读": 众, "众读票": g.get("众读票", 0),
            "次读": 次, "次读票": g.get("次读票", 0),
            "行带读": 带, "级": g.get("级", ""),
        })

    items.sort(key=lambda x: (x["tag"].split("_行")[0], int(x["tag"].split("_行")[1])))
    nb = 0
    for i in range(0, len(items), CAP):
        chunk = items[i:i + CAP]
        (PKG / f"分派_C类_{nb}.json").write_text(
            json.dumps(chunk, ensure_ascii=False, indent=1), encoding="utf-8")
        nb += 1

    cb, cl = Counter(x["桶"] for x in items), Counter(x["偏向"] for x in items)
    cf = Counter(x["tag"].split("_行")[0] for x in items)
    md = ["# C类池判读包(2026-11-08,弱档·助手视觉判读用户授权)", "",
          f"- 池 {len(pool)} 格(候选≠参考、双方非空、剔98定谳格);出裁片 {len(items)} 格,跳过 {len(skip)}",
          f"- 桶: {dict(cb)};偏向: {dict(cl)}",
          f"- 分派 {nb} 批 × ≤{CAP} 格;判定三选一: 现值对/参考对/都不对,text=纸面忠实转写",
          f"- 按图分布: {dict(sorted(cf.items()))}"]
    if skip:
        md += ["", "## 跳过"] + [f"- {s}" for s in skip]
    (PKG / "索引.md").write_text("\n".join(md), encoding="utf-8")
    print(f"包 {len(items)} 格 / {nb} 批,跳过 {len(skip)};桶 {dict(cb)};偏向 {dict(cl)}")
    print(f"-> {PKG}")
    for s in skip:
        print("  SKIP", s)


if __name__ == "__main__":
    main()
