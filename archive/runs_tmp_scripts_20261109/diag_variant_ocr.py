# -*- coding: utf-8 -*-
"""变体OCR实测(2026-11-03,约束9 选参靠数据):
格集: 69 desc补录格(裁决"采Agnes成句") + 47 dip含杂格(裁决"倾角词表"应用)
     + 对照格(同图同列,现窗读数非空且>=4字/纯数值,各取最多40格/图)
变体: v0=现窗(pad=3双向收进)  e10/e16=纵向底越线10/16px(顶不越)
     e10t/e16t=纵双向越线(顶底都越)   p6/p9/p12=横向pad加大(纵向同v0)
     e16+p9=组合
产出: runs/tmp/diag_variant_ocr.json + 摘要打印(缺陷格修复率/对照格劣化率)
判定: desc修复=Agnes成句的关键词在变体读数中出现(字符重合率>0.6)
     dip修复=变体读数为纯数值(可带°);劣化=对照格读数明显变差(长度/纯度)
"""
import json
import re
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

import cv2  # noqa: E402
import numpy as np  # noqa: E402

from src.core import paths  # noqa: E402
from src.table.agnes_era_blocks import OUT, chart_rows, _bound_span  # noqa: E402
from src.table.track_rows import row_y  # noqa: E402
from openpyxl import load_workbook  # noqa: E402
from rapidocr_onnxruntime import RapidOCR  # noqa: E402

EXTS = ("e10", "e16", "e10t", "e16t")
PADS = ("p6", "p9", "p12")
NUMRE = re.compile(r"^-?\d+(\.\d+)?°?$")


def bnd(bmap, p, step):
    while 0 <= p < len(bmap) and bmap[p] is None:
        p += step
    return bmap[p] if 0 <= p < len(bmap) else None


def crop_var(g, gray, bi, c, variant):
    """带 bi(行判定带号)、keep 列 c,按 variant 裁片。复刻 _crop_cell 几何。"""
    rows_r, hm = g["rows_r"], g["hm"]
    sep = hm["sep_pts"]
    keep = hm["keep"]
    if not (0 <= bi < len(rows_r) - 1) or c >= len(keep):
        return None
    top, bot = rows_r[bi], rows_r[bi + 1]
    kk = keep[c]
    H, W = gray.shape
    # 粗框:列界在中点y,行界在列中心x(与 build_cells 同口径)
    y_mid = (row_y(top, sum(g["rd"]["table_x"]) / 2) + row_y(bot, sum(g["rd"]["table_x"]) / 2)) / 2

    def bx(i, y, edge):
        if i is None or i < 0:
            return edge
        b = sep[i]
        return float(np.interp(y, b["ys"], b["xs"]))

    x0 = bx(kk.get("left_sep"), y_mid, 0.0)
    x1 = bx(kk.get("right_sep"), y_mid, float(W))
    xc = (x0 + x1) / 2
    y0c, y1c = row_y(top, xc), row_y(bot, xc)
    pad_x, ext_t, ext_b = 3, 0, 0
    if variant in PADS:
        pad_x = int(variant[1:])
    if variant[:3] in ("e10", "e16"):
        ext_b = int(variant[1:3])
        if variant.endswith("t"):
            ext_t = ext_b
    if variant in ("e16+p9", "e16mp9"):
        pad_x, ext_b = 9, 16
    if variant == "vmp9":
        pad_x = 9
        pad_x, ext_b = 9, 16
    margin = 40
    xa, xb = max(0, int(x0) - margin), min(W, int(x1) + margin)
    ya, yb = max(0, int(y0c) - margin - ext_t), min(H, int(y1c) + margin + ext_b)
    if xb - xa < 8 or yb - ya < 8:
        return None
    xs = np.arange(xa, xb, dtype=float)
    ys = np.arange(ya, yb, dtype=float)
    xl = np.asarray([bx(kk.get("left_sep"), y, 0.0) for y in ys], float)
    xr = np.asarray([bx(kk.get("right_sep"), y, float(W)) for y in ys], float)
    pt, pb = np.asarray(top["poly"], float), np.asarray(bot["poly"], float)
    ytg = np.interp(np.clip(xs, pt[0, 0], pt[-1, 0]), pt[:, 0], pt[:, 1])
    ybg = np.interp(np.clip(xs, pb[0, 0], pb[-1, 0]), pb[:, 0], pb[:, 1])
    inside = ((xs[None, :] >= xl[:, None] + pad_x) & (xs[None, :] <= xr[:, None] - pad_x)
              & (ys[:, None] >= ytg[None, :] + 3 - ext_t)
              & (ys[:, None] <= ybg[None, :] - 3 + ext_b))
    if "m" in variant or "vm" in variant:   # 线墨遮白(δ=4)
        inside &= ~(np.abs(ys[:, None] - ybg[None, :]) <= 4)
    if not inside.any():
        return None
    crop = gray[ya:yb, xa:xb].copy()
    crop[~inside] = 255
    return crop


