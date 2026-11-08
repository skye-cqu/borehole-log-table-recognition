# -*- coding: utf-8 -*-
"""列线的标尺（不依赖人眼）：定稿列线贴不贴原图真竖线、有没有漏、有没有把图案/文字当列线。

真竖线墨 = 自适应二值 → 1×40 竖条开运算（只留足够长的竖笔画）→ 竖向闭运算接断口。
① 贴合：每条定稿列线取 60 个纵向采样，量它离最近真竖线墨的水平距离，>5px 记超差；
   超差再分两档——±60px 内有竖墨=画偏了，什么都没有=这条线在原图里不存在（用户明令禁止）。
② 漏线：按整表高度采样竖墨占比，占比高、又没有列线贴着的 x 段 = 图上有线但我们没定出来。
③ 误线：贴合超差里"无墨"那一档 + 覆盖不到表高的列线，都是"把别的当列线"的信号。

用法: python runs/tmp/yard_cols.py [1035 1040]   # 无参数=30 张
"""
import json
import sys
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from src.core import paths                                          # noqa: E402
from src.table import track_rows as tr                              # noqa: E402

SAMPLE = 60
VLEN = 40           # 竖条开运算核高(px)：短于此的竖笔算字/图案
CLOSE = 25          # 竖线被横线打断处的回接长度
SEARCH = 60
TOL = 5.0
MISS_FRAC = 0.40    # 一个 x 段在 ≥40% 的表高上有竖墨 → 图上真有一条竖线
NEAR = 12           # 列线离这条竖线 ≤12px 才算"定了它"


def vmask(stem):
    gray = cv2.imread(str(paths.RAW_DIR / f"{stem}.JPG"), cv2.IMREAD_GRAYSCALE)
    bw = (cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                cv2.THRESH_BINARY_INV, 31, 12) > 0).astype(np.uint8) * 255
    v = cv2.morphologyEx(bw, cv2.MORPH_OPEN,
                         cv2.getStructuringElement(cv2.MORPH_RECT, (1, VLEN)))
    return gray, cv2.morphologyEx(v, cv2.MORPH_CLOSE, np.ones((CLOSE, 1), np.uint8))


def chains_of(stem):
    cj = json.load(open(paths.CANDIDATE_COORD_DIR / f"{stem}.json", encoding="utf-8"))
    seg = {s["id"]: s for s in cj["lines"]
           if s["direction"] == "vertical" and s["label"] == "high"}
    fp = paths.RUNS_DIR / "table_reconstruct" / f"{stem}_列结构定稿.json"
    cols = sorted(json.load(open(fp, encoding="utf-8"))["columns"], key=lambda c: c["x_at_mid"])
    return cj, [(c, np.asarray(tr.load_chain(c, seg)[0], float)) for c in cols]


def frame_edges(stem):
    """闭合外框的左右两条边（(y,x) 点列）。约束5：外框不作列分隔线，找漏线时先排掉。"""
    fp = paths.RUNS_DIR / "table_reconstruct" / f"{stem}_闭合外框.json"
    if not fp.exists():
        return []
    d = json.load(open(fp, encoding="utf-8"))
    return [np.array([[p[1], p[0]] for p in d[k]["pts"]], float)
            for k in ("left", "right") if k in d and d[k].get("pts")]


def sheet(code):
    stem = f"钻孔柱状图{code}"
    gray, v = vmask(stem)
    H, W = v.shape
    cj, ch = chains_of(stem)
    fr = frame_edges(stem)
    y_lo = min(a[0, 0] for _, a in ch)
    y_hi = max(a[-1, 0] for _, a in ch)
    ys = np.linspace(y_lo, y_hi, 200)
    # 图上真竖线：按 x 统计这些高度上有墨的比例
    ink = (v[np.round(ys).astype(int), :] > 0).mean(axis=0)  # 每个 x 在 200 个高度上有竖墨的比例
    lines = []
    for _, a in ch:
        y0, y1 = a[0, 0], a[-1, 0]
        dev = gap = 0
        for y in np.linspace(y0, y1, SAMPLE):
            xi, yi = int(round(tr.edge_at(a, y))), int(round(y))
            lo = max(0, xi - SEARCH)
            idx = np.flatnonzero(v[yi, lo:min(xi + SEARCH, W - 1)])
            d = float(np.abs(idx + lo - xi).min()) if len(idx) else np.inf
            dev += TOL < d <= SEARCH
            gap += d > SEARCH
        n = SAMPLE
        lines.append({"x": round(float(a[len(a) // 2, 1]), 0),
                      "cov": (y1 - y0) / max(1.0, y_hi - y_lo) * 100,
                      "dev": dev / n * 100, "gap": gap / n * 100})
    xs = [l["x"] for l in lines]
    miss = []
    x = 0
    while x < W:
        if ink[x] >= MISS_FRAC:
            x2 = x
            while x2 + 1 < W and ink[x2 + 1] >= MISS_FRAC:
                x2 += 1
            c = (x + x2) // 2
            ymid = (y_lo + y_hi) / 2
            lo_f = min(tr.edge_at(f, ymid) for f in fr) if fr else 0
            hi_f = max(tr.edge_at(f, ymid) for f in fr) if fr else W
            near_col = xs and min(abs(c - u) for u in xs) <= NEAR
            # 只看表内：外框以外的是图边注记/比例尺，不是列分隔线（约束5）
            in_table = lo_f + 20 <= c <= hi_f - 20
            if in_table and not near_col:
                miss.append((c, round(ink[c] * 100)))
            x = x2 + 1
        else:
            x += 1
    return {"code": code, "n": len(lines), "lines": lines,
            "bad": [l for l in lines if l["dev"] + l["gap"] > 10],
            "gaps": [l for l in lines if l["gap"] > 5],
            "short": [l for l in lines if l["cov"] < 90],
            "miss": miss, "h": H}


tot = dict(n=0, bad=0, gap=0, short=0, miss=0)
for code in [a for a in sys.argv[1:] if a.isdigit()] or \
        sorted(p.stem[-4:] for p in paths.CANDIDATE_COORD_DIR.glob("*.json")):
    d = sheet(code)
    tot["n"] += d["n"]
    tot["bad"] += len(d["bad"])
    tot["gap"] += len(d["gaps"])
    tot["short"] += len(d["short"])
    print(f"{code}: 列线{d['n']:>3}  超差10%+{len(d['bad']):>3}  其中图上无竖墨{len(d['gaps']):>3}"
          f"  覆盖<90%{len(d['short']):>3}  漏定竖线{len(d['miss']):>3}")
    for l in sorted(d["bad"], key=lambda u: -(u["dev"] + u["gap"]))[:4]:
        print(f"      x={l['x']:<5.0f} 覆盖{l['cov']:>3.0f}%  画偏{l['dev']:>3.0f}%"
              f"  无墨{l['gap']:>3.0f}%")
    for l in sorted(d["short"], key=lambda u: u["cov"])[:4]:
        print(f"      覆盖不足: x={l['x']:<5.0f} 只盖到表高{l['cov']:>3.0f}%")
    for m in sorted(d["miss"], key=lambda u: -u[1])[:4]:
        print(f"      漏: x={m[0]:<5} 竖墨占表高{m[1]:>3.0f}%  最近列线>{NEAR}px")
print(f"合计: 列线{tot['n']}  超差{tot['bad']}  含无墨档{tot['gap']}  覆盖不足{tot['short']}")
