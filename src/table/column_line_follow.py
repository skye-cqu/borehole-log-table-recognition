# -*- coding: utf-8 -*-
"""阶段5 列线识别：全局结构锚点 + 身份约束的列边界恢复。

从阶段4 候选段出发，恢复真实表格列边界结构。

设计原则（对照 memory-bank/stage5_user_principles_checklist.md）：
  - 列线只能由阶段4 候选段构成，不创造原图不存在的线；
  - 连续性优先于坐标：不使用固定 X / midx 聚类"决定"列；
  - 断口补齐三点要求：斜率像 + 延伸后能对齐 + 中间缺口能用近垂直线补上；
  - 真列线：连续且平直、具分隔作用、顶底相连、整体波动小；
  - 不做分箱重采样、不延伸端点（轨迹只画成员段 + 小桥接）。

核心变化（修复根因）：
  1. 列身份来自"整张表的横向结构"——水平候选段的左/右端点聚类给出列边界锚点，
     而不是来自竖向碎片自身"长得像竖线"；
  2. 每个竖向 run 只能属于一个锚点（最近锚点 + 走廊约束），从构造上禁止
     "从 A 列平滑漂移到 B 列"；
  3. 锚点路径内的缺口按同一身份补全（三点要求），真列线一次断裂不会丢失身份；
  4. 不在任何列锚点走廊内的竖向长链，作为内部结构/外框单独归类，
     不再因为"长、直、竖"进入列候选。

阈值依据见模块常量注释与 runs/stage5_line_follow/报告.md。
"""
import json
import sys
from pathlib import Path

import numpy as np
import cv2

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))
from src.core import paths
from src.core.batch import run_batch

# ---- run 化 ----
MIN_RUN_LEN = 30.0          # 竖直 run 最短 y 跨度（px）
RUN_SPLIT_STEEP = 2.0       # 连续点间 |dx/dy| 超过此值视为近水平跳变，切分
RUN_SPLIT_DX = 50.0         # 连续点间 |dx| 超过此值且方向陡（>0.5）也切分

# ---- 锚点发现（横向结构）----
EP_BIN = 6.0                # 水平端点直方图 bin（px）
EP_SIGMA = 2.0              # 直方图平滑 sigma（bin）
EP_MIN_SEP = 40.0           # 锚点最小间距（px）：小于此距的端点峰合并
EP_MIN_COUNT = 3            # 锚点最少支持端点数
HEADER_H = 700.0            # 表头区域高度（自表顶起）：表头边界额外加权
MIN_SEG_LEN = 40.0          # 参与锚点发现的水平段最小长度
ANCHOR_MERGE_DIST = 35.0    # 锚点合并距离（px）
ANCHOR_FIT_RADIUS = 18.0    # 拟合锚点走势时，端点离锚点的最大距离（px）

# ---- run -> 锚点分配 ----
X_TOL_BASE = 30.0           # 走廊基础半宽（px）
X_TOL_MIN = 12.0            # 密集相邻锚点时的走廊下限（px）
X_TOL_NEIGH_FRAC = 0.40     # 走廊 = min(base, max(min, frac*最近邻距离))

# ---- 桥接三点校验（断口补齐）----
BRIDGE_ALIGN_TOL = 15.0     # 桥接两端外推对齐容差（px）
BRIDGE_SLOPE_TOL = 0.05     # 桥斜率与两端 run 斜率差容差
BRIDGE_TILT_MAX = 0.1       # 桥本身近垂直上限（|dx/dy|）
BRIDGE_MIN_GAP = 5.0        # 缺口 < 此值只查对齐，不查斜率一致性（噪声大）
OVERLAP_TOL = 15.0          # 相邻 run 允许的最大重叠量

# ---- 路径与分类 ----
BRIDGE_DRAW_MAX_PX = 500.0  # 桥接画线最大缺口（px）。依据：同线断口实测最大 457px；
                           # 超过此值的缺口只记录身份，不画线（不桥接远距段）
CHAIN_GAP_MAX_FRAC = 0.15   # 内部链拼接（只分身份，不画桥）的最大缺口 = 表高 * 此比例
MIN_RUNS_BOUNDARY = 2       # 列边界最少成员 run 数
MIN_COV_BOUNDARY = 400.0    # 列边界最少 y 覆盖（px，并集）
MIN_SPAN_BOUNDARY = 600.0   # 列边界最少 y 跨度（px，绝对下限）
MIN_SPAN_FRAC = 0.08        # 列边界最少 y 跨度（表高比例，与绝对下限取大）
FRAME_MIN_SPAN_FRAC = 0.25  # 判定外框的最小跨度比例
FRAME_NEAR = 45.0           # 距外框锚点 <= 此距离的路径也归为外框
INTERNAL_MIN_SPAN_FRAC = 0.20  # 内部结构链最小跨度比例（诊断输出）

# ---- 表框估计 ----
FRAME_SPAN_FRAC = 0.35      # 水平线 span >= 此比例 * 最大水平 span 视为表框行


