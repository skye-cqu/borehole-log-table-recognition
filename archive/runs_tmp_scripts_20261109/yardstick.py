# -*- coding: utf-8 -*-
"""标尺（不依赖任何人眼判断）：拿原扫描图自己的墨迹量两条硬指标。

把二值图做一次"横条开运算"(核 40×1) → 只留下足够长的水平笔画 = 表格横线墨迹(ruling)。
剩下的短小连通域 = 字(glyph)。

指标A 贴合误差(px)：画的层界折线在采样 x 处，离最近的 ruling 墨迹多远。
    >5px 的采样占比 = 用户定的容差红线。
    采样处 ±60px 内根本找不到横线墨 = 这条线走过一张图上没有横线的地方，按超差计入。
    （2026-09-24 收紧：早先版本把"找不到墨"的采样丢出分母，只量找得到墨的地方，
      结果把坏线报得很干净——1017 同一批线，松口径 8 条超差、硬口径 57 条。）
    线级两档：处处≤5px = 60 个采样一个都不超；
              贴合线 = 超差采样 ≤10%。差在链断口：桥接段横跨无墨空隙，
              那里根本找不到横线墨（采样距离顶到 60px 搜索窗），不是线画歪了。
指标B 压字率(%)：画的线(±2px)穿过 glyph 墨迹的采样占比 → "线条挡住文字"的客观读数。

用法: python runs/tmp/yardstick.py [1019 1035 ...]   # 无参数=30 张
"""
import json
import os
import sys
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from src.core import paths                                          # noqa: E402
from src.table.track_rows import row_y                              # noqa: E402

SAMPLE = 60
RULING_LEN = 40
SEARCH = 60
CLOSE = 0 if os.environ.get("YARD_NOCLOSE") else 25   # 横线断口回接长度(px)，关掉可对照
POLY_TOL = 5.0        # 用户容差：拟合折线离成员链原点的残差上限(px)
# 同一把尺子也可量重生成前的旧判据快照：YARD=old python runs/tmp/yardstick.py
# YARD=nopoly = 同一批线、同一把尺，只把表征换回"一条水平线"→ 隔离表征这一项的贡献
OLD = ROOT / "rollback" / "行判定_旧判据_20260923"
# YARD_SRC=目录 直接量任意一批 行判定.json（门禁阈值 A/B 的每档落一个目录，同一把尺子）
SRC = (Path(os.environ["YARD_SRC"]) if os.environ.get("YARD_SRC")
       else OLD if os.environ.get("YARD") == "old"
       else paths.RUNS_DIR / "table_reconstruct")
NOPOLY = os.environ.get("YARD") == "nopoly"


def line_y(rec, x):
    """这条线在 x 处的高度：新表征走折线，旧快照没有 poly 就还是那根水平线。
    尺子调的是生产代码同一个函数，量的是"画出来/切格用"的那条线，不留两套口径。"""
    return rec["y_at_mid"] if NOPOLY or not rec.get("poly") else row_y(rec, x)


def search_of(row_h):
    """找墨的搜索半径。原来固定 ±60px，可 60px 就约等于一个行距：行界一断口，尺子就抓到
    相邻一行的线，把"图上本来没横线"报成"线画偏了"(实测 1017/1020/1024 那几条平直 59px
    偏移全是这么来的)。收到半行高——越过半行的墨属于另一行，不该替本行背锅。
    YARD_SEARCH=60 退回旧口径对照。"""
    return float(os.environ.get("YARD_SEARCH") or min(SEARCH, 0.5 * (row_h or 2 * SEARCH)))


def samples(rec, ruling, S):
    """一条线 → (采样 x, 该处线高, 离最近横线墨的距离; inf=半径内根本没有墨)。
    标尺/成因分类/剖面三处共用这一份采样，改口径只改这里，不留第二套读数。"""
    x0, x1 = int(rec["x"][0]), int(rec["x"][1])
    W, S = ruling.shape[1], int(S)
    xs = np.linspace(x0 + 10, min(x1 - 10, W - 2), SAMPLE)
    ys, ds = [], []
    for x in xs:
        xi, y = int(x), line_y(rec, x)
        lo = max(0, int(y) - S)
        idx = np.flatnonzero(ruling[lo:int(y) + S, xi])
        ys.append(y)
        ds.append(float(np.abs(idx + lo - y).min()) if len(idx) else np.inf)
    return xs, ys, ds


