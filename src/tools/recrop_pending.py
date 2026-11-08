# -*- coding: utf-8 -*-
"""待人审格重裁(墨段驱动版)。

为什么不用行区间直接裁:实测 1032 三列 409 格,手写墨迹中心在行区间内的相对位置
中位 +0.75(p90 0.94~0.98)——数字普遍贴下边线书写,行区间高达 322px 时一格内还
有多个子层值。按行区间裁必然把邻行数字带进来,判读时"这数字算谁的"全靠猜,
第一轮视觉判读因此与几何实测冲突(见 diag_row_ownership.py)。

本脚本改为:先在列带内按暗像素找**本格行区间内的墨段**,以墨段包围盒(+留白)
作为裁片内容。裁片里出现的就只有本格的字,归属由几何定,眼睛只管读字。
区间内无墨(含放宽阈复核)→ 直接判 EMPTY,不占视觉判读额度。

输入(只读): runs/table_reconstruct/<stem>_待核清单.json + 矫正图几何
输出:        runs/复核直览/crops/<stem>_L<层>_<列>.png
             runs/复核直览/几何预判.json   {tag: "EMPTY"|"HAS_INK", ...}
用法:        python src/tools/recrop_pending.py [1032 1018 ...]
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
from src.tools.agnes4_verify import chart_geometry  # noqa: E402
from src.tools.rebuild4_excel import STEMS4, _chain_x  # noqa: E402

OUT = paths.RUNS_DIR / "复核直览"
CROPS = OUT / "crops"
PAD = 10          # 墨段包围盒外扩
SCALE = 4         # 判读放大倍数
INK_STRICT = 128  # 主阈:深色笔画
INK_LOOSE = 175   # 复核阈:淡墨/铅笔
MIN_RUN = 5       # 墨段最小行高,滤掉水平行线本身


def col_x(g, name, y_mid):
    c = next((c for c in g["keep"] if c["name"] == name), None)
    if c is None:
        return None
    xa = _chain_x(g["seg_all"], g["bs"][c["li"]]["ids"], y_mid)
    xb = _chain_x(g["seg_all"], g["bs"][c["ri"]]["ids"], y_mid)
    return (xa if xa is not None else c["x0"], xb if xb is not None else c["x1"])


def runs_of(dark, min_len=MIN_RUN):
    out, s = [], None
    for i, d in enumerate(dark):
        if d and s is None:
            s = i
        elif not d and s is not None:
            if i - s >= min_len:
                out.append((s, i))
            s = None
    if s is not None and len(dark) - s >= min_len:
        out.append((s, len(dark)))
    return out


def merge(runs, gap=8):
    """相邻墨段并成块(同一数字的上下笔画被行内空白断开时不该拆两格)。"""
    if not runs:
        return []
    blocks = [list(runs[0])]
    for s, e in runs[1:]:
        if s - blocks[-1][1] <= gap:
            blocks[-1][1] = e
        else:
            blocks.append([s, e])
    return [tuple(b) for b in blocks]


def cell_crop(g, li, name):
    """返回 (裁片BGR 或 None, 本格墨段块数)。None=区间内无墨=空格。"""
    h, w = g["gray"].shape
    y0, y1 = int(g["rows_y"][li]), int(g["rows_y"][li + 1])
    xb = col_x(g, name, (g["rows_y"][li] + g["rows_y"][li + 1]) / 2)
    if xb is None:
        return None, 0
    x0, x1 = int(min(xb)), int(max(xb))
    # x 同样外扩:手写岩性描述常压着印刷列线书写,内缩会削掉右半边笔画。
    # 但墨段检测仍用内缩带,否则邻列的墨会把块数算多。
    X0, X1 = max(0, x0 - PAD), min(w, x1 + PAD)
    C0, C1 = min(w, x0 + 3), max(x0 + 4, x1 - 3)
    Y0, Y1 = max(0, y0), min(h, y1)
    if Y1 - Y0 < 3 or X1 - X0 < 3:
        return None, 0
    band = g["gray"][Y0:Y1, C0:C1]
    for thr in (INK_STRICT, INK_LOOSE):
        prof = (band < thr).sum(axis=1)
        blocks = merge(runs_of(prof > 0))
        # 行线本身在区间上下沿,贴沿 ≤3px 的段视为线,不算字
        blocks = [(s, e) for s, e in blocks if not (s <= 3 and e - s < 8)]
        if blocks:
            break
    if not blocks:
        return None, 0
    b0, b1 = blocks[0][0], blocks[-1][1]
    cy0, cy1 = max(0, Y0 + b0 - PAD), min(h, Y0 + b1 + PAD)
    crop = g["gray"][cy0:cy1, X0:X1]
    vis = cv2.cvtColor(crop, cv2.COLOR_GRAY2BGR)
    # 子层分隔:块与块之间画淡蓝虚线,提示"这里可能不止一个值"
    for j in range(1, len(blocks)):
        yy = (blocks[j - 1][1] + blocks[j][0]) // 2
        for xx in range(0, vis.shape[1], 12):
            cv2.line(vis, (xx, yy), (min(xx + 6, vis.shape[1]), yy), (255, 190, 120), 1)
    return cv2.resize(vis, None, fx=SCALE, fy=SCALE, interpolation=cv2.INTER_CUBIC), len(blocks)


def main(stems):
    CROPS.mkdir(parents=True, exist_ok=True)
    pre = json.loads((OUT / "几何预判.json").read_text(encoding="utf-8")) if (OUT / "几何预判.json").exists() else {}
    # tag 唯一分配处:拼图与判读结果都读这份映射,避免两边各自排序错位
    mapf = OUT / "tag映射.json"
    tags = json.loads(mapf.read_text(encoding="utf-8")) if mapf.exists() else {}
    for stem in stems:
        flags = json.loads((paths.RUNS_DIR / "table_reconstruct" / f"{stem}_待核清单.json")
                           .read_text(encoding="utf-8"))
        pend = [f for f in flags if f.get("处置") == "待人审" and f.get("列")]
        g = chart_geometry(int(stem[-4:]))
        n4 = stem[-4:]
        empty = ink = 0
        rows = []
        for i, f in enumerate(pend, 1):
            tag = f"{n4}-{i:02d}"
            rows.append({"tag": tag, "层": f["层"], "列": f["列"],
                         "草案": f.get("草案"), "agnes单格": f.get("agnes单格"),
                         "agnes条": f.get("agnes条")})
            img, nblk = cell_crop(g, f["层"] - 1, f["列"])
            if img is None:
                pre[tag] = "EMPTY"
                empty += 1
                continue
            pre[tag] = f"HAS_INK:{nblk}"
            cv2.imencode(".png", img)[1].tofile(
                str(CROPS / f"{stem}_L{f['层']}_{f['列']}.png"))
            ink += 1
        tags[stem] = rows
        print(f"{stem}: 有墨 {ink} 格 / 几何判空 {empty} 格 → 需视觉判读 {ink}")
    (OUT / "tag映射.json").write_text(json.dumps(tags, ensure_ascii=False, indent=1),
                                      encoding="utf-8")
    (OUT / "几何预判.json").write_text(json.dumps(pre, ensure_ascii=False, indent=1),
                                       encoding="utf-8")
    return 0


if __name__ == "__main__":
    args = sys.argv[1:]
    sys.exit(main([f"钻孔柱状图{a}" for a in args] if args else list(STEMS4)))
