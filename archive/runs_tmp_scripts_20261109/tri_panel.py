# -*- coding: utf-8 -*-
"""人眼核验片：同一块区域三栏并排 = 原图 | 旧判据叠加 | 新判据叠加。

自动选窗：新层界最密而旧层界最稀的那一段（最能暴露差别的窗口）。
用法: python runs/tmp/tri_panel.py 1019 [1018 1030 1035 ...]
产物 runs/tmp/三态_<code>.png
"""
import json
import sys
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from src.core import paths                                          # noqa: E402

OLD = ROOT / "rollback" / "行判定_旧判据_20260923"
WIN = 1500


def load(p):
    return json.loads(Path(p).read_text(encoding="utf-8"))


def draw(base, d, color_new):
    im = base.copy()
    for r in d["rows"]:
        cv2.line(im, (int(r["x"][0]), int(r["y_at_mid"])),
                 (int(r["x"][1]), int(r["y_at_mid"])), color_new, 5, cv2.LINE_AA)
    for r in d.get("sub_rows", []):
        cv2.line(im, (int(r["x"][0]), int(r["y_at_mid"])),
                 (int(r["x"][1]), int(r["y_at_mid"])), (0, 140, 255), 3, cv2.LINE_AA)
    return im


def pick_window(new, old):
    """滑窗：新线数 − 旧线数 最大的窗口。"""
    ny = [r["y_at_mid"] for r in new["rows"]]
    oy = [r["y_at_mid"] for r in old["rows"]]
    best = (0, 0, 0)
    for y in sorted(set(ny)):
        a = sum(1 for v in ny if y <= v < y + WIN)
        b = sum(1 for v in oy if y <= v < y + WIN)
        if a - b > best[0]:
            best = (a - b, y, a)
    return best[1], best[1] + WIN, best[0], best[2]


for code in sys.argv[1:] or ["1019"]:
    stem = f"钻孔柱状图{code}"
    new = load(paths.RUNS_DIR / "table_reconstruct" / f"{stem}_行判定.json")
    old = load(OLD / f"{stem}_行判定.json")
    y0, y1, gain, nnew = pick_window(new, old)
    gray = cv2.imread(str(paths.RAW_DIR / f"{stem}.JPG"), cv2.IMREAD_GRAYSCALE)
    base = cv2.imread(str(paths.TRACK_GROUP_OVERLAY_DIR / f"{stem}.png"))
    x0, x1 = int(new["table_x"][0]), int(new["table_x"][1])
    y0, y1, m = int(y0), int(y1), 40
    p = [cv2.cvtColor(gray[y0 - m:y1 + m, x0:x1], cv2.COLOR_GRAY2BGR),
         draw(base, old, (200, 200, 0))[y0 - m:y1 + m, x0:x1],
         draw(base, new, (0, 0, 255))[y0 - m:y1 + m, x0:x1]]
    gap = np.full((p[0].shape[0], 10, 3), 40, np.uint8)
    img = np.hstack([p[0], gap, p[1], gap, p[2]])
    k = 1500 / img.shape[1]
    img = cv2.resize(img, None, fx=k, fy=k, interpolation=cv2.INTER_AREA)
    for i, t in enumerate(("原图",
                           f"旧判据 全表{len(old['rows'])}条",
                           f"新判据 全表{len(new['rows'])}条")):
        cv2.putText(img, t, (int((i * (p[0].shape[1] + 10)) * k) + 6, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 0, 255), 2)
    out = paths.RUNS_DIR / "tmp" / f"三态_{code}.png"
    cv2.imwrite(str(out), img, [cv2.IMWRITE_PNG_COMPRESSION, 6])
    print(f"{code}: 窗口 y={y0:.0f}-{y1:.0f} 窗内新{nnew}条/比旧多{gain}条 "
          f"全表 旧{len(old['rows'])}→新{len(new['rows'])} → {out.name}")
