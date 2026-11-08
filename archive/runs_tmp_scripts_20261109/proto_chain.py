# -*- coding: utf-8 -*-
"""阶段5 沿线追踪原型 — 只读校准用，不写入正式产物。"""
import json, math, sys
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from src.core import paths

# ---- 参数（待校准）----
MIN_RUN_LEN = 30.0        # 子段最短 y 跨度
SEG_TILT_MAX = 0.15       # 子段自身 |dx/dy| 上限（分割处更严格）
OVERLAP_TOL = 15.0        # 允许 B.top 在 A.bot 之前的重叠量
LOCAL_GAP_MAX = 60.0      # 局部链接的最大 y 缺口
JUNCTION_TOL = 12.0       # 链接点 x 预测残差容差（px）
SLOPE_TOL = 0.03          # 相邻子段斜率差容差
BRIDGE_MIN_GAP = 5.0      # 超过此缺口才检查桥接斜率
BRIDGE_SLOPE_TOL = 0.04   # 桥接斜率与两端斜率差容差

def split_runs(line):
    pts = line.get("points") or []
    if len(pts) < 2:
        return []
    # 按原 trace 顺序，在 |dx/dy| 过大处分段；再把每段按 y 归一化
    runs = []
    cur = [pts[0]]
    for p0, p1 in zip(pts, pts[1:]):
        dy = p1[1] - p0[1]
        dx = p1[0] - p0[0]
        steep = (abs(dx) / abs(dy)) if dy != 0 else 1e9
        # 在近水平跳变处切分；小抖动保留在段内
        if steep > 2.0 or (abs(dx) > 50 and steep > 0.5):
            if len(cur) >= 2:
                runs.append(cur)
            cur = [p1]
        else:
            cur.append(p1)
    if len(cur) >= 2:
        runs.append(cur)
    out = []
    for idx, rpts in enumerate(runs):
        s = sorted(rpts, key=lambda q: (q[1], q[0]))
        ys = [q[1] for q in s]
        xs = [q[0] for q in s]
        y0, y1 = float(ys[0]), float(ys[-1])
        x0, x1 = float(xs[0]), float(xs[-1])
        span = y1 - y0
        if span < MIN_RUN_LEN:
            continue
        k = (x1 - x0) / span if span > 1e-9 else 0.0
        b = x0 - k * y0
        # 直线度：点到端点线最大残差
        resid = max(abs(x - (k * y + b)) for x, y in zip(xs, ys)) if len(xs) > 2 else 0.0
        out.append({
            "id": f"{line['id']}.{idx}",
            "orig_id": line["id"],
            "points": s,
            "y0": y0, "y1": y1,
            "x_top": x0, "x_bot": x1,
            "k": k, "b": b,
            "span": span,
            "resid": resid,
        })
    return out

def chain_runs(runs):
    runs = sorted(runs, key=lambda r: (r["y0"], r["x_top"]))
    n = len(runs)
    succ = {}   # i -> j
    owner = {}  # j -> i
    for i, a in enumerate(runs):
        best_j, best_d = None, None
        # 候选：y_top 在 [a.y1 - OVERLAP_TOL, a.y1 + LOCAL_GAP_MAX]
        for j in range(i + 1, n):
            b = runs[j]
            if b["y0"] > a["y1"] + LOCAL_GAP_MAX:
                break
            if b["y0"] < a["y1"] - OVERLAP_TOL:
                continue
            g = b["y0"] - a["y1"]
            x_pred = a["k"] * b["y0"] + a["b"]
            d = abs(b["x_top"] - x_pred)
            if d > JUNCTION_TOL:
                continue
            if abs(a["k"] - b["k"]) > SLOPE_TOL:
                continue
            if g >= BRIDGE_MIN_GAP:
                kb = (b["x_top"] - a["x_bot"]) / g
                if abs(kb - a["k"]) > BRIDGE_SLOPE_TOL or abs(kb - b["k"]) > BRIDGE_SLOPE_TOL:
                    continue
            if best_d is None or d < best_d:
                best_d, best_j = d, j
        if best_j is None:
            continue
        # 冲突裁决：若已被更近的前驱占用，比 d
        if best_j in owner:
            k_prev = owner[best_j]
            a_prev = runs[k_prev]
            g_prev = a_prev["y1"] - a_prev["y0"]  # not used
            # 重新计算前驱 d
            x_pred_prev = a_prev["k"] * runs[best_j]["y0"] + a_prev["b"]
            d_prev = abs(runs[best_j]["x_top"] - x_pred_prev)
            if d_prev <= best_d:
                continue
            succ.pop(k_prev, None)
        owner[best_j] = i
        succ[i] = best_j

    # 收集链
    has_pred = set(succ.values())
    chains = []
    visited = set()
    for i in range(n):
        if i in visited or i in has_pred:
            continue
        chain = []
        j = i
        while j is not None and j not in visited:
            visited.add(j)
            chain.append(runs[j])
            j = succ.get(j)
        if len(chain) >= 2:
            chains.append(chain)
    # 单条长 run 也算链候选（后续过滤用）
    for i in range(n):
        if i not in visited:
            if runs[i]["span"] >= 300:
                chains.append([runs[i]])
            visited.add(i)
    return chains

