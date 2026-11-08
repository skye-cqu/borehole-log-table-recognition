# -*- coding: utf-8 -*-
"""组装时代列整字裁剪核验包 → outputs/时代列整字裁剪核验_20261010/(用户肉眼核验用,约束7)。

内容:每图 montage 拼段版(长条带切 8 段横排,肉眼可读)+ 原始 montage + 整字裁片/
+ era_chars.json + 门禁报告 CSV/JSON + 说明.md。
用法: python runs/tmp/组装时代列核验包_20261010.py
"""
import json
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import cv2
import numpy as np

from src.core.paths import ERA_CHAR_DIR, OUTPUTS_DIR, RUNS_DIR, TMP_DIR

OUT = OUTPUTS_DIR / "时代列整字裁剪核验_20261010"
CHARTS = ["1016", "1022", "1026", "1036", "1040"]


def montage_grid(src: Path, dst: Path, n=8):
    m = cv2.imread(str(src))
    h, w = m.shape[:2]
    ch = (h + n - 1) // n
    cols = []
    for i in range(n):
        c = m[i * ch:(i + 1) * ch]
        if c.shape[0] < ch:
            c = np.vstack([c, np.full((ch - c.shape[0], w, 3), 255, np.uint8)])
        cols.append(np.vstack([c, np.full((3, w, 3), 120, np.uint8)]))
    cv2.imwrite(str(dst), np.hstack(cols))


def main():
    for num in CHARTS:
        stem = f"钻孔柱状图{num}"
        d = ERA_CHAR_DIR / stem
        od = OUT / stem
        od.mkdir(parents=True, exist_ok=True)
        montage_grid(d / "montage.png", od / "montage_拼段.png")
        shutil.copy(d / "montage.png", od / "montage_原始.png")
        cp = od / "整字裁片"
        if cp.exists():
            shutil.rmtree(cp)
        shutil.copytree(d, cp)               # 裁片 PNG + era_chars.json
        print(stem, "->", od)
    rep = OUT / "门禁报告"
    rep.mkdir(exist_ok=True)
    for f in ["时代列门禁_20261010.csv", "时代列门禁_20261010.json",
              "时代列门禁基线_20261010.csv", "时代列门禁基线_20261010.json",
              "时代列前置体检_20261010.csv"]:
        if (TMP_DIR / f).exists():
            shutil.copy(TMP_DIR / f, rep / f)
    print("报告 ->", rep)


if __name__ == "__main__":
    main()
