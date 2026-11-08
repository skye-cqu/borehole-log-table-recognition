# -*- coding: utf-8 -*-
"""阶段6：列片段聚簇（集合式，零拟合）。

列 = 同一列碎片段的**集合**，成员按原始坐标原样沿用，不产生任何新几何。
成员判据（三个读数，全部来自碎片自身端点数据）：
  1. 方向差：候选段端点弦倾角 − 集合末端段端点弦倾角 ≤ ANG_TOL；
  2. 轴向间隙：候选段顶端 y − 集合末端底端 y ≤ GAP_MAX（被行线切碎的切片距）；
  3. 对齐：末端段沿**它自己的端点弦**外推到候选段顶端，横向偏差 ≤ ALIGN_TOL。
噪声排除（排除发生在归属层，不动数据层）：
  横向腿片段（bbox宽 − 首尾位移 > LEG_MAX，绕框/顺行线笔画）、
  总墨长 < 1 行高的集合 → 不计入列集合。

阈值由 --quantify 依据现行 track_group 归组结果（真同线碎片对）的分布自动确定。
"""
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

ANG_TOL = 2.0        # °，方向差（量化后定）
GAP_MAX = 340.0      # px，轴向间隙（≈1行高+余量）
ALIGN_TOL = 12.0     # px，对齐偏差（量化后定）
LEG_MAX = 150.0      # px，横向腿
ROW_H = 313.0        # 行高（1019 实测；集长下限用）


def load_frags(stem):
    """vertical+high 碎片段 → {id, top(x,y), bot, ang(°), leg, length}。"""
    cj = json.load(open(paths.CANDIDATE_COORD_DIR / f"{stem}.json", encoding="utf-8"))
    frags = {}
    for s in cj["lines"]:
        if s["direction"] != "vertical" or s["label"] != "high":
            continue
        p = np.asarray(s["points"], float)
        i_t, i_b = int(p[:, 1].argmin()), int(p[:, 1].argmax())
        top, bot = p[i_t], p[i_b]
        dx, dy = bot[0] - top[0], bot[1] - top[1]
        frags[s["id"]] = {
            "id": s["id"], "top": top, "bot": bot, "points": p,
            "ang": math.degrees(math.atan2(dx, dy)) if dy > 1 else 0.0,
            "leg": float(p[:, 0].max() - p[:, 0].min() - abs(dx)),
            "length": float(s["length"]),
        }
    return frags


def _join_stats(frags, tracks):
    """参照聚簇（track_group）的相邻碎片对 → (ang_diff, dev, gap) 分布。
    dev = 上段沿自己端点弦外推到下段顶端的横向偏差。"""
    out = []
    for t in tracks:
        ids = t["segment_ids"]
        for a, b in zip(ids, ids[1:]):
            fa, fb = frags[a], frags[b]
            gap = fb["top"][1] - fa["bot"][1]
            x_pred = fa["bot"][0] + math.tan(math.radians(fa["ang"])) * gap
            out.append((abs(fb["ang"] - fa["ang"]),
                        abs(fb["top"][0] - x_pred), gap))
    return out


def quantify(stem):
    frags = load_frags(stem)
    tp = paths.TRACK_GROUP_COORD_DIR / f"{stem}.json"
    if not tp.exists():
        raise SystemExit(f"{stem}: track 归组实验目录已退役({tp} 不存在);"
                         f"本统计脚本依赖 track 聚簇结果,该路径不可用")
    tj = json.load(open(tp, encoding="utf-8"))
    st = np.array(_join_stats(frags, tj["tracks"]))
    ang, dev, gap = st[:, 0], st[:, 1], st[:, 2]
    q = lambda a: [round(float(np.percentile(a, p)), 2) for p in (50, 95, 99, 100)]
    print(f"{stem} 参照同线对 n={len(st)}")
    print(f"  ang_diff p50/95/99/max: {q(ang)}")
    print(f"  dev      p50/95/99/max: {q(dev)}")
    print(f"  gap      p50/95/99/max: {q(gap)}")
    return {"ang": q(ang), "dev": q(dev), "gap": q(gap)}


