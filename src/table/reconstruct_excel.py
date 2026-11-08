# -*- coding: utf-8 -*-
"""阶段6 (d)+(e)：网格单元格 → OCR 逐格识别 → Excel 还原。

网格：列 = 表头映射的保留列（边界=分隔线链，按行带插值取 x）；
     行 = track_rows 的层界折线（按该格横向位置在折线上取 y，与列方向对称）；
         岩性描述列每层一格（子行文本合并）。
文本：单元格裁小图 → RapidOCR（当前环境已装；MinerU 不在本环境，
     管线在 OCR 步骤模块化，可后续换 MinerU 逐格后端）。
Excel：openpyxl，一图一 sheet，保留 8 列（地质时代..真厚、岩性描述），
      删除柱状/简易水文曲线；纯数字转 float。输出 runs/table_reconstruct/。
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import cv2
import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.core import paths  # noqa: E402
from src.table.track_rows import row_y  # noqa: E402

NUM_RE = re.compile(r"^-?\d+(\.\d+)?$")


def _crop_cell(gray, top, bot, bx_l, bx_r, x0, x1, y0, y1, pad=3, margin=40):
    """逐格裁片:四边界各按折线逐像素取,不再用中心标量的直线矩形。

    列界折线在每行 y 取 x(可倾斜/弯曲),行界折线在每列 x 取 y;界内 pad px 收进
    (不把界线墨喂给 OCR),搜索窗=粗框(x0/x1/y0/y1,中心标量口径)外扩 margin;
    行界折线出窗口取近端点值不外推(1035 缺陷守卫);界外像素一律置白。
    """
    H, W = gray.shape
    xa, xb = max(0, int(x0) - margin), min(W, int(x1) + margin)
    ya, yb = max(0, int(y0) - margin), min(H, int(y1) + margin)
    if xb - xa < 8 or yb - ya < 8:
        return None
    xs = np.arange(xa, xb, dtype=float)
    ys = np.arange(ya, yb, dtype=float)
    xl = np.asarray(bx_l(ys), float)                   # 列界逐行(图缘时为标量→广播)
    xr = np.asarray(bx_r(ys), float)
    if xl.ndim == 0:
        xl = np.full(ys.size, float(xl))
    if xr.ndim == 0:
        xr = np.full(ys.size, float(xr))
    pt, pb = np.asarray(top["poly"], float), np.asarray(bot["poly"], float)
    yt = np.interp(np.clip(xs, pt[0, 0], pt[-1, 0]), pt[:, 0], pt[:, 1])
    ybt = np.interp(np.clip(xs, pb[0, 0], pb[-1, 0]), pb[:, 0], pb[:, 1])
    inside = ((xs[None, :] >= xl[:, None] + pad) & (xs[None, :] <= xr[:, None] - pad)
              & (ys[:, None] >= yt[None, :] + pad) & (ys[:, None] <= ybt[None, :] - pad))
    if not inside.any():
        return None
    crop = gray[ya:yb, xa:xb].copy()
    crop[~inside] = 255
    return crop


def build_cells(stem: str):
    """返回 (sheet_rows, meta)：sheet_rows = [[列名...], [行...]]，meta 含格数等。"""
    hm = json.load(open(paths.RUNS_DIR / "table_reconstruct" / f"{stem}_表头映射.json",
                        encoding="utf-8"))
    rd = json.load(open(paths.RUNS_DIR / "table_reconstruct" / f"{stem}_行判定.json",
                        encoding="utf-8"))
    keep = hm["keep"]
    v3 = hm.get("sep_pts") or None
    # track 数据源(stage5_track_grouping)已按 EXPERIMENT.md 定案退役;
    # 现口径一律走 hm["sep_pts"](_分割线 P10 真段),旧映射缺 sep_pts 即报错重跑 6b。
    if not v3:
        return None, {"error": "映射无 sep_pts(track 旧口径已退役),该图需重跑 6b 表头映射"}

    def _bound_x(i, y, edge):
        """边界 x:v3=sep_pts 真段插值(单一真源 _分割线);i<0=图左/右缘。y 可为数组。"""
        if i is None or i < 0:
            return edge
        b = v3[i]
        r = np.interp(y, b["ys"], b["xs"])
        return r if np.ndim(r) else float(r)
    # 层界 = 折线；先用表中线高筛掉表头底界之上的线（顶框/表头内线），层从其下开始
    x_tbl = sum(rd["table_x"]) / 2
    rows_r = [r for r in rd["rows"] if row_y(r, x_tbl) >= hm["band"][1]]
    # 行界需覆盖整个数据区：顶=表头底界（首条主行线即表头底），底=最后一条主行线
    if len(rows_r) < 2:
        return None, {"error": "主行线不足"}

    gray = cv2.imread(str(paths.RAW_DIR / f"{stem}.JPG"), cv2.IMREAD_GRAYSCALE)
    from rapidocr_onnxruntime import RapidOCR
    ocr = RapidOCR(intra_op_num_threads=1)  # 默认满核线程在多进程池里互踩,实测慢 12 倍

    header = [c["name"] for c in keep]
    table = []
    n_cells = n_text = 0
    for li in range(len(rows_r) - 1):
        top, bot = rows_r[li], rows_r[li + 1]
        y_mid = (row_y(top, x_tbl) + row_y(bot, x_tbl)) / 2
        out_row = []
        for c in keep:
            x0 = _bound_x(c["left_sep"], y_mid, 0.0)
            x1 = _bound_x(c["right_sep"], y_mid, float(gray.shape[1]))
            xc = (x0 + x1) / 2
            y0c, y1c = row_y(top, xc), row_y(bot, xc)
            if max(x0, x1) - min(x0, x1) < 8 or y1c - y0c < 8:
                out_row.append("")
                continue
            crop = _crop_cell(
                gray, top, bot,
                lambda y, i=c["left_sep"]: _bound_x(i, y, 0.0),
                lambda y, i=c["right_sep"]: _bound_x(i, y, float(gray.shape[1])),
                x0, x1, y0c, y1c)
            if crop is None:
                out_row.append("")
                continue
            res, _ = ocr(crop)
            n_cells += 1
            texts = [r[1] for r in (res or [])]
            text = " ".join(texts).strip()
            if text:
                n_text += 1
            m = NUM_RE.match(text)
            out_row.append(float(text) if m else text)
        table.append(out_row)
    meta = {"image": stem, "header": header, "n_layers": len(table),
            "n_cells": n_cells, "n_text_cells": n_text}
    return [header] + table, meta


def to_excel(stem, sheet, out_dir=None):
    """出一份表。out_dir 默认写 runs/table_reconstruct/（旧行为），重出新行界时传对应 REEMIT_DIR_* 注册目录。"""
    from openpyxl import Workbook
    wb = Workbook()
    ws = wb.active
    ws.title = stem.replace("钻孔柱状图", "")
    for row in sheet:
        ws.append(row)
    out = (out_dir or paths.RUNS_DIR / "table_reconstruct")
    out.mkdir(parents=True, exist_ok=True)
    out = out / f"{stem}_还原.xlsx"
    wb.save(out)
    return out


def main():
    stems = sys.argv[1:] or ["钻孔柱状图1019"]
    for stem in stems:
        sheet, meta = build_cells(stem)
        if sheet is None:
            print(stem, "FAIL", meta)
            continue
        # 裸跑禁止写正式表目录(runs/table_reconstruct 存人工判读),一律进重出目录
        p = to_excel(stem, sheet, paths.REEMIT_DIR_20261023)
        print(f"{stem}: 层 {meta['n_layers']} 格 {meta['n_cells']} "
              f"有字格 {meta['n_text_cells']} → {p.name}")


if __name__ == "__main__":
    main()
