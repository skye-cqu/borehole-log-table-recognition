# -*- coding: utf-8 -*-
"""交付表文字/格位置抽查裁片: 时代列前8行 + 其余列有字格8 + 空格4, 拼竖版标注图。
表值=交付xlsx内容, 裁片=按同一套 _crop_cell 从原图裁出, 供(弱档)比对 OCR 对错与空格是否真空。"""
import json, random, sys
from pathlib import Path

import cv2
import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))
from src.core import paths  # noqa: E402
from src.table.reconstruct_excel import _crop_cell  # noqa: E402
from src.table.track_rows import row_y  # noqa: E402
from PIL import Image, ImageDraw, ImageFont  # noqa: E402

FONT = ImageFont.truetype("C:/Windows/Fonts/msyh.ttc", 18)
OUT = paths.RUNS_DIR / "tmp" / "文字抽查_20261005"
OUT.mkdir(parents=True, exist_ok=True)


def bound_x_fn(hm):
    v3 = hm.get("sep_pts") or None

    def bx(i, y, edge):
        if i is None or i < 0:
            return edge
        if v3:
            b = v3[i]
            r = np.interp(y, b["ys"], b["xs"])
            return r if np.ndim(r) else float(r)
        return edge
    return bx


for stem in ["钻孔柱状图1015", "钻孔柱状图1027", "钻孔柱状图1042"]:
    s = stem[-4:]
    hm = json.load(open(paths.RUNS_DIR / "table_reconstruct" / f"{stem}_表头映射.json",
                        encoding="utf-8"))
    rd = json.load(open(paths.RUNS_DIR / "table_reconstruct" / f"{stem}_行判定.json",
                        encoding="utf-8"))
    keep = hm["keep"]
    bx = bound_x_fn(hm)
    x_tbl = sum(rd["table_x"]) / 2
    rows_r = [r for r in rd["rows"] if row_y(r, x_tbl) >= hm["band"][1]]
    gray = cv2.imread(str(paths.RAW_DIR / f"{stem}.JPG"), cv2.IMREAD_GRAYSCALE)
    from openpyxl import load_workbook
    ws = load_workbook(str(paths.REEMIT_DIR_20261005 / f"{stem}_还原.xlsx")).active
    vals = [[c.value for c in row] for row in ws.iter_rows()]
    assert len(rows_r) - 1 == len(vals) - 1, (stem, len(rows_r), len(vals))

    picks = [(d, 0) for d in range(min(8, len(vals) - 1))]          # 时代列前8行
    random.seed(7)
    filled = [(d, ci) for d in range(len(vals) - 1)
              for ci in range(1, len(vals[0])) if str(vals[d + 1][ci]).strip()]
    picks += random.sample(filled, min(8, len(filled)))
    empty = [(d, ci) for d in range(len(vals) - 1)
             for ci in range(len(vals[0])) if not str(vals[d + 1][ci]).strip()]
    picks += random.sample(empty, min(4, len(empty)))

    tiles = []
    for d, ci in picks:
        c = keep[ci]
        top, bot = rows_r[d], rows_r[d + 1]
        y_mid = (row_y(top, x_tbl) + row_y(bot, x_tbl)) / 2
        x0 = bx(c["left_sep"], y_mid, 0.0)
        x1 = bx(c["right_sep"], y_mid, float(gray.shape[1]))
        xc = (x0 + x1) / 2
        y0c, y1c = row_y(top, xc), row_y(bot, xc)
        crop = _crop_cell(gray, top, bot,
                          lambda y, i=c["left_sep"]: bx(i, y, 0.0),
                          lambda y, i=c["right_sep"]: bx(i, y, float(gray.shape[1])),
                          x0, x1, y0c, y1c)
        lab = f"行{d+1} {c['name']} 表值={vals[d+1][ci]!r}"
        if crop is None:
            tiles.append((None, lab))
            continue
        ys_, xs_ = np.where(crop < 230)
        if ys_.size:
            y_a, y_b = max(0, ys_.min() - 5), min(crop.shape[0], ys_.max() + 6)
            x_a, x_b = max(0, xs_.min() - 5), min(crop.shape[1], xs_.max() + 6)
            crop = crop[y_a:y_b, x_a:x_b]
        if crop.shape[1] > 1100:                    # 只压超宽的,竖条一律原尺寸
            crop = cv2.resize(crop, (1100, int(crop.shape[0] * 1100 / crop.shape[1])))
        tiles.append((crop, lab))

    W = max((t[0].shape[1] if t[0] is not None else 400) for t in tiles) + 30
    H = sum((t[0].shape[0] if t[0] is not None else 26) + 34 for t in tiles) + 12
    W = max(W, 760)
    img = Image.new("L", (W, H), 255)
    dr = ImageDraw.Draw(img)
    y = 8
    for crop, lab in tiles:
        dr.text((10, y), lab, fill=0, font=FONT)
        y += 28
        if crop is not None:
            img.paste(Image.fromarray(crop), (10, y))
            y += crop.shape[0] + 6
        else:
            dr.text((30, y), "[裁片None]", fill=128, font=FONT)
            y += 26
    p = OUT / f"{s}_抽查.png"
    img.save(p)
    print("→", p, f"{len(tiles)}格")