# ============================================================
# run 化（保留阶段4 原始点）
# ============================================================
def split_runs(line):
    """把一条候选段切成竖直 run（保留原始点，不重采样）。"""
    pts = line.get("points") or []
    if len(pts) < 2:
        return []
    runs = []
    cur = [pts[0]]
    for p0, p1 in zip(pts, pts[1:]):
        dy = p1[1] - p0[1]
        dx = p1[0] - p0[0]
        steep = (abs(dx) / abs(dy)) if dy != 0 else 1e9
        if steep > RUN_SPLIT_STEEP or (abs(dx) > RUN_SPLIT_DX and steep > 0.5):
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
        resid = max(abs(x - (k * y + b)) for x, y in zip(xs, ys)) if len(xs) > 2 else 0.0
        out.append({
            "id": f"{line['id']}.{idx}",
            "orig_id": line["id"],
            "points": rpts,          # 原始 trace 顺序，画图用
            "y0": y0, "y1": y1,
            "x_top": x0, "x_bot": x1,
            "x_med": (x0 + x1) / 2.0,
            "y_mid": (y0 + y1) / 2.0,
            "k": k, "b": b,
            "span": span,
            "resid": resid,
        })
    return out


# ============================================================
# 锚点发现：水平段端点 -> 列边界锚点
# ============================================================
def _hist_peaks(values, bin_w, sigma, min_sep, min_count):
    """一维直方图平滑后找局部峰（numpy 实现，不依赖 scipy）。"""
    values = np.asarray(values, dtype=np.float64)
    if values.size == 0:
        return []
    lo, hi = values.min(), values.max()
    if hi - lo < bin_w:
        return [float(np.median(values))] if len(values) >= min_count else []
    bins = np.arange(lo, hi + bin_w, bin_w)
    hist, edges = np.histogram(values, bins=bins)
    xs = (edges[:-1] + edges[1:]) / 2.0
    # 高斯平滑
    if sigma > 0:
        k = int(np.ceil(3 * sigma))
        kernel = np.exp(-0.5 * (np.arange(-k, k + 1) / sigma) ** 2)
        kernel /= kernel.sum()
        sm = np.convolve(hist.astype(float), kernel, mode="same")
    else:
        sm = hist.astype(float)
    min_sep_bins = max(1, int(np.ceil(min_sep / bin_w)))
    peaks = []
    i = 0
    n = len(sm)
    while i < n:
        if sm[i] < 0.5:
            i += 1
            continue
        j = i
        while j + 1 < n and sm[j + 1] >= sm[j]:
            j += 1
        # j 是平台/峰的右端；取平台内最大值位置
        j2 = j
        while j2 + 1 < n and sm[j2 + 1] == sm[j]:
            j2 += 1
        pk = j if sm[j] >= sm[i] else i
        # 检查是否局部极大（左右邻居不超过）
        if (pk == 0 or sm[pk] >= sm[pk - 1]) and (pk == n - 1 or sm[pk] >= sm[pk + 1]):
            # 峰内端点计数
            xc = xs[pk]
            cnt = int(((values >= xc - bin_w) & (values <= xc + bin_w)).sum())
            if cnt >= min_count:
                sel = values[(values >= xc - bin_w) & (values <= xc + bin_w)]
                peaks.append((float(np.median(sel)), len(sel)))
        i = max(j2 + 1, pk + min_sep_bins)
    return peaks


def discover_anchors(data, table_top, table_bot):
    """从水平段端点 + 表头行边界发现列边界锚点。

    表头行边界是最高置信的列身份（受保护，不被合并）；直方图峰用于
    补充只在表头以下出现的 rowspan 子边界。
    """
    hh = [l for l in data.get("lines", [])
          if l.get("direction") == "horizontal" and l.get("label") == "high"]
    if not hh:
        return []
    eps = []
    for l in hh:
        if l.get("length", 0) < MIN_SEG_LEN:
            continue
        b = l["bbox"]
        eps.append(b[0])
        eps.append(b[2])
    peaks = _hist_peaks(eps, EP_BIN, EP_SIGMA, EP_MIN_SEP, EP_MIN_COUNT)
    header = _header_anchors(hh, table_top, HEADER_H)

    # 表头锚点受保护（x, n_ep, n_rows）
    anchors = [(x, n, True) for x, n, _nrows in header]
    # 峰锚点：离表头锚点 >= 25px 才加入，避免把 30-35px 间距的
    # rowspan 子边界与表头边界合并
    for x, n in peaks:
        if any(abs(x - hx) < 25.0 for hx, _, _ in header):
            continue
        anchors.append((x, n, False))
    anchors.sort(key=lambda a: a[0])

    # 仅对非表头锚点做小距离合并（20px）
    merged = []
    for x, n, protected in anchors:
        if protected:
            merged.append([x, n, True])
        elif merged and not merged[-1][2] and x - merged[-1][0] <= 20.0:
            px, pn, _ = merged[-1]
            merged[-1] = [(px * pn + x * n) / (pn + n), pn + n, False]
        else:
            merged.append([x, n, False])

    out = []
    for ax, n_ep, protected in merged:
        sel = []
        for l in hh:
            if l.get("length", 0) < MIN_SEG_LEN:
                continue
            b = l["bbox"]
            ymid = (b[1] + b[3]) / 2.0
            for ex in (b[0], b[2]):
                if abs(ex - ax) <= ANCHOR_FIT_RADIUS:
                    sel.append((ymid, ex))
        k, b = 0.0, float(ax)
        if len(sel) >= 3:
            ys = np.array([s[0] for s in sel], dtype=np.float64)
            xs = np.array([s[1] for s in sel], dtype=np.float64)
            A = np.vstack([ys, np.ones(len(ys))]).T
            k, b = np.linalg.lstsq(A, xs, rcond=None)[0]
            if abs(k) > 0.03:
                k = 0.03 * np.sign(k)
                b = float(np.median(xs - k * ys))
        n_ep_top = sum(1 for l in hh
                       if l.get("length", 0) >= MIN_SEG_LEN
                       and l["bbox"][1] <= table_top + HEADER_H
                       and (abs(l["bbox"][0] - ax) <= 12 or abs(l["bbox"][2] - ax) <= 12))
        out.append({
            "x": float(ax),
            "n_ep": int(n_ep),
            "n_ep_top": int(n_ep_top),
            "from_header": bool(protected),
            "k": float(k),
            "b": float(b),
        })
    out.sort(key=lambda a: a["x"])
    return out


