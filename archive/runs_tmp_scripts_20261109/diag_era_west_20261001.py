"""诊断: 行线为什么没覆盖地质时代列(用户 2026-10-01 提出全图同症)。

三步:
1) 原图墨迹: 取若干行线, 沿 x 从链西端往西走到框外, 逐 x 测行线高度 ±6px 内有无墨,
   报"连续墨迹实际到达的最西 x"——行线墨在原图上到底断在哪。
2) 阶段4 段: 西端 <500 的横向段按标签列出 x 范围/长度/y——西侧那截墨在阶段4 是什么身份。
3) 行判定链: 对应行的 poly 西端与成员 segment_ids。

用法: python runs/tmp/diag_era_west_20261001.py 1015 1042
"""
import json, sys
sys.path.insert(0, ".")
import numpy as np
import cv2
from src.core import paths

B = paths.RUNS_DIR / "table_reconstruct"
INK_THR = 200          # 淡规则线实测灰度 172~196(行线检测教训), 取 200 宽口径
Y_TOL = 6


def row_ink_west(gray, poly, x_from, x_to):
    """沿折线高度往西逐 x 测墨, 容 3px 小缺口, 返回连续墨到达的最西 x 与墨迹 x 集合。"""
    p = np.asarray(poly, float)
    xs = np.arange(x_from, x_to - 1, -1)
    ink_xs = []
    for x in xs:
        if x < p[0, 0]:                       # 链西端以西: 按链最西两点斜率外推高度
            dx = p[0, 0] - p[1, 0]
            y = p[0, 1] + (p[0, 1] - p[1, 1]) / dx * (p[0, 0] - x) if dx else p[0, 1]
        else:
            y = float(np.interp(x, p[:, 0], p[:, 1]))
        y0, y1 = int(y - Y_TOL), int(y + Y_TOL + 1)
        col = gray[max(y0, 0):y1, max(int(x) - 1, 0):int(x) + 2]
        if col.size and col.min() < INK_THR:
            ink_xs.append(int(x))
    if not ink_xs:
        return None, []
    runs, cur = [], [ink_xs[0], ink_xs[0]]
    for a, b in zip(ink_xs, ink_xs[1:]):
        if a - b <= 3:
            cur[1] = b
        else:
            runs.append(tuple(cur))
            cur = [b, b]
    runs.append(tuple(cur))
    best = max(runs, key=lambda r: r[0] - r[1])
    return best[1], runs


def main(stem):
    d = json.loads((B / f"钻孔柱状图{stem}_行判定.json").read_text(encoding="utf-8"))
    fr = json.loads((B / f"钻孔柱状图{stem}_闭合外框.json").read_text(encoding="utf-8"))
    Lx = [p[0] for p in fr["left"]["pts"]]
    cj = json.loads((paths.CANDIDATE_COORD_DIR / f"钻孔柱状图{stem}.json").read_text(encoding="utf-8"))
    print(f"== {stem}: tab_l={d['table_x'][0]} 左框x[{min(Lx)},{max(Lx)}] "
          f"col0={json.loads((B/f'钻孔柱状图{stem}_列结构定稿.json').read_text(encoding='utf-8'))['columns'][0]['x_at_mid']}")
    gray = cv2.imread(str(paths.RAW_DIR / f"钻孔柱状图{stem}.JPG"), cv2.IMREAD_GRAYSCALE)
    rows = d["rows"]
    picks = [rows[i] for i in np.linspace(0, len(rows) - 1, 5).astype(int)]
    for r in picks:
        w0 = r["x"][0]
        wx, runs = row_ink_west(gray, r["poly"], w0, 60)
        print(f"  行 y={r['y_at_mid']:7.1f} 链西端={w0:4} 墨连续到 x={wx}  墨 runs(西←东前6): {runs[:6]}")
    print("  -- 阶段4 横向段 西端<500:")
    segs = [s for s in cj["lines"] if s["direction"] == "horizontal"
            and min(p[0] for p in s["points"]) < 500]
    segs.sort(key=lambda s: (min(p[1] for p in s["points"]), min(p[0] for p in s["points"])))
    for s in segs[:60]:
        xs = [p[0] for p in s["points"]]
        ys = [p[1] for p in s["points"]]
        print(f"    id={s['id']:>6} {s['label']:>7} x[{min(xs):4},{max(xs):4}] len={s['length']:6.0f} y[{min(ys)},{max(ys)}]")


if __name__ == "__main__":
    for s in sys.argv[1:]:
        main(s)