def masks(stem):
    gray = cv2.imread(str(paths.RAW_DIR / f"{stem}.JPG"), cv2.IMREAD_GRAYSCALE)
    bw = (cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                cv2.THRESH_BINARY_INV, 31, 12) > 0).astype(np.uint8) * 255
    ruling = cv2.morphologyEx(bw, cv2.MORPH_OPEN,
                              cv2.getStructuringElement(cv2.MORPH_RECT, (RULING_LEN, 1)))
    # 横线被竖线/曲线打断 1~3px 时，40px 开运算会连带吃掉断口两侧各 ~20px；
    # 闭一次把这种断口接回去，否则采样落在打断处 = 冤枉线画歪。YARD_NOCLOSE=1 可关掉对照。
    if CLOSE:
        ruling = cv2.morphologyEx(ruling, cv2.MORPH_CLOSE, np.ones((1, CLOSE), np.uint8))
    # glyph = 全部墨迹 减去 长横笔(含其 ±2px 厚度带)→ 剩下的是字/短笔。
    # 不减厚度带的话：短横线段没被开运算留下、却被算成"字"，压线在正确位置也报压字。
    band = cv2.dilate(ruling, np.ones((5, 1), np.uint8))
    return ruling, cv2.subtract(bw, band)


def measure(code):
    stem = f"钻孔柱状图{code}"
    rd = json.loads((SRC / f"{stem}_行判定.json").read_text(encoding="utf-8"))
    ruling, glyph = masks(stem)
    fit, cross, good, near, bad_lines, noline, overs = [], 0, 0, 0, 0, 0, []
    nsamp = 0
    S = search_of(rd.get("row_h"))
    for r in rd["rows"]:
        xs, ysv, ds = samples(r, ruling, S)
        for xi, y in zip((int(x) for x in xs), ysv):
            if glyph[int(y) - 2:int(y) + 3, xi].any():
                cross += 1
        nsamp += len(ds)
        ys = ds                                 # inf = 半径内无墨，下面按最大超差计入
        fin = [v for v in ys if np.isfinite(v)]
        fit += fin
        if len(fin) < SAMPLE * 0.5:
            noline += 1                      # 过半采样找不到横线墨：桥接过长，另记一档
        # 找不到墨 = 这条线走过一张图上没有横线的地方，按最大超差计入（旧版把它丢出分母，偏松）
        over = float(np.mean([not np.isfinite(v) or v > 5.0 for v in ys]))
        overs.append(over * 100)
        if over == 0.0:
            good += 1                        # 60 个采样处处 ≤5px
        if over <= 0.10:
            near += 1                        # 超差采样 ≤10%
        else:
            bad_lines += 1
    fit = np.array(fit)
    fr = [r.get("fit_res", 0.0) for r in rd["rows"]]
    return {"code": code, "n": len(rd["rows"]), "samples": len(fit),
            "med": float(np.median(fit)), "p90": float(np.percentile(fit, 90)),
            "max": float(fit.max()), "over5": float((fit > 5).mean() * 100),
            "ink": len(fit) / max(nsamp, 1) * 100, "over": float(np.mean(overs)),
            "good": good, "near": near, "bad_lines": bad_lines, "noline": noline,
            "fit_res": max(fr), "fit_over": sum(f > POLY_TOL for f in fr),
            "cross": cross / max(nsamp, 1) * 100}


def main():
    codes = [a for a in sys.argv[1:] if a.isdigit()] or \
            sorted(p.stem[-4:] for p in paths.CANDIDATE_COORD_DIR.glob("*.json"))
    print(f"源 {SRC.name}   样本 {SAMPLE}px/线  容差 {POLY_TOL:.0f}px")
    print(f"{'张':<6}{'层界':>5}{'有墨采样%':>9}{'贴合中位':>9}{'p90':>6}{'离墨采样%':>10}"
          f"{'处处≤5px':>10}{'贴合线≥90%':>11}{'超差':>6}{'压字率%':>8}{'拟合残差':>9}{'残差超5':>8}")
    rows = [measure(c) for c in codes]
    for m in rows:
        print(f"{m['code']:<6}{m['n']:>5}{m['ink']:>9.0f}{m['med']:>9.1f}{m['p90']:>6.0f}"
              f"{m['over']:>10.0f}{m['good']:>10}{m['near']:>11}{m['bad_lines']:>6}"
              f"{m['cross']:>8.1f}{m['fit_res']:>9.1f}{m['fit_over']:>8}")
    a = np.array([[m['ink'], m['med'], m['p90'], m['over'], m['cross']] for m in rows])
    print(f"{'合计':<5}{sum(m['n'] for m in rows):>5}" +
          f"{a[:,0].mean():>9.0f}{a[:,1].mean():>9.1f}{a[:,2].mean():>6.0f}{a[:,3].mean():>10.0f}"
          f"{sum(m['good'] for m in rows):>10}"
          f"{sum(m['near'] for m in rows):>11}{sum(m['bad_lines'] for m in rows):>6}"
          f"{a[:,4].mean():>8.1f}{max(m['fit_res'] for m in rows):>9.1f}"
          f"{sum(m['fit_over'] for m in rows):>8}")


if __name__ == "__main__":
    main()