def calibrate(stem, frags):
    """逐图自适应参数：全部由该图碎片/横线数据实测，无全局常数、无参照聚类。
    紧贴对（gap≤5px，行线切割处）≈真同线接续的抽样，其分布即本图接续噪声尺度。"""
    cj = json.load(open(paths.CANDIDATE_COORD_DIR / f"{stem}.json", encoding="utf-8"))
    hl = sorted(s["midy"] for s in cj["lines"]
                if s["direction"] == "horizontal" and s["label"] == "high")
    # 同一行线的多碎片 midy 先聚簇（间隔>20px 分组），行高=簇心间距中位数
    row_ys, grp = [], [hl[0]] if hl else []
    for y in hl[1:]:
        if y - grp[-1] <= 20:
            grp.append(y)
        else:
            row_ys.append(float(np.mean(grp)))
            grp = [y]
    if grp:
        row_ys.append(float(np.mean(grp)))
    sp_row = np.diff(row_ys)
    # 行高 = 平均簇间距（首尾簇距÷簇数）：对"描述文字行 ~70px + 层界 ~300px"双峰混合稳健
    row_h = float((row_ys[-1] - row_ys[0]) / max(len(row_ys) - 1, 1)) if len(row_ys) > 2 else ROW_H
    # 紧贴对：上段底 与 下段顶 轴向距离 ≤5px
    ang_t, dev_t = [], []
    live = [f for f in frags.values() if f["leg"] <= LEG_MAX]
    live.sort(key=lambda f: f["bot"][1])
    for a in live:
        for b in live:
            gap = b["top"][1] - a["bot"][1]
            if not (0 <= gap <= 5):
                continue
            ang_t.append(abs(b["ang"] - a["ang"]))
            x_pred = a["bot"][0] + math.tan(math.radians(a["ang"])) * gap
            dev_t.append(abs(b["top"][0] - x_pred))
    # 最小不同线间距：y 重叠且 8<|dx| 的最近邻
    tops = np.array([f["top"] for f in live])
    bots = np.array([f["bot"] for f in live])
    sp = []
    for i in range(len(live)):
        ov = (np.maximum(tops[:, 1], tops[i, 1]) < np.minimum(bots[:, 1], bots[i, 1]))
        dx = np.abs(tops[:, 0] - tops[i, 0])
        m = ov & (dx > 8)
        if m.any():
            sp.append(dx[m].min())
    min_sp = float(np.percentile(sp, 5)) if sp else 40.0
    p = {
        "ANG_TOL": float(np.clip(np.percentile(ang_t, 99) if ang_t else 2.0, 2.5, 6.0)),
        "ALIGN_TOL": float(np.clip(np.percentile(dev_t, 99) if dev_t else 8.0,
                                   4.0, 0.25 * min_sp)),
        "GAP_MAX": float(np.clip(1.3 * row_h, 200, 600)),
        "ROW_H": row_h, "MIN_SP": round(min_sp, 1),
    }
    return p


def cluster(stem, ang_tol=ANG_TOL, gap_max=GAP_MAX, align_tol=ALIGN_TOL):
    frags = load_frags(stem)
    # 片段级滤噪：横向腿
    live = {i: f for i, f in frags.items() if f["leg"] <= LEG_MAX}
    order = sorted(live.values(), key=lambda f: (f["top"][1], f["top"][0]))
    used, sets = set(), []
    for f in order:
        if f["id"] in used:
            continue
        used.add(f["id"])
        members, last = [f], f
        while True:
            best = None
            for g in order:
                if g["id"] in used:
                    continue
                gap = g["top"][1] - last["bot"][1]
                if not (-3 <= gap <= gap_max):
                    continue
                if abs(g["ang"] - last["ang"]) > ang_tol:
                    continue
                x_pred = last["bot"][0] + math.tan(math.radians(last["ang"])) * gap
                dev = abs(g["top"][0] - x_pred)
                if dev > align_tol:
                    continue
                score = dev + gap / 10
                if best is None or score < best[0]:
                    best = (score, g)
            if best is None:
                break
            g = best[1]
            used.add(g["id"])
            members.append(g)
            last = g
        sets.append(members)
    # 集合级滤噪：总墨长 < 1 行高 = 噪声
    cols = [m for m in sets if sum(x["length"] for x in m) >= ROW_H]
    noise = [m for m in sets if m not in cols]
    return cols, noise, frags


def merge_sets(cols, ang_tol, gap_max, align_tol):
    """切向连续的相邻簇并簇（弓弯处方向渐变导致的拆簇）：
    末端弦向差 ≤2°、轴向间隙 ≤1.5×gap_max、对齐 ≤1.5×align_tol。零拟合。"""
    ends = []
    for m in cols:
        top, bot = m[0], m[-1]
        ends.append({"m": m, "top": top, "bot": bot,
                     "ang": math.degrees(math.atan2(
                         bot["bot"][0] - top["top"][0],
                         max(bot["bot"][1] - top["top"][1], 1)))})
    changed = True
    while changed:
        changed = False
        ends.sort(key=lambda e: e["top"]["top"][1])
        for a in ends:
            for b in ends:
                if a is b:
                    continue
                gap = b["top"]["top"][1] - a["bot"]["bot"][1]
                if not (0 <= gap <= 1.5 * gap_max):
                    continue
                if abs(b["ang"] - a["ang"]) > 2.0:
                    continue
                x_pred = a["bot"]["bot"][0] + math.tan(math.radians(a["ang"])) * gap
                if abs(b["top"]["top"][0] - x_pred) > 1.5 * align_tol:
                    continue
                a["m"] = a["m"] + b["m"]
                a["bot"] = b["bot"]
                ends.remove(b)
                changed = True
                break
            if changed:
                break
    return [e["m"] for e in ends]


def to_groups(cols, frags):
    """集合 → track_columns.classify 消费的 group dict（pts 按 y 排序）。"""
    groups = []
    for m in cols:
        pts = np.vstack([frags[x["id"]]["points"] for x in m])
        pts = pts[np.lexsort((pts[:, 1], pts[:, 0]))]   # y 主排序
        k, b = np.polyfit(pts[:, 0], pts[:, 1], 1)   # 仅供报告的直线度读数，不参与归属
        groups.append({"ids": [x["id"] for x in m], "pts": pts,
                       "ink": sum(x["length"] for x in m),
                       "y0": float(pts[0, 0]), "y1": float(pts[-1, 0]),
                       "res": float(np.percentile(
                           np.abs(np.polyval((k, b), pts[:, 0]) - pts[:, 1]), 90))})
    return groups


def main():
    stem = sys.argv[1] if len(sys.argv) > 1 else "钻孔柱状图1019"
    quantify(stem)
    cols, noise, _ = cluster(stem)
    print(f"聚簇结果：列集合 {len(cols)}（噪声集 {len(noise)}），"
          f"成员数分布 {sorted(len(m) for m in cols)[-5:]}")


if __name__ == "__main__":
    main()
