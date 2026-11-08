# -*- coding: utf-8 -*-
"""列线核验：几何一律取阶段4 column_fit 的 column_lines[].trajectory，出叠加图给人肉眼判。

为什么是它：6a 定稿 JSON 只存 segment_ids（哪些碎片属于这条列），不存坐标；出表时我用
load_chain 把碎片端点按 y 排序再逐段直线连，断口处就斜着穿到邻线上（实测 1042/1024/1019/1033
每张两条，斜穿 169 段）。column_fit 的 trajectory 是逐 y 连续的实测轨迹（30 张全有，
每条 ~850-1080 点，相邻点 y 间隔恒为 30px，无一处断档），不存在"凭两端点连线"这一步。

产物：全分辨率叠加图 + 分段预览 + 定稿对应表 + 线级 CSV。只读，不回写任何判定产物。
颜色：蓝=列分隔线(separator) 橙=柱状带内图案边线(internal，不作列线) 绿=外框(frame/wrap)。

用法: python src/tools/emit_column_overlay.py [1019 1042]   # 无参数=30 张
"""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

import cv2
import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.core import paths  # noqa: E402

SEP, INT, FRAME = "separator", "internal", ("frame", "wrap")
SEP_COL, INT_COL, FRAME_COL = (255, 90, 0), (0, 165, 255), (0, 200, 0)
TILE_H = 3600          # 预览每段原图高(px)
TILE_W = 1500          # 预览段缩放后宽(px)


def load_fit(stem):
    p = paths.COLUMN_FIT_COORD_DIR / f"{stem}_column_fit.json"
    if not p.exists():
        return None
    d = json.load(open(p, encoding="utf-8"))
    for l in d["column_lines"]:
        l["tr"] = np.asarray(l["trajectory"], float)     # (x, y)
    return d


def role_of(l):
    return INT if l["role"] == "internal" else (FRAME if l["role"] in ("frame", "wrap") else SEP)


def draw(stem, d):
    """全分辨率叠加图：每条轨迹按自己的点画，不跨线、不补点。"""
    img = cv2.imread(str(paths.RAW_DIR / f"{stem}.JPG"), cv2.IMREAD_COLOR)
    if img is None:
        return None, None
    for l in d["column_lines"]:
        r = role_of(l)
        col, w = {SEP: (SEP_COL, 3), INT: (INT_COL, 2), FRAME: (FRAME_COL, 2)}[r]
        pts = np.round(l["tr"]).astype(np.int32).reshape(-1, 1, 2)
        cv2.polylines(img, [pts], False, col, w, cv2.LINE_AA)
    return img, d


def tiles(stem, img, out_dir):
    """竖着切成若干段、每段缩到 TILE_W 宽，逐段写 JPG（全分辨率图 3200x20000 没法直接看）。"""
    H = img.shape[0]
    n = max(1, int(np.ceil(H / TILE_H)))
    for i in range(n):
        y0, y1 = i * TILE_H, min(H, (i + 1) * TILE_H)
        s = TILE_W / img.shape[1]
        cv2.imwrite(str(out_dir / f"{stem}_段{i + 1}of{n}.jpg"),
                    cv2.resize(img[y0:y1], None, fx=s, fy=s, interpolation=cv2.INTER_AREA),
                    [cv2.IMWRITE_JPEG_QUALITY, 82])


def match_final(stem, d):
    """6a 定稿的每条列线 → 最近的 column_fit 轨迹（在该列自身 y 区间中点比 x），带碎片重叠率。"""
    fp = paths.RUNS_DIR / "table_reconstruct" / f"{stem}_列结构定稿.json"
    if not fp.exists() or d is None:
        return []
    cols = sorted(json.load(open(fp, encoding="utf-8"))["columns"], key=lambda c: c["x_at_mid"])
    lines = d["column_lines"]
    out = []
    for c in cols:
        ymid = (c["y"][0] + c["y"][1]) / 2.0
        best, bx = None, None
        for l in lines:
            t = l["tr"]
            if t[0, 1] <= ymid <= t[-1, 1]:
                x = float(np.interp(ymid, t[:, 1], t[:, 0]))
                if bx is None or abs(x - c["x_at_mid"]) < bx:
                    best, bx = l, abs(x - c["x_at_mid"])
        ids = set(c["segment_ids"])
        ov = (len(ids & set(best["member_ids"])) / max(1, len(ids))) if best else 0.0
        out.append({"col_index": c["index"], "final_x": round(c["x_at_mid"], 1),
                    "fit_id": best["id"] if best else None,
                    "fit_role": best["role"] if best else None,
                    "dx": round(bx, 1) if bx is not None else None,
                    "seg_overlap": round(ov, 3),
                    "usable": bool(best is not None and bx <= 40)})
    return out


def main(codes):
    stems = [f"钻孔柱状图{n}" for n in codes] if codes else \
        sorted({p.stem for p in paths.RAW_DIR.glob("钻孔柱状图*.JPG")})
    for p in (paths.COLFIX_OVERLAY_DIR, paths.COLFIX_PREVIEW_DIR):
        p.mkdir(parents=True, exist_ok=True)
    rows, mapping, done = [], {}, 0
    for stem in stems:
        d = load_fit(stem)
        if d is None:
            print(f"{stem}: 无 column_fit 产物，跳过", flush=True)
            continue
        img, _ = draw(stem, d)
        if img is None:
            print(f"{stem}: 原图读不到，跳过", flush=True)
            continue
        cv2.imwrite(str(paths.COLFIX_OVERLAY_DIR / f"{stem}.png"), img)
        tiles(stem, img, paths.COLFIX_PREVIEW_DIR)
        del img
        mapping[stem] = match_final(stem, d)
        for l in d["column_lines"]:
            t = l["tr"]
            rows.append({"image": stem, "fit_id": l["id"], "role": l["role"],
                         "x_mid": round(float(t[np.argmax(t[:, 1]), 0]), 1),
                         "y_top": int(t[:, 1].min()), "y_bot": int(t[:, 1].max()),
                         "n_pts": len(t), "max_dy": round(float(np.diff(t[np.argsort(t[:, 1])][:, 1]).max()), 1),
                         "x_min": round(float(t[:, 0].min()), 1), "x_max": round(float(t[:, 0].max()), 1),
                         "coverage_ratio": l["coverage_ratio"]})
        done += 1
        print(f"{stem}: 线 {len(d['column_lines'])}  定稿可用匹配 "
              f"{sum(1 for m in mapping[stem] if m['usable'])}/{len(mapping[stem])}  已出图", flush=True)

    with open(paths.COLFIX_LINES_CSV, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader(), w.writerows(rows)
    tot = sum(len(v) for v in mapping.values())
    ok = sum(1 for v in mapping.values() for m in v if m["usable"])
    json.dump({"n_sheets": done, "n_fit_lines": len(rows),
               "final_columns_total": tot, "final_columns_matched": ok,
               "note": "几何全部来自 column_fit trajectory；匹配=6a 定稿列在该列 y 中点到最近轨迹的 dx<=40px",
               "每张": mapping},
              open(paths.COLFIX_MANIFEST, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"\n合计 {done} 张 / column_fit 线 {len(rows)} 条；"
          f"6a 定稿列 {tot} 条中 {ok} 条能直接落到轨迹上")
    print(f"叠加图: {paths.COLFIX_OVERLAY_DIR}\n预览: {paths.COLFIX_PREVIEW_DIR}")


if __name__ == "__main__":
    main(sys.argv[1:] or [])
