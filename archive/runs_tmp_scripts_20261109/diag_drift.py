# -*- coding: utf-8 -*-
"""诊断C：线内"台阶"出在哪一跳——上游的链里就有，还是我聚簇时拼进去的。

链 = 阶段6c 之前已经拼好的横向链（merge_tracks 的产物，来自阶段3/4 的段）。
一条链自己的点列若在 Δx<60px 内竖向跳了 >15px → 这条链本身就跨了两行（问题在上游/拼链）。
一条层界若由多条链拼成，接缝处（前一条链末 x 与后一条链起 x 之间）跳了 >15px → 是我聚簇
把两行的链并成了一条（问题在本阶段 6c 的 ±LINE_TOL 单链接）。
两条分开数，就知道该去哪个阶段修。

用法: python runs/tmp/diag_drift.py [1027 1040 ...]
"""
import json
import os
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "runs" / "tmp"))
from src.core import paths                                          # noqa: E402
from diag_row_geom import chains_of                                 # noqa: E402

STEP_DX = 60      # 相邻顶点横向距离上限：小于它才算"同一处的跳变"，不是长距离斜率
STEP = float(os.environ.get("STEP", 15))   # 台阶判定阈值(px)；门禁用的是半行高≈35
# 同一把尺子也可量门禁前的快照：SRC=rollback/行判定_门禁前_20260924 python runs/tmp/diag_drift.py
SRC = Path(os.environ.get("SRC", ROOT / "runs" / "table_reconstruct"))


def step_of(pts):
    """点列内部最大台阶（Δx<STEP_DX 内的 |Δy| 最大）。"""
    p = np.asarray(pts, float)
    if len(p) < 2:
        return 0.0
    dx, dy = np.diff(p[:, 0]), np.abs(np.diff(p[:, 1]))
    m = dx < STEP_DX
    return float(dy[m].max()) if m.any() else 0.0


def seam_jump(a, b):
    """两条链按 x 排开后的接缝竖向跳变：a 末段 y 与 b 起段 y 之差。"""
    pa, pb = np.asarray(a["pts"], float), np.asarray(b["pts"], float)
    ya = float(np.median(pa[max(0, len(pa) - 5):, 1]))
    yb = float(np.median(pb[:min(5, len(pb)), 1]))
    return abs(yb - ya)


for code in [a for a in sys.argv[1:] if a.isdigit()] or ["1027", "1040"]:
    stem = f"钻孔柱状图{code}"
    groups, _ = chains_of(stem)
    rd = json.loads((SRC / f"{stem}_行判定.json").read_text(encoding="utf-8"))
    gid = {}
    for g in groups:
        for i in g["ids"]:
            gid.setdefault(i, []).append(g)
    # 跳A：链自己带台阶（上游）
    gstep = np.array([step_of(g["pts"]) for g in groups])
    # 跳B：层界由几条链拼、拼的时候跳了多少（本阶段）
    n = len(rd["rows"])
    in_chain = np.zeros(n, bool)     # 台阶来自某条成员链内部
    seam = np.zeros(n, bool)         # 台阶来自链与链的接缝
    js = []
    for k, r in enumerate(rd["rows"]):
        mem = {id(g): g for i in r["segment_ids"] for g in gid.get(i, [])}
        mem = sorted(mem.values(), key=lambda g: float(np.mean(np.asarray(g["pts"], float)[:, 0])))
        if any(step_of(g["pts"]) > STEP for g in mem):
            in_chain[k] = True
        j = max([seam_jump(a, b) for a, b in zip(mem, mem[1:])], default=0.0)
        js.append(j)
        if j > STEP:
            seam[k] = True
    big = np.array([step_of(np.asarray(r["poly"], float)) for r in rd["rows"]]) > STEP
    rowh = float(np.median(np.diff(sorted(r["y_at_mid"] for r in rd["rows"]))))
    print(f"\n{code}: 链 {len(groups)} 条(带台阶>15px {int((gstep > STEP).sum())} 条,"
          f"最大 {gstep.max():.0f}px)  层界 {n} 条  中位行高 {rowh:.0f}px")
    print(f"    层界里有台阶: {int(big.sum())} 条 → 其中台阶在链内部(上游拼链): "
          f"{int((big & in_chain).sum())} 条;  只在接缝(6c 聚簇并错行): "
          f"{int((big & seam & ~in_chain).sum())} 条")
    order = np.argsort(-np.array(js))[:6]
    for i in order:
        if js[i] <= STEP:
            break
        r = rd["rows"][i]
        print(f"      y={r['y_at_mid']:<8} x={r['x'][0]}-{r['x'][1]:<6} 链{r['n_chains']} "
              f"接缝跳 {js[i]:.0f}px  行高 {rowh:.0f}px")