def chain_stats(c):
    ys = [p[1] for r in c for p in r["points"]]
    xs = [p[0] for r in c for p in r["points"]]
    y0, y1 = min(ys), max(ys)
    x0, x1 = min(xs), max(xs)
    span = y1 - y0
    # 全局线拟合
    A = np.vstack([ys, np.ones(len(ys))]).T
    k, b = np.linalg.lstsq(A, xs, rcond=None)[0]
    res = np.abs(np.array(xs) - (k * np.array(ys) + b))
    # 端点（实际，用于桥接）
    top_run = min(c, key=lambda r: r["y0"])
    bot_run = max(c, key=lambda r: r["y1"])
    x_top_act = top_run["x_top"]
    x_bot_act = bot_run["x_bot"]
    # 折线：相邻 run 端点方向变化
    turns = 0
    ks = [r["k"] for r in sorted(c, key=lambda r: r["y0"])]
    for k0, k1 in zip(ks, ks[1:]):
        if abs(k1 - k0) > 0.05:
            turns += 1
    return {"n": len(c), "span": span, "x_range": x1 - x0, "y0": y0, "y1": y1,
            "k": float(k), "b": float(b), "x_top_act": float(x_top_act),
            "x_bot_act": float(x_bot_act),
            "resid_std": float(res.std()), "resid_max": float(res.max()),
            "turns": turns, "member_ids": [r["orig_id"] for r in c],
            "run_ids": [r["id"] for r in c]}


# ---- 第二阶段：跨大缺口合并链（斜率像 + 延伸对齐 + 缺口可用同斜率补） ----
MERGE_GAP_MAX = 500.0
MERGE_SLOPE_TOL = 0.02
MERGE_ALIGN_TOL = 25.0
MERGE_BRIDGE_TOL = 0.03

def merge_chains(chains):
    stats = [chain_stats(c) for c in chains]
    n = len(chains)
    parent = list(range(n))

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a, b):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[ra] = rb

    for i in range(n):
        for j in range(n):
            if i == j:
                continue
            A, B = stats[i], stats[j]
            gap = B["y0"] - A["y1"]
            if gap < -OVERLAP_TOL or gap > MERGE_GAP_MAX:
                continue
            if abs(A["k"] - B["k"]) > MERGE_SLOPE_TOL:
                continue
            # 延伸对齐：A 预测 B 端，B 预测 A 端
            d_bot = abs(B["x_top_act"] - (A["k"] * B["y0"] + A["b"]))
            d_top = abs(A["x_bot_act"] - (B["k"] * A["y1"] + B["b"]))
            if d_bot > MERGE_ALIGN_TOL or d_top > MERGE_ALIGN_TOL:
                continue
            if gap > 0:
                # 缺口桥接斜率
                kb = (B["x_top_act"] - A["x_bot_act"]) / gap
                if abs(kb - A["k"]) > MERGE_BRIDGE_TOL or abs(kb - B["k"]) > MERGE_BRIDGE_TOL:
                    continue
                if abs(kb) > 0.1:
                    continue
            union(i, j)
    groups = {}
    for i in range(n):
        groups.setdefault(find(i), []).append(chains[i])
    return [sum(g, []) for g in groups.values()]

def main():
    for stem in ["1015", "1027", "1035"]:
        data = json.load(open(paths.CANDIDATE_COORD_DIR / f"钻孔柱状图{stem}.json", encoding="utf-8"))
        vh = [l for l in data["lines"] if l.get("direction") == "vertical" and l.get("label") == "high"]
        runs = []
        for l in vh:
            runs.extend(split_runs(l))
        chains = chain_runs(runs)
        # 表高
        hh = [l for l in data["lines"] if l.get("direction") == "horizontal" and l.get("label") == "high"]
        mx = max(max(p[0] for p in l["points"]) - min(p[0] for p in l["points"]) for l in hh)
        full = [l for l in hh if max(p[0] for p in l["points"]) - min(p[0] for p in l["points"]) >= 0.35 * mx]
        ys = [p[1] for l in full for p in l["points"]]
        table_top, table_bot = min(ys), max(ys)
        table_h = table_bot - table_top
        merged = merge_chains(chains)
        stats = [chain_stats(c) for c in merged]
        stats.sort(key=lambda s: -s["span"])
        print(f"\n===== {stem}: runs={len(runs)} chains={len(chains)} merged={len(merged)} table_y={table_top:.0f}-{table_bot:.0f} h={table_h:.0f}")
        for s in stats[:35]:
            ratio = s["span"] / table_h if table_h else 0
            print(f"  n={s['n']:3d} span={s['span']:7.0f} ratio={ratio:4.2f} y={s['y0']:6.0f}-{s['y1']:6.0f} "
                  f"x_range={s['x_range']:6.1f} k={s['k']:+.4f} resid_std={s['resid_std']:5.1f} resid_max={s['resid_max']:5.1f} turns={s['turns']}")

if __name__ == "__main__":
    main()
