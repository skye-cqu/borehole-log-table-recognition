# -*- coding: utf-8 -*-
"""阶段6c：把 Agnes 全竖线判定 + 断口补齐合并应用到列结构，产出定稿 v2。

规则（均先经 1018 试点验证）：
1. 基线 = finalize_columns.FINAL 的结构定稿（坐标间距拟合+表头放大核验）。
2. Agnes 判 frame 但位于表格内部（距左右边缘 >EDGE_TOL）的 track → 列线候选
   （表格内部不存在竖向外框，1018 #14 实证）。
3. 候选与其余 track 按"断口补齐三点要求"合并：与竖直夹角差 ≤SLOPE_TOL、
   弦延伸到对方端点的横向偏差 ≤ALIGN_TOL、轴向缺口 ≤GAP_MAX（1024 实测 615px）。
4. 槽位测试：合并链中点落在"缺失槽位"的 x 区间（相邻已检列线间距中恰好缺一条
   标准内部线）且链跨度 ≥0.55×表高 → 回收为该槽位列线；否则维持基线角色
   （1018 #18 实证：水文区子表线被误判 column，被槽位测试拒绝）。
5. 其余 Agnes 与基线的分歧（sep 被判 content/frame 等）只列清单，逐图放大核验后
   人工落定，不自动采纳。
输出：{stem}_列结构定稿.json（v2，含 recoveries）+ 重出定稿叠加图 + 分歧清单。"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.core import paths  # noqa: E402
from src.table.agnes_all_verify import load_tracks  # noqa: E402
from src.table.finalize_columns import COLUMN_NAMES, FINAL, render  # noqa: E402

SLOPE_TOL = 3.0    # deg，与竖直方向的夹角差
ALIGN_TOL = 40.0   # px，弦延伸横向对齐
GAP_MAX = 700.0    # px，轴向缺口
EDGE_TOL = 120.0   # px，frame 判定仅允许出现在表格左右边缘附近
SLOT_GAP_FACTOR = 1.5  # 相邻列线间距超过中位内部间距×该倍数 → 视为含缺失槽位


def chord(pts):
    """首末点弦：返回 (angle_from_vertical_deg, x_at(y))。"""
    p0, p1 = pts[0], pts[-1]
    dy = p1[1] - p0[1]
    dx = p1[0] - p0[0]
    ang = math.degrees(math.atan2(abs(dx), abs(dy))) if abs(dy) > 1e-6 else 90.0
    return ang, (p0, p1)


def x_at(p0, p1, y):
    y0, y1 = p0[1], p1[1]
    if abs(y1 - y0) < 1e-6:
        return p0[0]
    t = min(1.0, max(0.0, (y - y0) / (y1 - y0)))
    return p0[0] + t * (p1[0] - p0[0])


def merge_chain(seed, by_gidx, used):
    """seed 出发，按 斜率像+延伸对齐+缺口可补 传递吸收 track。"""
    chain = {seed["gidx"]}
    changed = True
    while changed:
        changed = False
        set_pts = np.vstack([by_gidx[g]["pts"] for g in chain])
        y_lo, y_hi = set_pts[:, 1].min(), set_pts[:, 1].max()
        for t in by_gidx.values():
            if t["gidx"] in chain:
                continue
            p = t["pts"]
            if p[:, 1].min() > y_hi + GAP_MAX or p[:, 1].max() < y_lo - GAP_MAX:
                continue
            ang_s, (s0, s1) = chord(set_pts[np.argsort(set_pts[:, 1])][[0, -1]])
            ang_t, (t0, t1) = chord(p[np.argsort(p[:, 1])][[0, -1]])
            if abs(ang_s - ang_t) > SLOPE_TOL:
                continue
            # 弦延伸到对方最近端点的横向偏差
            y_near = min(max(t0[1], y_lo), y_hi)
            if abs(x_at(s0, s1, y_near) - x_at(t0, t1, y_near)) > ALIGN_TOL:
                continue
            chain.add(t["gidx"])
            used.add(t["gidx"])
            changed = True
    return chain


def apply_image(n):
    stem = "钻孔柱状图" + n
    spec = FINAL[n]
    verdict = json.load(open(paths.RUNS_DIR / "table_reconstruct" /
                             f"{stem}_全竖线判定.json", encoding="utf-8"))
    vmap = {int(k): v for k, v in verdict["merged_by_track"].items()}
    d, seg, tracks = load_tracks(stem)
    by_gidx = {}
    for t in tracks:
        p = np.asarray([pt for sid in t["ids"] for pt in seg[sid]["points"]], float)
        by_gidx[t["gidx"]] = {**t, "pts": p}

    seps = {s["no"]: s for s in d["separators"]}
    frames = d.get("frames", [])
    sep_xs = sorted(seps[no]["x_at_mid"] for no in spec["columns"]) + \
             sorted(seps[no]["x_at_mid"] for no in spec["frame"])
    sep_xs = sorted(sep_xs)
    frame_xs = [f["x_at_mid"] for f in frames] + \
               [seps[no]["x_at_mid"] for no in spec["frame"]]
    x_left, x_right = (min(frame_xs + sep_xs), max(frame_xs + sep_xs))

    # 回收只允许发生在"已知缺线"的图（9 槽不满）上。标准布局 10 列固定，
    # 槽位齐全的图多出的"column"判定必是条带边/水文内线误判
    # （1016/1028/1035/1039/1044 实证）；1032 缺失两列在扫描件外，无从回收。
    missing_slots = 9 - len(spec["columns"])
    if n == "1032":
        missing_slots = 0

    # 缺失槽位区间：相邻已检列线中，间距 > 中位内部间距×1.5 的空档
    gaps = []
    med_gap = float(np.median(np.diff(sep_xs))) if len(sep_xs) > 2 else 0
    for a, b in zip(sep_xs, sep_xs[1:]):
        if b - a > med_gap * SLOT_GAP_FACTOR:
            gaps.append((a, b))
    # 端侧缺失（如 1025 缺岩性|水文、1020 情形）：最外侧列线到框线的间距
    # 不在此处理——端侧缺线无法用"两侧邻线"界定，维持基线缺检标注。

    # 基线已分配的 sep（columns/frame/content 角色）不进回收流程
    baseline_seps = {}
    for no in spec["columns"] + spec["frame"] + spec["content"]:
        baseline_seps[no] = seps[no]["x_at_mid"]

    def is_baseline_sep(t):
        if (t["pts"][:, 1].max() - t["pts"][:, 1].min()) < 0.5 * table_h:
            return False
        return any(abs(t["x_mid"] - x) < 60 for x in baseline_seps.values())

    table_h = max(p["pts"][:, 1].max() for p in by_gidx.values()) - \
              min(p["pts"][:, 1].min() for p in by_gidx.values())

    # 候选种子：Agnes 判 column，或判 frame 但在表格内部；排除基线已分配者
    seeds = []
    for t in by_gidx.values():
        if is_baseline_sep(t):
            continue
        r = vmap.get(t["gidx"])
        if r == "column":
            seeds.append(t["gidx"])
        elif r == "frame" and not (t["x_mid"] <= x_left + EDGE_TOL or
                                   t["x_mid"] >= x_right - EDGE_TOL):
            seeds.append(t["gidx"])
    used, recoveries, consumed_gaps = set(), [], []
    if missing_slots > 0:
        for g in seeds:
            if g in used:
                continue
            chain = merge_chain(by_gidx[g], by_gidx, used)
            allp = np.vstack([by_gidx[c]["pts"] for c in chain])
            span = allp[:, 1].max() - allp[:, 1].min()
            xm = float(np.median(allp[:, 0]))
            for a, b in gaps:
                if (a, b) in consumed_gaps:
                    continue
                if a < xm < b and span >= 0.55 * table_h:
                    recoveries.append({"chain": sorted(chain), "x_mid": xm,
                                       "span": span, "gap": [a, b],
                                       "segment_ids": sorted(
                                           sid for c in chain
                                           for sid in by_gidx[c]["ids"])})
                    used.update(chain)
                    consumed_gaps.append((a, b))
                    break

    # 分歧清单：sep 角色与 Agnes 不一致（不自动采纳）。只匹配贯通全表的 track，
    # 防止匹配到同 x 的碎段（1018 gidx9 实证）。
    table_h = max(p["pts"][:, 1].max() for p in by_gidx.values()) - \
              min(p["pts"][:, 1].min() for p in by_gidx.values())
    disagreements = []
    for no in spec["columns"] + spec["frame"] + spec["content"]:
        base = "column" if no in spec["columns"] else \
               ("frame" if no in spec["frame"] else "content")
        cands = [t for t in tracks
                 if abs(t["x_mid"] - seps[no]["x_at_mid"]) < 60 and
                 (by_gidx[t["gidx"]]["pts"][:, 1].max() -
                  by_gidx[t["gidx"]]["pts"][:, 1].min()) >= 0.5 * table_h]
        if not cands:
            disagreements.append({"no": no, "gidx": None, "base": base,
                                  "agnes": "unjudged", "x_mid": seps[no]["x_at_mid"],
                                  "note": "未找到对应贯通track"})
            continue
        t = min(cands, key=lambda t: abs(t["x_mid"] - seps[no]["x_at_mid"]))
        r = vmap.get(t["gidx"], "unjudged")
        if r != base and r not in ("unjudged", "unknown"):
            disagreements.append({"no": no, "gidx": t["gidx"], "base": base,
                                  "agnes": r, "x_mid": t["x_mid"]})
    return recoveries, disagreements, vmap, tracks


def apply_recovery(n, rec):
    """把已放大核验的回收线插入 v1 定稿结构 → v2（9 槽齐），重出定稿叠加图。"""
    from src.table.finalize_columns import COLUMN_NAMES, render
    stem = "钻孔柱状图" + n
    sp = paths.RUNS_DIR / "table_reconstruct" / f"{stem}_列结构定稿.json"
    struct = json.load(open(sp, encoding="utf-8"))
    cj = json.load(open(paths.CANDIDATE_COORD_DIR / f"{stem}.json", encoding="utf-8"))
    seg = {s["id"]: s for s in cj["lines"]
           if s["direction"] == "vertical" and s["label"] == "high"}
    pts = np.asarray([p for sid in rec["segment_ids"] for p in seg[sid]["points"]], float)
    struct["columns"].append({
        "index": 0, "name": None, "src": "recovery",
        "x_at_mid": rec["x_mid"], "y": [int(pts[:, 1].min()), int(pts[:, 1].max())],
        "segment_ids": rec["segment_ids"]})
    struct["columns"].sort(key=lambda c: c["x_at_mid"])
    names = COLUMN_NAMES[-len(struct["columns"]):] \
        if len(struct["columns"]) == 10 else COLUMN_NAMES[-len(struct["columns"]):]
    for i, c in enumerate(struct["columns"]):
        c["index"] = i + 1
        c["name"] = names[i]
    struct["missing"] = ""
    json.dump(struct, open(sp, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    render(stem, struct)


def main():
    only = sys.argv[1:] or sorted(FINAL)
    report = {}
    for n in only:
        rec, dis, vmap, tracks = apply_image(n)
        report[n] = {"recoveries": rec, "disagreements": dis}
        tag = "回收%d" % len(rec) if rec else ""
        print(n, tag, "分歧:%d" % len(dis), flush=True)
    json.dump(report, open(paths.RUNS_DIR / "table_reconstruct" /
                           "回收与分歧报告.json", "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)

    # 回收经逐图放大核验后落定：4 张插入定稿；1042 拒收（左区轨为双线杂轨，
    # 回收链不在 深度|层厚 位置——分带墨迹剖面实证），维持缺检标注；
    # 1020 无可用轨，1032 缺失列在扫描件外。
    for n, rec in (("1018", None), ("1024", None), ("1025", None), ("1033", None)):
        rs = report[n]["recoveries"]
        if rs:
            apply_recovery(n, rs[0])
            print(n, "v2 定稿已更新（回收 %s）" % (rs[0]["chain"],), flush=True)


if __name__ == "__main__":
    main()