def _header_anchors(hh, table_top, header_h):
    """表头区行内边界：按行聚类水平段，行内段端点即列边界。

    同一行内每个单元格左右端点都是边界；跨行再按 x 聚类（eps=15）统一。
    这样单行只出现一次的边界（如 rowspan 子列）不会被丢掉。
    """
    segs = []
    for l in hh:
        if l.get("length", 0) < MIN_SEG_LEN:
            continue
        b = l["bbox"]
        if b[1] <= table_top + header_h:
            segs.append((b[1], b[0], b[2]))
    if not segs:
        return []
    segs.sort(key=lambda s: s[0])
    # 按行聚类（y0 相差 <= 12px 视为同一行）
    rows = []
    for y0, x0, x1 in segs:
        if not rows or y0 - rows[-1][-1][0] > 12.0:
            rows.append([(y0, x0, x1)])
        else:
            rows[-1].append((y0, x0, x1))
    # 每行端点 -> 跨行聚类
    row_bounds = []
    for row in rows:
        eps = []
        for _, x0, x1 in row:
            eps.append(x0)
            eps.append(x1)
        eps.sort()
        row_bounds.append(eps)
    all_eps = [v for eps in row_bounds for v in eps]
    if not all_eps:
        return []
    all_eps.sort()
    clusters = []
    for v in all_eps:
        if not clusters or v - clusters[-1][-1] > 15.0:
            clusters.append([v])
        else:
            clusters[-1].append(v)
    # 统计每个聚类出现在多少行
    anchors = []
    for c in clusters:
        xc = float(np.median(c))
        n_rows = sum(1 for eps in row_bounds
                     if any(abs(v - xc) <= 12.0 for v in eps))
        anchors.append((xc, len(c), n_rows))
    return anchors


def _anchor_x(anchor, y):
    """锚点在 y 处的期望 x。"""
    return anchor["k"] * y + anchor["b"]


def _assign_runs_to_anchors(runs, anchors):
    """把竖向 run 分配给最近锚点（走廊约束）。返回 assign, unassigned。

    每个 run 至多属于一个锚点；不在任何走廊内的 run 属于内部结构/外框。
    """
    n = len(anchors)
    tol = [X_TOL_BASE] * n
    for i in range(n):
        dl = anchors[i]["x"] - anchors[i - 1]["x"] if i > 0 else 1e9
        dr = anchors[i + 1]["x"] - anchors[i]["x"] if i + 1 < n else 1e9
        tol[i] = max(X_TOL_MIN, min(X_TOL_BASE, X_TOL_NEIGH_FRAC * min(dl, dr)))
        anchors[i]["x_tol"] = tol[i]

    assign = [[] for _ in range(n)]
    unassigned = []
    for r in runs:
        best_i, best_d = None, None
        for i, a in enumerate(anchors):
            d = abs(r["x_med"] - _anchor_x(a, r["y_mid"]))
            if d <= tol[i] and (best_d is None or d < best_d):
                best_d, best_i = d, i
        if best_i is not None:
            assign[best_i].append(r)
        else:
            unassigned.append(r)
    return assign, unassigned


