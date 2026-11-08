# -*- coding: utf-8 -*-
"""新旧对照条带:同一 y 窗口,左=用户判定基准 6d `_外框叠加图.png`,右=本轮交付叠加图。

只为回答一件事:锯齿(碎片间断口直连)在新图上有没有消失,以及消失后线上还剩什么。
窗口按"该图无账弦最长处"自动挑,不靠我翻图。用法: python runs/tmp/cmp_old_new.py [1024 1042]
"""
import json
import sys
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from src.core import paths  # noqa: E402
from src.table import col_segments as cs  # noqa: E402

RECON = paths.RUNS_DIR / "table_reconstruct"
NEW = paths.OUTPUTS_DIR / "行列线数据集_列线分段_20260927"
H = 1400
SCALE = 0.6


def worst_y(code):
    """该图里最长的一根无账弦落在哪段 y:逐线取 pts 相邻点跨碎片且非 fills/extends 登记的最大者。"""
    stem = f"钻孔柱状图{code}"
    seg = cs.frag_points(stem)
    best = (0, 0)
    for ln in json.load(open(RECON / f"{stem}_分割线.json", encoding="utf-8"))["lines"]:
        p = np.asarray(ln["pts"], float)
        own = [{tuple(q) for q in seg[i]} for i in ln.get("_orig_ids", []) if i in seg]
        bridged = {tuple(q) for f in ln.get("fills", []) for q in f["fill"]}
        bridged |= {tuple(e) for e in ln.get("extends", []) if len(e) == 2}
        for a, b in zip(p, p[1:]):
            if abs(b[1] - a[1]) < 2 or abs(b[0] - a[0]) < 3 or tuple(a) in bridged:
                continue
            if any(tuple(a) in o and tuple(b) in o for o in own):
                continue
            d = float(np.hypot(b[0] - a[0], b[1] - a[1]))
            if d > best[0]:
                best = (d, (a[1] + b[1]) / 2)
    return best


def band(code, yc):
    stem = f"钻孔柱状图{code}"
    old = cv2.imread(str(RECON / f"{stem}_外框叠加图.png"))
    new = cv2.imread(str(NEW / "叠加图" / f"{stem}.png"))
    y0 = max(0, int(yc - H / 2))
    crop = lambda im: im[y0:y0 + H, :]                      # noqa: E731
    for tag, im in (("OLD 6d", old), ("NEW", new)):
        if im is None:
            raise FileNotFoundError(f"{tag} 读不到: {stem}")
    a, b = crop(old), crop(new)
    w = int(a.shape[1] * SCALE)
    a = cv2.resize(a, (w, int(a.shape[0] * SCALE)), interpolation=cv2.INTER_AREA)
    b = cv2.resize(b, (w, int(b.shape[0] * SCALE)), interpolation=cv2.INTER_AREA)
    lab = np.full((40, a.shape[1] * 2 + 20, 3), 40, np.uint8)
    cv2.putText(lab, f"{code} y={y0}-{y0+H}  LEFT=6d baseline (sawtooth)  RIGHT=P10 segmented",
                (8, 27), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2, cv2.LINE_AA)
    out = np.vstack([lab, np.hstack([a, np.full((a.shape[0], 20, 3), 40, np.uint8), b])])
    p = ROOT / "runs" / "tmp" / f"cmp_{code}.png"
    cv2.imwrite(str(p), out, [cv2.IMWRITE_PNG_COMPRESSION, 3])
    return p


if __name__ == "__main__":
    for code in [a for a in sys.argv[1:] if a.isdigit()] or ["1024", "1042", "1019"]:
        d, yc = worst_y(code)
        print(code, f"最长无账弦 {d:.0f}px @ y={yc:.0f} →", band(code, yc) if yc else "无弦")
