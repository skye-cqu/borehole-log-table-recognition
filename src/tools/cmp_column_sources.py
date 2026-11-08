# -*- coding: utf-8 -*-
"""列线新旧对照：同一扇窗口，左=交付版(6a segment_ids 现拼)，右=column_fit 轨迹。

一律 1:1 原尺寸裁片，不缩放、不改长宽比（上一版按固定 400x760 resize 把图拉变形了）。
窗口按"宽 x 高"给，两块并排，中间 16px 白缝，顶部 30px 标签条。

用法: python src/tools/cmp_column_sources.py        # 出默认 6 扇窗口
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import cv2
import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.core import paths  # noqa: E402
from src.table.track_columns import load_chain  # noqa: E402

RECON = paths.RUNS_DIR / "table_reconstruct"
LINE = (0, 0, 255)          # BGR 红
JUMP = 20                   # 横向跳 >20px 且 >0.3×纵向 = 一段斜穿（竖线不该有）
TILE = (720, 2000)          # 每扇窗口 宽x高，原图像素，不缩放


def worst_windows(k=8):
    """全量扫一遍交付版列线，取斜穿段最多的 k 条，各截一段最陡处当窗口。"""
    g = {}
    for jpg in sorted(paths.RAW_DIR.glob("钻孔柱状图*.JPG")):
        stem = jpg.stem
        fp = RECON / f"{stem}_列结构定稿.json"
        if not fp.exists():
            continue
        seg = {s["id"]: s for s in json.load(open(
            paths.CANDIDATE_COORD_DIR / f"{stem}.json", encoding="utf-8"))["lines"]}
        for c in json.load(open(fp, encoding="utf-8"))["columns"]:
            P = np.asarray(load_chain(c, seg)[0][:, ::-1], float)      # (x, y)
            cnt, top = 0, None
            for (x0, y0), (x1, y1) in zip(P, P[1:]):
                dx = abs(x1 - x0)
                if dx > JUMP and dx > 0.3 * abs(y1 - y0):
                    cnt += 1
                    if top is None or dx > top[0]:
                        top = (dx, min(y0, y1), min(x0, x1))
            if cnt:
                g[(stem, c["index"])] = (cnt, top[1], top[2])
    g = sorted(g.items(), key=lambda kv: (-kv[1][0], -kv[1][1]))[:k]
    return [(stem, idx, int(max(0, y - 700)), int(y + 1300),
             int(max(0, x - 260)), int(max(0, x - 260)) + TILE[0]) for (stem, idx), (_, y, x) in g]


def sheet(stem):
    return (cv2.imread(str(paths.RAW_DIR / f"{stem}.JPG"), cv2.IMREAD_COLOR),
            {s["id"]: s for s in json.load(open(
                paths.CANDIDATE_COORD_DIR / f"{stem}.json", encoding="utf-8"))["lines"]},
            json.load(open(RECON / f"{stem}_列结构定稿.json", encoding="utf-8")),
            {l["id"]: np.asarray(l["trajectory"], float) for l in
             json.load(open(paths.COLUMN_FIT_COORD_DIR / f"{stem}_column_fit.json",
                            encoding="utf-8"))["column_lines"]},
            json.load(open(paths.COLFIX_MANIFEST, encoding="utf-8"))["每张"][stem])


def panel(img, pts):
    out = img.copy()
    cv2.polylines(out, [np.round(np.asarray(pts, float)).astype(np.int32).reshape(-1, 1, 2)],
                  False, LINE, 3, cv2.LINE_AA)
    return out


def main():
    out_dir = paths.COLFIX_DIR / "对照_1比1"
    out_dir.mkdir(parents=True, exist_ok=True)
    for i, (stem, idx, y0, y1, x0, x1) in enumerate(worst_windows(), 1):
        full, seg, d, fit, mp = sheet(stem)
        col = [c for c in d["columns"] if c["index"] == idx][0]
        left = panel(full, np.asarray(load_chain(col, seg)[0][:, ::-1], float))
        m = [u for u in mp if u["col_index"] == idx][0]
        right = panel(full, fit[m["fit_id"]]) if m["usable"] else full.copy()
        del full
        a, b = left[y0:y1, x0:x1], right[y0:y1, x0:x1]
        h = min(a.shape[0], b.shape[0])
        row = cv2.hconcat([a[:h], np.full((h, 16, 3), 255, np.uint8), b[:h]])
        lab = np.full((30, row.shape[1], 3), 255, np.uint8)
        tag = (f"column_fit({m['fit_id']}/{m['fit_role']})" if m["usable"] else "no match")
        cv2.putText(lab, f"{stem[-4:]} col{idx}  y{y0}-{y1} x{x0}-{x1}  1:1 unscaled  "
                         f"LEFT=mine   RIGHT={tag}",
                    (6, 21), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1, cv2.LINE_AA)
        out = out_dir / f"{i}_{stem[-4:]}_col{idx}.png"
        cv2.imwrite(str(out), np.vstack([lab, row]))
        print(f"{out.name}  {row.shape[1]}x{row.shape[0]}px  1:1 未缩放", flush=True)
    print(f"目录: {out_dir}")


if __name__ == "__main__":
    main()
