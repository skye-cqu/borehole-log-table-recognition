# -*- coding: utf-8 -*-
"""疑漏带核实包(2026-10-05): 148 嫌疑带逐条裁数值区 1:1 裁片,12 带/张拼竖版。
裁片范围 = 表左缘→柱状带西缘(行线判覆盖率的区域),标 注信号/带内sub。"""
import csv
import json
import math
import re
import sys
from pathlib import Path

import cv2
import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))
from src.core import paths  # noqa: E402
from src.table.track_rows import row_y, content_band  # noqa: E402
from PIL import Image, ImageDraw, ImageFont  # noqa: E402

FONT = ImageFont.truetype("C:/Windows/Fonts/msyh.ttc", 17)
OUT = paths.RUNS_DIR / "tmp" / "疑漏带核实_20261005"
OUT.mkdir(parents=True, exist_ok=True)
PER = 12


def main():
    rows = list(csv.reader(open(paths.RUNS_DIR / "tmp" / "疑漏带归因_20261005.csv",
                                encoding="utf-8-sig")))[1:]
    tiles = []
    cache = {}
    for r in rows:
        stem, xr, sig, y0, y1, nsub, subs, noff = r[0], int(r[1]), r[2], int(r[3]), \
            int(r[4]), int(r[5]), r[6], int(r[7])
        if stem not in cache:
            rd = json.load(open(paths.RUNS_DIR / "table_reconstruct" /
                                f"钻孔柱状图{stem}_行判定.json", encoding="utf-8"))
            gray = cv2.imread(str(paths.RAW_DIR / f"钻孔柱状图{stem}.JPG"),
                              cv2.IMREAD_GRAYSCALE)
            W, _, _ = content_band(stem)
            cache[stem] = (rd, gray, W)
        rd, gray, W = cache[stem]
        x_l = rd["table_x"][0] - 25
        if W is not None:
            x_r = float(np.interp((y0 + y1) / 2, W[:, 0], W[:, 1])) + 25
        else:
            x_r = rd["table_x"][1] + 25
        if x_r - x_l < 200:
            x_r = x_l + 400
        crop = gray[max(0, y0 - 10):y1 + 10, int(x_l):int(x_r)]
        h = crop.shape[0]
        if h > 220:
            crop = cv2.resize(crop, (int(crop.shape[1] * 220 / h), 220))
        lab = f"{stem} 行{xr} [{sig}]{' sub@' + subs if nsub else ''}{' off' + str(noff) if noff else ''}"
        tiles.append((crop, lab))

    for si in range(math.ceil(len(tiles) / PER)):
        part = tiles[si * PER:(si + 1) * PER]
        Wc = max(max(c.shape[1] for c, _ in part), 700) + 24
        Hc = sum(min(c.shape[0] + 8, 228) + 26 for c, _ in part) + 10
        img = Image.new("L", (Wc, Hc), 255)
        dr = ImageDraw.Draw(img)
        y = 6
        for crop, lab in part:
            dr.text((10, y), lab, fill=0, font=FONT)
            y += 25
            img.paste(Image.fromarray(crop), (10, y))
            y += crop.shape[0] + 8
        p = OUT / f"包{si+1:02d}.png"
        img.save(p)
        print("→", p, f"{len(part)}带")
    print(f"共 {len(tiles)} 带 / {math.ceil(len(tiles)/PER)} 张")


if __name__ == "__main__":
    main()
