# -*- coding: utf-8 -*-
"""真歪行线的离墨剖面：把 60 个采样的"离最近横线墨多少像素"打成一串，看是台阶还是爬坡。

区分两种成因（肉眼判读只算弱证据，这条是量出来的）：
  台阶 = 一段内偏移基本恒定（相邻列块各自画线、彼此错开十几像素）→ 线本身没跟错，是"一行界线在
         不同列块不在同一高度"，切格按 x 取高时各列块仍各自正确；
  爬坡 = 偏移沿 x 单调增大 → 链从真行界滑进相邻一行，是拼线跟错，得修。
用法: python runs/tmp/prof_off.py            # 默认量 off_lines_frame.json 里真歪那 9 条
      python runs/tmp/prof_off.py 1017:2500
"""
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "runs" / "tmp"))
from src.core import paths                                          # noqa: E402
import yardstick as Y                                               # noqa: E402

DEV, BAR = 6, "▁▂▄▅▆▇█"            # ▁=贴墨 ≤5px，往上一档 +5px，█=≥40px


def prof(code, y):
    stem = f"钻孔柱状图{code}"
    rd = json.loads((Y.SRC / f"{stem}_行判定.json").read_text(encoding="utf-8"))
    r = min(rd["rows"], key=lambda q: abs(q["y_at_mid"] - y))
    ruling, _ = Y.masks(stem)
    S = Y.search_of(rd.get("row_h"))
    xs, _, d = Y.samples(r, ruling, S)
    d = np.minimum(np.asarray(d, float), 2 * S)   # 无墨=半径外，按 2×半径封顶，别把 inf 喂给拟合
    bad = d > 5
    # 超差连续段：段内偏移的离散度小 = 台阶；单调上升且跨度大 = 爬坡
    runs = []
    for i, v in enumerate(bad):
        if v and (not runs or runs[-1][1] != i - 1):
            runs.append([i, i])
        elif v:
            runs[-1][1] = i
    seg = []
    for a, b in runs:
        if b - a < 3:
            continue
        s = d[a:b + 1]
        ramp = float(np.polyfit(np.arange(len(s)), s, 1)[0]) * len(s)
        seg.append(f"x{int(xs[a])}~{int(xs[b])} 偏移{s.min():.0f}~{s.max():.0f}px "
                   f"段内起伏{s.std():.1f} 斜走{ramp:+.0f}px")
    bar = "".join("×" if v >= 2 * S else BAR[min(int(v / 5), 6)] for v in d)
    return bar, seg


if __name__ == "__main__":
    tg = [a.split(":") for a in sys.argv[1:] if ":" in a] or \
         [(r["code"], str(r["y"])) for r in
          json.load(open(Path(__file__).resolve().parent / "off_lines_frame.json", encoding="utf-8"))
          if r["dev_o"] >= DEV]
    print(f"源 {Y.SRC.name}   找墨半径取半行高   ▁≤5px 每档+5px  ×=半径内无墨")
    for code, y in tg:
        bar, seg = prof(code, int(y))
        print(f"\n{code} y={y}\n  {bar}")
        for s in seg:
            print("  ", s)