# ============================================================
# 链/路径几何
# ============================================================
def chain_stats(chain):
    """链的几何统计（输入 run 列表）。"""
    ys = [p[1] for r in chain for p in r["points"]]
    xs = [p[0] for r in chain for p in r["points"]]
    y0, y1 = min(ys), max(ys)
    x0, x1 = min(xs), max(xs)
    A = np.vstack([ys, np.ones(len(ys))]).T
    k, b = np.linalg.lstsq(A, xs, rcond=None)[0]
    res = np.abs(np.array(xs) - (k * np.array(ys) + b))
    top_run = min(chain, key=lambda r: r["y0"])
    bot_run = max(chain, key=lambda r: r["y1"])
    turns = 0
    ks = [r["k"] for r in sorted(chain, key=lambda r: r["y0"])]
    for k0, k1 in zip(ks, ks[1:]):
        if abs(k1 - k0) > 0.05:
            turns += 1
    # y 并集覆盖
    segs = sorted((r["y0"], r["y1"]) for r in chain)
    cov = 0.0
    if segs:
        c0, c1 = segs[0]
        for a0, a1 in segs[1:]:
            if a0 <= c1:
                c1 = max(c1, a1)
            else:
                cov += c1 - c0
                c0, c1 = a0, a1
        cov += c1 - c0
    gaps = []
    for (_, prev_y1), (next_y0, _) in zip(segs, segs[1:]):
        if next_y0 > prev_y1:
            gaps.append({"y0": float(prev_y1), "y1": float(next_y0),
                         "len": float(next_y0 - prev_y1)})
    return {
        "n_runs": len(chain),
        "span": y1 - y0,
        "coverage": float(cov),
        "x_range": x1 - x0,
        "y0": y0, "y1": y1,
        "k": float(k), "b": float(b),
        "x_top_act": float(top_run["x_top"]),
        "x_bot_act": float(bot_run["x_bot"]),
        "resid_std": float(res.std()),
        "resid_max": float(res.max()),
        "turns": turns,
        "gaps": gaps,
        "member_ids": [r["orig_id"] for r in chain],
        "run_ids": [r["id"] for r in chain],
    }


def _valid_junction(a, b, bridge_max):
    """断口补齐三点校验（用于拆分/桥接）。

    重叠/触碰（gap<=0）用局部对齐判据；真实缺口（gap>0）必须满足：
    斜率像 + 延伸能对齐 + 缺口可用近垂直线补上。
    小缺口（<20px）斜率噪声大，只查对齐 + 近垂直；
    斜率一致性只在两端 run 都足够长（span>=150）时收紧到 0.05。
    """
    g = b["y0"] - a["y1"]
    d = abs(b["x_top"] - (a["k"] * b["y0"] + a["b"]))
    if g < -OVERLAP_TOL:
        return False
    if g <= 0:
        return d <= BRIDGE_ALIGN_TOL and abs(a["k"] - b["k"]) <= 0.08
    if g > bridge_max:
        # 大缺口：不画桥但保留同一锚点身份（断裂不丢列）
        return True
    if d > BRIDGE_ALIGN_TOL:
        return False
    kb = (b["x_top"] - a["x_bot"]) / g
    if g < 20.0:
        # 小缺口斜率噪声大，但横向跳变仍不能太大
        return abs(kb) <= 0.5
    if abs(kb) > BRIDGE_TILT_MAX:
        return False
    if a["span"] >= 150.0 and b["span"] >= 150.0:
        if abs(kb - a["k"]) > BRIDGE_SLOPE_TOL or abs(kb - b["k"]) > BRIDGE_SLOPE_TOL:
            return False
    return True


def build_trajectory(chain, bridge_max):
    """轨迹 = 成员 run 原始点 + 已校验的相邻 run 间小桥接。

    不重采样、不延伸端点；未通过三点校验的接点不画桥。
    """
    chain = sorted(chain, key=lambda r: (r["y0"], r["x_top"]))
    polylines = [[p for p in r["points"]] for r in chain]
    bridges = []
    for a, b in zip(chain, chain[1:]):
        gap = b["y0"] - a["y1"]
        if 0 < gap <= bridge_max and _valid_junction(a, b, bridge_max):
            bridges.append([[a["x_bot"], a["y1"]], [b["x_top"], b["y0"]]])
    return polylines, bridges


def split_anchor_runs(runs, bridge_max):
    """把锚点内 run 按连接有效性切成子路径。

    同一走廊可能吸入两条平行线（相距 < 走廊宽），按三点校验拆开，
    避免画斜桥把两条线误连成一条。
    """
    runs = sorted(runs, key=lambda r: (r["y0"], r["x_top"]))
    if not runs:
        return []
    pieces = []
    cur = [runs[0]]
    for a, b in zip(runs, runs[1:]):
        if _valid_junction(a, b, bridge_max):
            cur.append(b)
        else:
            pieces.append(cur)
            cur = [b]
    pieces.append(cur)
    return pieces


# ============================================================
# 未分配 run 链拼接（内部结构 / 外框诊断）
# ============================================================
def _chain_unassigned(runs, bridge_max):
    """对未分配 run 做竖直链拼接（同一物理线尽量连成一条）。"""
    if not runs:
        return []
    runs = sorted(runs, key=lambda r: (r["y0"], r["x_med"]))
    chains = []
    used = set()
    for i, a in enumerate(runs):
        if i in used:
            continue
        chain = [a]
        used.add(i)
        prev = a
        while True:
            best_j, best_d = None, None
            for j in range(i + 1, len(runs)):
                if j in used:
                    continue
                b = runs[j]
                if b["y0"] > prev["y1"] + bridge_max:
                    break
                if b["y0"] < prev["y1"] - OVERLAP_TOL:
                    continue
                if not _valid_junction(prev, b, bridge_max):
                    continue
                d = abs(b["x_top"] - (prev["k"] * b["y0"] + prev["b"]))
                if best_d is None or d < best_d:
                    best_d, best_j = d, j
            if best_j is None:
                break
            chain.append(runs[best_j])
            used.add(best_j)
            prev = runs[best_j]
        chains.append(chain)
    return chains


