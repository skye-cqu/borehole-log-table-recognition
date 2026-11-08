# -*- coding: utf-8 -*-
"""时代列逐格横排拼图(用户 2026-10-25 拍板):单字识别语义会乱,把每个时代格(名带)里
已切出的字横行紧凑排列拼成一张图,供带上下文的整格识别。

输入 = era_chars.json(ERA_CHAR_DIR 下各图的字块与名带账)
     + 同目录 字_XX_yY.png 裁片。
输出 = 同目录 格_XX_yY0.png(格内各字等高横排、4px 间距,白底)
     + era_chars.json 增写 "cell_images": [{band, name, 判定, y0, y1, file, chars, ocr}]
       (ocr = RapidOCR 对拼图的整格复读,带上下文;幂等可重跑,重跑覆盖)。

用法: python src/tools/era_cell_montage.py [图号...]   (无参数=两个 era 目录全量)
"""
import json
import sys
from pathlib import Path

import cv2
import numpy as np

from src.core import paths, batch

PAD = 4          # 字间距(px,缩放后)
CELL_H = 96      # 拼图统一字高(px)


def _montage_one(chart_dir, stem):
    """一张图:按名带把字横排成格图,回写 era_chars.json 的 cell_images。"""
    f = chart_dir / stem / "era_chars.json"
    d = json.loads(f.read_text(encoding="utf-8"))
    chars, bands = d.get("chars") or [], d.get("bands") or []
    if not chars or not bands:
        return "无字块/名带,跳过"
    # 每个字块载入已落盘裁片(比重裁原图快且口径一致)
    crops = []
    for i, c in enumerate(chars):
        p = chart_dir / stem / f"字_{i:02d}_y{c['y0']}.png"
        img = cv2.imread(str(p), cv2.IMREAD_GRAYSCALE)
        crops.append((c, img))
    from rapidocr_onnxruntime import RapidOCR
    ocr = RapidOCR(intra_op_num_threads=1)  # 默认满核线程在多进程池里互踩,实测慢 12 倍
    cell_images = []
    for bi, b in enumerate(bands):
        members = [(c, img) for c, img in crops
                   if img is not None and b["y0"] <= (c["y0"] + c["y1"]) / 2 <= b["y1"]]
        if not members:
            continue
        tiles = []
        for c, img in members:
            h = CELL_H
            w = max(2, int(round(img.shape[1] * h / img.shape[0])))
            tiles.append(cv2.resize(img, (w, h), interpolation=cv2.INTER_AREA))
        gap = np.full((CELL_H, PAD), 255, np.uint8)
        row = tiles[0]
        for t in tiles[1:]:
            row = np.hstack([row, gap, t])
        name = f"格_{bi:02d}_y{int(b['y0'])}.png"
        cv2.imwrite(str(chart_dir / stem / name), row)
        res, _ = ocr(row)
        cell_images.append({
            "band": bi, "name": b.get("name"), "判定": b.get("判定"),
            "y0": int(b["y0"]), "y1": int(b["y1"]), "file": name,
            "chars": [int(chars.index(c)) if c in chars else None for c, _ in members],
            "ocr": " ".join(r[1] for r in (res or [])).strip(),
        })
    d["cell_images"] = cell_images
    f.write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8")
    return f"格 {len(cell_images)} 张: " + " | ".join(
        f"{c['name'] or '∅'}→{c['ocr'] or '∅'}" for c in cell_images)


def worker(payload):
    """batch.run_batch 约定:返回 (name, ok, info)。"""
    chart_dir, stem = payload
    try:
        return stem, True, _montage_one(chart_dir, stem)
    except Exception as e:  # noqa: BLE001
        return stem, False, f"{type(e).__name__}: {e}"


def main():
    dirs = [d for d in (paths.ERA_CHAR_DIR,) if d.exists()]
    want = {_stem(s) for s in sys.argv[1:]}
    items = [(d, p.name) for d in dirs for p in sorted(d.iterdir())
             if p.is_dir() and (p / "era_chars.json").exists()
             and (not want or p.name in want)]
    if want:
        miss = want - {s for _, s in items}
        if miss:
            print(f"未见 era_chars.json: {sorted(miss)}")
    results = batch.run_batch(items, worker, max_workers=6)
    bad = [r for _, ok, info in results if not ok for r in [info]]
    n_cells = sum(len(json.loads((d / s / "era_chars.json").read_text(
        encoding="utf-8")).get("cell_images") or []) for d, s in items)
    print(f"--- {len(items)} 图,格图共 {n_cells} 张" + (f";FAIL {bad}" if bad else ""))
    return 1 if bad else 0


def _stem(num):
    return num if num.startswith("钻孔柱状图") else f"钻孔柱状图{num}"


if __name__ == "__main__":
    sys.exit(main())
