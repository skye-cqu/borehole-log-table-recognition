# -*- coding: utf-8 -*-
"""裁片真相(2026-10-28):两缺陷代表格的当前窗口裁片 vs 加余量变体 vs 原图标线图。
desc: 1016 带120-130(d132=石灰岩案/140煤案) + 1018 行2(表士残句案)
dip : 1017 行46 / 1018 行8,20,28 / 1019 行28
每格三张: v0=现窗口(_crop_cell 同口径)  v1=底+外延16px(不遮界外)  raw=原窗+线标红
"""
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

import cv2  # noqa: E402
import numpy as np  # noqa: E402

from src.core import paths  # noqa: E402
from src.table.reconstruct_excel import _crop_cell  # noqa: E402
from src.table.track_rows import row_y  # noqa: E402

OUTD = paths.RUNS_DIR / "tmp" / "diag_win"
EXT = 16


def geom(stem):
    hm = paths.RUNS_DIR / "table_reconstruct" / f"{stem}_表头映射.json"
    hm = hm if hm.exists() else None
    import json
    hmj = json.load(open(paths.RUNS_DIR / "table_reconstruct" / f"{stem}_表头映射.json", encoding="utf-8"))
    rdj = json.load(open(paths.RUNS_DIR / "table_reconstruct" / f"{stem}_行判定.json", encoding="utf-8"))
    keep, v3 = hmj["keep"], hmj["sep_pts"]
    rd = rdj
    x_tbl = sum(rd["table_x"]) / 2
    rows_r = [r for r in rd["rows"] if row_y(r, x_tbl) >= hmj["band"][1]]
    return keep, v3, rows_r, rd


def bound_x(v3, i, y, edge):
    if i is None or i < 0:
        return edge
    b = v3[i]
    r = np.interp(y, b["ys"], b["xs"])
    return r if np.ndim(r) else float(r)


def dump(stem, band_idx, tag, colname=None):
    """裁带 band_idx(=行判定带号,还原xlsx行=band_idx+2)。colname=None 裁全宽。"""
    keep, v3, rows_r, rd = geom(stem)
    gray = cv2.imread(str(paths.RAW_DIR / f"{stem}.JPG"), cv2.IMREAD_GRAYSCALE)
    top, bot = rows_r[band_idx], rows_r[band_idx + 1]
    x_tbl = sum(rd["table_x"]) / 2
    y_mid = (row_y(top, x_tbl) + row_y(bot, x_tbl)) / 2
    ci = None
    if colname:
        ci = next((j for j, c in enumerate(keep) if colname in c.get("name", "")), None)
        if ci is None:
            print(f"{stem} 找不到列 {colname}: {[c.get('name') for c in keep]}")
            return
    cols = [ci] if ci is not None else range(len(keep))
    for j in cols:
        x0 = bound_x(v3, keep[j]["left_sep"], y_mid, 0.0)
        x1 = bound_x(v3, keep[j]["right_sep"], y_mid, float(gray.shape[1]))
        xc = (x0 + x1) / 2
        y0c, y1c = row_y(top, xc), row_y(bot, xc)
        crop = _crop_cell(gray, top, bot,
                          lambda y, i=keep[j]["left_sep"]: bound_x(v3, i, y, 0.0),
                          lambda y, i=keep[j]["right_sep"]: bound_x(v3, i, y, float(gray.shape[1])),
                          x0, x1, y0c, y1c)
        if crop is None:
            print(f"band{band_idx} col{j}: crop None")
            continue
        nm = f"{stem[-4:]}_b{band_idx:03d}_c{j}_{tag}"
        cv2.imwrite(str(OUTD / f"{nm}_v0现窗.png"), crop)
        # v1: 底部外延 EXT px,界外不遮(只保留原 inside 遮到 ybt,再放开底)
        ya, yb = max(0, int(y0c) - 40), min(gray.shape[0], int(y1c) + EXT)
        xa, xb = max(0, int(x0) - 40), min(gray.shape[1], int(x1) + 40)
        ys2 = np.arange(ya, yb, dtype=float)
        xl = np.asarray([bound_x(v3, keep[j]["left_sep"], y, 0.0) for y in ys2], float)
        xr = np.asarray([bound_x(v3, keep[j]["right_sep"], y, float(gray.shape[1])) for y in ys2], float)
        pt, pb = np.asarray(top["poly"], float), np.asarray(bot["poly"], float)
        ybt = np.interp(np.clip(np.arange(xa, xb, dtype=float), pb[0, 0], pb[-1, 0]), pb[:, 0], pb[:, 1])
        inside2 = ((np.arange(xa, xb, dtype=float)[None, :] >= xl[:, None] + 3)
                   & (np.arange(xa, xb, dtype=float)[None, :] <= xr[:, None] - 3)
                   & (ys2[:, None] >= np.interp(np.clip(np.arange(xa, xb, dtype=float), pt[0, 0], pt[-1, 0]), pt[:, 0], pt[:, 1])[None, :] + 3))
        crop2 = gray[ya:yb, xa:xb].copy()
        crop2[~inside2] = 255
        cv2.imwrite(str(OUTD / f"{nm}_v1底延.png"), crop2)


def main():
    OUTD.mkdir(parents=True, exist_ok=True)
    # desc 1016: 行126(d124) 带=124..? 直接裁带 122..128 全宽降采样太大 → 只裁 desc 列
    for b in range(122, 129):
        dump("钻孔柱状图1016", b, "desc", "岩性")
    dump("钻孔柱状图1018", 0, "desc", "岩性")       # 行2 表士案(带0)
    # dip: 需带号。1017 行46→d44, 带≈44;1018 行8→d6, 行20→d18, 行28→d26;1019 行28→d26
    dump("钻孔柱状图1017", 44, "dip", "倾角")
    dump("钻孔柱状图1018", 6, "dip", "倾角")
    dump("钻孔柱状图1018", 18, "dip", "倾角")
    dump("钻孔柱状图1018", 26, "dip", "倾角")
    dump("钻孔柱状图1019", 26, "dip", "倾角")
    print("→", OUTD)


if __name__ == "__main__":
    main()