# ============================================================
# 主流程：锚点 -> 分配 -> 路径 -> 分类
# ============================================================
def estimate_table_bounds(data):
    """用水平 high 段估计表格顶/底（无水平线时退回垂直候选范围）。"""
    hh = [l for l in data.get("lines", [])
          if l.get("direction") == "horizontal" and l.get("label") == "high"]
    if not hh:
        vh = [l for l in data.get("lines", [])
              if l.get("direction") == "vertical" and l.get("label") == "high"]
        ys = [p[1] for l in vh for p in l.get("points", [])]
        return (min(ys), max(ys)) if ys else (0.0, 0.0)
    mx = max(max(p[0] for p in l["points"]) - min(p[0] for p in l["points"])
             for l in hh)
    full = [l for l in hh
            if max(p[0] for p in l["points"]) - min(p[0] for p in l["points"])
            >= FRAME_SPAN_FRAC * mx]
    ys = [p[1] for l in full for p in l["points"]]
    return (min(ys), max(ys)) if ys else (0.0, 0.0)


def _make_path(pid, role, anchor, runs, table_top, table_h, bridge_draw_max):
    """把一组 run 组织成输出路径 dict。"""
    if not runs:
        return None
    s = chain_stats(runs)
    polylines, bridges = build_trajectory(runs, bridge_draw_max)
    span_ratio = s["span"] / table_h if table_h else 0.0
    cov_ratio = s["coverage"] / table_h if table_h else 0.0
    xs = [p[0] for r in runs for p in r["points"]]
    support = _support_flags_from_runs(runs, table_top, table_h)
    return {
        "id": pid,
        "role": role,
        "anchor_x": float(anchor["x"]) if anchor else None,
        "anchor_k": float(anchor["k"]) if anchor else 0.0,
        "anchor_b": float(anchor["b"]) if anchor else 0.0,
        "x_tol": float(anchor.get("x_tol", 0.0)) if anchor else 0.0,
        "n_ep": int(anchor.get("n_ep", 0)) if anchor else 0,
        "n_ep_top": int(anchor.get("n_ep_top", 0)) if anchor else 0,
        "y_top": s["y0"],
        "y_bot": s["y1"],
        "span": s["span"],
        "span_ratio": round(span_ratio, 4),
        "coverage": s["coverage"],
        "coverage_ratio": round(cov_ratio, 4),
        "x_med": float(np.median(xs)),
        "x_range": s["x_range"],
        "k": s["k"],
        "b": s["b"],
        "resid_std": s["resid_std"],
        "resid_max": s["resid_max"],
        "turns": s["turns"],
        "n_runs": s["n_runs"],
        "gaps": s["gaps"],
        "support": support,
        "member_ids": s["member_ids"],
        "run_ids": s["run_ids"],
        "polylines": polylines,
        "bridges": bridges,
    }


def _support_flags_from_runs(runs, table_top, table_h):
    segs = [(r["y0"], r["y1"]) for r in runs]
    top = sum(1 for y0, y1 in segs if y0 <= table_top + 0.15 * table_h)
    mid = sum(1 for y0, y1 in segs
              if y0 <= table_top + 0.5 * table_h and y1 >= table_top + 0.35 * table_h)
    bot = sum(1 for y0, y1 in segs if y1 >= table_top + 0.85 * table_h)
    return {"top": int(top), "middle": int(mid), "bottom": int(bot)}