def main():
    ocr = RapidOCR(intra_op_num_threads=1)
    variants = ["v0", "vm", "vmp9"]
    gcache, grcache = {}, {}

    def G(stem):
        if stem not in gcache:
            gcache[stem] = chart_rows(stem)
            grcache[stem] = cv2.imread(str(paths.RAW_DIR / f"{stem}.JPG"), cv2.IMREAD_GRAYSCALE)
        return gcache[stem], grcache[stem]
    cells = {"desc": [], "dip": []}
    seen = set()
    for vp in sorted(OUT.glob("*/裁决.json")):
        stem = vp.parent.name
        try:
            g = chart_rows(stem)
        except Exception:  # noqa: BLE001
            continue
        bmap, roles = g["bmap"], g["roles"]
        fin = load_workbook(paths.FINALIZE_FULL_DIR / f"{stem}_整合.xlsx")
        xdata = list(fin.active.iter_rows(values_only=True))
        for e in json.loads(vp.read_text(encoding="utf-8")).get("条目", []):
            d = e.get("依据", "")
            k = e["角色"]
            bad = ("采Agnes成句" in d and k == "desc") or ("倾角词表" in d and k == "dip")
            if not bad:
                continue
            di = int(e["行"]) - 2
            c = roles.get(k)
            if c is None:
                continue
            bi = bnd(bmap, di, -1)
            if bi is None:
                continue
            cells[k].append({"stem": stem, "di": di, "bi": bi, "c": c, "type": "bad",
                             "k": k, "agnes": str(e.get("agnes", ""))[:80], "行": e["行"]})
            seen.add((stem, di, k))
    # 对照格:每图每列取前40个非空格
    for vp in sorted(OUT.glob("*/裁决.json")):
        stem = vp.parent.name
        try:
            g = chart_rows(stem)
        except Exception:  # noqa: BLE001
            continue
        bmap, roles = g["bmap"], g["roles"]
        fin = load_workbook(paths.FINALIZE_FULL_DIR / f"{stem}_整合.xlsx")
        xdata = list(fin.active.iter_rows(values_only=True))
        for k in ("dip",):
            c = roles.get(k)
            n = 0
            for di in range(len(bmap) - 1):
                if n >= 3:
                    break
                if (stem, di, k) in seen or di not in [x["di"] for x in cells[k] if x["stem"] == stem] and False:
                    continue
                bi = bnd(bmap, di, -1)
                if bi is None:
                    continue
                row = xdata[di + 1] if di + 1 < len(xdata) else ()
                v = str(row[c]) if len(row) > c and row[c] is not None else ""
                if k == "desc" and len(v) >= 4 and n < 999:
                    n += 1
                    cells[k].append({"stem": stem, "di": di, "bi": bi, "c": c, "type": "ctrl",
                                     "k": k, "agnes": "", "行": di + 2})
                elif k == "dip" and NUMRE.match(v):
                    n += 1
                    cells[k].append({"stem": stem, "di": di, "bi": bi, "c": c, "type": "ctrl",
                                     "k": k, "agnes": "", "行": di + 2})
    res = []
    for k in ("dip",):
        for cell in cells[k]:
            stem = cell["stem"]
            g, gray = G(stem)
            readings = {}
            for v in variants:
                crop = crop_var(g, gray, cell["bi"], cell["c"], v)
                if crop is None:
                    readings[v] = None
                    continue
                out, _ = ocr(crop)
                readings[v] = " ".join(r[1] for r in (out or [])).strip()
            res.append({**cell, "读": readings})
            print(f"{k} {stem[-4:]} 行{cell['行']} {cell['type']}: "
                  + " | ".join(f"{v}={str(readings[v])[:18]}" for v in variants), flush=True)
    p = paths.RUNS_DIR / "tmp" / "diag_variant_ocr.json"
    p.write_text(json.dumps({"variants": variants, "cells": res}, ensure_ascii=False), encoding="utf-8")
    print("→", p)


if __name__ == "__main__":
    main()