def extract_column_lines(data):
    """纯函数：阶段4 数据 -> 列边界路径 + 内部结构 + 外框 + 诊断。"""
    vh = [l for l in data.get("lines", [])
          if l.get("direction") == "vertical" and l.get("label") == "high"]
    runs = []
    for l in vh:
        runs.extend(split_runs(l))

    table_top, table_bot = estimate_table_bounds(data)
    table_h = max(table_bot - table_top, 1.0)

    anchors = discover_anchors(data, table_top, table_bot)
    assign, unassigned = _assign_runs_to_anchors(runs, anchors)
    bridge_draw_max = BRIDGE_DRAW_MAX_PX
    chain_gap_max = CHAIN_GAP_MAX_FRAC * table_h

    # 锚点路径：同一锚点内先按三点校验拆成子路径（禁止斜桥把平行线误连）
    anchor_paths = []
    for i, a in enumerate(anchors):
        rs = assign[i]
        if not rs:
            continue
        pieces = split_anchor_runs(rs, bridge_draw_max)
        paths = []
        for piece in pieces:
            p = _make_path(i, "column", a, piece, table_top, table_h, bridge_draw_max)
            if p is not None:
                p["is_main"] = False
                paths.append(p)
        if not paths:
            continue
        # 主路径 = 覆盖证据最多的子路径；其余视为平行碎片/内部线
        main_idx = max(range(len(paths)), key=lambda k: paths[k]["coverage"])
        paths[main_idx]["is_main"] = True
        anchor_paths.extend(paths)

    # 未分配链（内部结构 / 外框）：身份拼接用 0.15×表高，画桥仍用 500px 上限
    unassigned_chains = _chain_unassigned(unassigned, chain_gap_max)
    unassigned_paths = []
    for i, chain in enumerate(unassigned_chains):
        p = _make_path(len(anchors) + i, "internal", None, chain, table_top, table_h,
                       bridge_draw_max)
        unassigned_paths.append(p)

    # 外框识别：
    # 1) 所有结构中，最左/最右且足够长的路径；
    # 2) 超出最外端表头锚点的路径（表头锚点界定真正的列边界范围）。
    all_structs = anchor_paths + [p for p in unassigned_paths
                                  if p["span_ratio"] >= FRAME_MIN_SPAN_FRAC]
    frame_xs = []
    if all_structs:
        leftmost = min(all_structs, key=lambda p: p["x_med"])
        rightmost = max(all_structs, key=lambda p: p["x_med"])
        frame_xs = [leftmost["x_med"], rightmost["x_med"]]
    header_anchors = [a for a in anchors if a.get("from_header")]
    outer_header_x = None
    if header_anchors:
        outer_header_x = (min(a["x"] for a in header_anchors),
                          max(a["x"] for a in header_anchors))

    def _is_left_frame(p):
        # 只有最左端结构是外框；左侧其余未分配结构归内部
        return bool(frame_xs) and abs(p["x_med"] - frame_xs[0]) <= FRAME_NEAR

    def _is_right_frame(p):
        # 右侧：超出最右表头锚点的结构都归外框（右框常裂成多段）
        if outer_header_x is not None and p["x_med"] > outer_header_x[1] + 20.0:
            return True
        return bool(frame_xs) and abs(p["x_med"] - frame_xs[-1]) <= FRAME_NEAR

    frames = []
    columns = []
    internal_structures = []
    rejected = []
    for p in anchor_paths:
        if _is_left_frame(p) or _is_right_frame(p):
            p["role"] = "frame"
            frames.append(p)
        elif (p["n_runs"] >= MIN_RUNS_BOUNDARY
              and p["coverage"] >= MIN_COV_BOUNDARY
              and p["span"] >= max(MIN_SPAN_BOUNDARY, MIN_SPAN_FRAC * table_h)):
            if p["is_main"]:
                p["role"] = "column"
                columns.append(p)
            else:
                # 同走廊内的平行碎片/内部线，不进列候选
                p["role"] = "parallel"
                internal_structures.append(p)
        else:
            p["role"] = "rejected"
            rejected.append(p)

    for p in unassigned_paths:
        if (_is_left_frame(p) or _is_right_frame(p)) \
                and p["span_ratio"] >= FRAME_MIN_SPAN_FRAC:
            p["role"] = "frame"
            frames.append(p)
        elif p["span_ratio"] >= INTERNAL_MIN_SPAN_FRAC:
            p["role"] = "internal"
            internal_structures.append(p)
        else:
            p["role"] = "rejected"
            rejected.append(p)

    columns.sort(key=lambda p: p["x_med"])
    frames.sort(key=lambda p: p["x_med"])
    internal_structures.sort(key=lambda p: p["x_med"])
    rejected.sort(key=lambda p: p["x_med"])

    # 相邻列距离
    for idx, p in enumerate(columns):
        left_x = columns[idx - 1]["x_med"] if idx > 0 else None
        right_x = columns[idx + 1]["x_med"] if idx + 1 < len(columns) else None
        p["left_neighbor_x"] = left_x
        p["right_neighbor_x"] = right_x
        dists = []
        if left_x is not None:
            dists.append(p["x_med"] - left_x)
        if right_x is not None:
            dists.append(right_x - p["x_med"])
        p["min_neighbor_dist"] = min(dists) if dists else None

    return {
        "table_top": float(table_top),
        "table_bottom": float(table_bot),
        "table_height": float(table_h),
        "n_runs": len(runs),
        "n_anchors": len(anchors),
        "n_column_candidates": len(columns),
        "anchors": anchors,
        "chains": anchor_paths,           # 兼容旧字段：锚点路径
        "column_candidates": columns,
        "frames": frames,
        "internal_structures": internal_structures,
        "rejected": rejected,
        "n_unassigned_runs": len(unassigned),
    }


# ============================================================
# 可视化与指标
# ============================================================
def draw_path(viz, path, color, thickness=2, bridge_style="solid"):
    for pl in path["polylines"]:
        if len(pl) < 2:
            continue
        arr = np.array(pl, dtype=np.int32)
        cv2.polylines(viz, [arr], False, color, thickness, cv2.LINE_8)
    for b in path["bridges"]:
        pt1 = (int(round(b[0][0])), int(round(b[0][1])))
        pt2 = (int(round(b[1][0])), int(round(b[1][1])))
        if bridge_style == "dashed":
            cv2.line(viz, pt1, pt2, color, 1, cv2.LINE_AA)
        else:
            cv2.line(viz, pt1, pt2, color, thickness, cv2.LINE_8)


def structure_checks(result, data):
    """结构正确性自动检查（非 ground truth，只证明结构性质）。"""
    checks = {
        "non_crossing": True,
        "no_run_duplication": True,
        "lateral_jump_count": 0,
        "bridge_tilt_violations": 0,
        "bridge_tilt_warnings": 0,
        "columns_local_only": sum(
            1 for p in result["column_candidates"] if p["span_ratio"] < 0.3),
        "internal_long_verticals": len(result["internal_structures"]),
    }
    cols = result["column_candidates"] + result["frames"]
    run_seen = {}
    for p in cols:
        for rid in p["run_ids"]:
            if rid in run_seen:
                checks["no_run_duplication"] = False
                run_seen[rid] += 1
            else:
                run_seen[rid] = 1
        for b in p["bridges"]:
            dy = abs(b[1][1] - b[0][1])
            dx = abs(b[1][0] - b[0][0])
            if dy == 0 or dx / dy > 0.5:
                checks["bridge_tilt_violations"] += 1
            elif dx / dy > 0.1:
                checks["bridge_tilt_warnings"] += 1
    # 相邻列在重叠 y 区间的 x 顺序
    ordered = sorted(cols, key=lambda p: p["x_med"])
    for pa, pb in zip(ordered, ordered[1:]):
        if pa["y_bot"] <= pb["y_top"] or pb["y_bot"] <= pa["y_top"]:
            continue
        if pa["x_med"] > pb["x_med"]:
            checks["non_crossing"] = False
    # 路径内大幅横向跳变
    for p in cols:
        # 从 polylines 还原相邻 run 端点
        pls = p["polylines"]
        for a, b in zip(pls, pls[1:]):
            if not a or not b:
                continue
            dx = abs(b[0][0] - a[-1][0])
            dy = b[0][1] - a[-1][1]
            if dy > 0 and (dx > 60.0 or dx / dy > 0.2):
                checks["lateral_jump_count"] += 1
    return checks


def chain_metrics(result):
    """几何健全性指标（折线/近横线/跨列伪影），只统计输出列候选。"""
    metrics = {"turns": 0, "near_horizontal": 0, "cross_col_artifacts": 0,
               "n_chains": len(result["chains"]),
               "n_column_candidates": result["n_column_candidates"]}

    def scan(p, out):
        if p["turns"] > 0:
            out["turns"] += 1
        for pl in p["polylines"]:
            for p0, p1 in zip(pl, pl[1:]):
                dy = abs(p1[1] - p0[1])
                dx = abs(p1[0] - p0[0])
                if dy == 0 or dx / dy > 2.0:
                    out["near_horizontal"] += 1
        for b in p["bridges"]:
            dy = abs(b[1][1] - b[0][1])
            dx = abs(b[1][0] - b[0][0])
            if dy == 0 or dx / dy > 2.0:
                out["near_horizontal"] += 1
        natural = abs(p["k"]) * p["span"]
        if p["x_range"] - natural > 150.0:
            out["cross_col_artifacts"] += 1

    for p in result["column_candidates"]:
        scan(p, metrics)
    return metrics


def raster_assert(data, result, thickness=2):
    """内部一致性：输出像素 ⊆ 成员段并集 ∪ 桥接（不证明结构正确）。"""
    width, height = int(data["width"]), int(data["height"])
    by_id = {l["id"]: l for l in data.get("lines", [])}
    member_mask = np.zeros((height, width), dtype=np.uint8)
    out_mask = np.zeros((height, width), dtype=np.uint8)
    bridge_mask = np.zeros((height, width), dtype=np.uint8)
    for p in result["column_candidates"] + result["frames"]:
        for mid in p["member_ids"]:
            ln = by_id.get(mid)
            if not ln:
                continue
            pts = ln.get("points") or []
            for p0, p1 in zip(pts, pts[1:]):
                cv2.line(member_mask,
                         (int(round(p0[0])), int(round(p0[1]))),
                         (int(round(p1[0])), int(round(p1[1]))), 1,
                         thickness=thickness)
        for pl in p["polylines"]:
            for p0, p1 in zip(pl, pl[1:]):
                cv2.line(out_mask,
                         (int(round(p0[0])), int(round(p0[1]))),
                         (int(round(p1[0])), int(round(p1[1]))), 1,
                         thickness=thickness)
        for b in p["bridges"]:
            cv2.line(out_mask,
                     (int(round(b[0][0])), int(round(b[0][1]))),
                     (int(round(b[1][0])), int(round(b[1][1]))), 1,
                     thickness=thickness)
            cv2.line(bridge_mask,
                     (int(round(b[0][0])), int(round(b[0][1]))),
                     (int(round(b[1][0])), int(round(b[1][1]))), 1,
                     thickness=thickness)
    out_unexplained = (out_mask > 0) & ~(member_mask > 0) & ~(bridge_mask > 0)
    return {
        "output_px": int((out_mask > 0).sum()),
        "member_px": int((member_mask > 0).sum()),
        "bridge_px": int((bridge_mask > 0).sum()),
        "output_px_not_in_members": int(((out_mask > 0) & (member_mask == 0)).sum()),
        "output_px_unexplained": int(out_unexplained.sum()),
        "ok": bool(out_unexplained.sum() == 0),
    }


def process_image(json_path):
    """处理单张图：锚点路径 + 三张可视化（原图/叠加/诊断）。"""
    json_path = Path(json_path)
    try:
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        result = extract_column_lines(data)
        metrics = chain_metrics(result)
        assertion = raster_assert(data, result)
        checks = structure_checks(result, data)

        stem = json_path.stem
        out_dir = paths.LINE_FOLLOW_COORD_DIR
        overlay_dir = paths.LINE_FOLLOW_OVERLAY_DIR
        diag_dir = paths.LINE_FOLLOW_DIAG_DIR
        paths.ensure_dirs(out_dir, overlay_dir, diag_dir)

        out = {
            "image": data.get("image"),
            "width": data.get("width"),
            "height": data.get("height"),
            "pipeline": "global_anchor: horizontal_endpoints -> column_anchors "
                        "-> run_assignment -> per_anchor_paths",
            **result,
            "visual_soundness": metrics,
            "structure_checks": checks,
            "raster_assert": assertion,
        }
        with open(out_dir / f"{stem}_line_follow.json", "w", encoding="utf-8") as f:
            json.dump(out, f, ensure_ascii=False)

        # 可视化
        jpg = paths.RAW_DIR / f"{stem}.JPG"
        if not jpg.exists():
            jpg = paths.RAW_DIR / f"{stem}.jpg"
        if jpg.exists():
            orig = cv2.imread(str(jpg))
            if orig is not None:
                palette = [(0, 0, 255), (0, 200, 0), (255, 0, 0), (255, 255, 0),
                           (255, 0, 255), (0, 255, 255), (0, 128, 255), (0, 255, 128),
                           (128, 0, 255), (255, 128, 0)]
                # A. 原图
                cv2.imwrite(str(diag_dir / f"{stem}_A原图.png"), orig)
                # B. 列边界叠加图（按角色着色）
                viz = orig.copy()
                for p in result["column_candidates"]:
                    draw_path(viz, p, (0, 200, 0), thickness=2)      # 列 = 绿
                for p in result["frames"]:
                    draw_path(viz, p, (128, 128, 128), thickness=1)  # 外框 = 灰
                for p in result["internal_structures"]:
                    draw_path(viz, p, (0, 0, 255), thickness=1)      # 内部/平行 = 蓝
                for p in result["rejected"]:
                    draw_path(viz, p, (0, 165, 255), thickness=1)    # 拒绝 = 橙
                cv2.imwrite(str(overlay_dir / f"{stem}.png"), viz)
                # C. 诊断图 = 角色着色 + 列 ID 标注（复用 viz，省内存）
                for i, p in enumerate(result["column_candidates"]):
                    ytxt = int((p["y_top"] + p["y_bot"]) / 2)
                    cv2.putText(viz, f"C{i}@{int(p['x_med'])}",
                                (int(p["x_med"]) + 4, min(ytxt, int(data["height"]) - 8)),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), 2, cv2.LINE_AA)
                cv2.imwrite(str(diag_dir / f"{stem}_C诊断图.png"), viz)
                del viz
                # B2. 每列不同色（可选第二张）
                viz2 = orig.copy()
                for i, p in enumerate(result["column_candidates"]):
                    draw_path(viz2, p, palette[i % len(palette)], thickness=2)
                for p in result["frames"]:
                    draw_path(viz2, p, (128, 128, 128), thickness=1)
                for p in result["internal_structures"]:
                    draw_path(viz2, p, (0, 0, 255), thickness=1)
                cv2.imwrite(str(overlay_dir / f"{stem}_列分色.png"), viz2)
                del viz2

        return stem, True, {
            "n_runs": result["n_runs"],
            "n_anchors": result["n_anchors"],
            "n_column_candidates": result["n_column_candidates"],
            "n_frames": len(result["frames"]),
            "n_internal": len(result["internal_structures"]),
            "structure_checks": checks,
            "visual_soundness": metrics,
            "raster_assert": assertion,
        }
    except Exception as e:
        return json_path.stem, False, {"error": str(e)}


def main():
    paths.ensure_dirs(paths.LINE_FOLLOW_COORD_DIR, paths.LINE_FOLLOW_OVERLAY_DIR,
                      paths.LINE_FOLLOW_DIAG_DIR)
    pairs = [(jf,) for (_, jf) in paths.pair_jpg_json(paths.CANDIDATE_COORD_DIR)]
    if not pairs:
        print("未找到候选 JSON 配对，退出。")
        return
    args = sys.argv[1:]
    if args:
        stems = set(args)
        pairs = [p for p in pairs if p[0].stem in stems]
    results = run_batch(pairs, process_image, starmap=True)
    ok = sum(1 for _, s, _ in results if s)
    print(f"完成 {ok}/{len(results)} 张；产物目录：{paths.LINE_FOLLOW_COORD_DIR}")
    for stem, status, info in results:
        if status:
            c = info["structure_checks"]
            print(f"  {stem}: columns={info['n_column_candidates']} "
                  f"frames={info['n_frames']} internal={info['n_internal']} "
                  f"anchors={info['n_anchors']} "
                  f"non_crossing={c['non_crossing']} "
                  f"dup_run={not c['no_run_duplication']} "
                  f"jumps={c['lateral_jump_count']}")
        else:
            print(f"  {stem}: FAILED {info}")


if __name__ == "__main__":
    main()
