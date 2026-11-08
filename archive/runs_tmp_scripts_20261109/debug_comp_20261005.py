# -*- coding: utf-8 -*-
"""项④反例诊断裁片:对指定 (图, sub_y) 复现走查,画预测轨迹/锚点/邻行,出放大条带。

用法: python runs/tmp/debug_comp_20261005.py  (CASES 写死在文件头)
红=上下邻行折线 绿=预测轨迹 蓝=墨锚 橙=sub原点 黄=柱状带边界
"""
import json
import sys
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from src.core import paths
from src.table import track_group, track_rows

CASES = [  # (编号, sub_y, 说明)
    (1017, 3143, "负:run162"),
    (1017, 3249, "负:run162"),
    (1021, 1556, "负:run56"),
    (1031, 15310, "负:run115"),
    (1032, 16419, "负:run95"),
    (1034, 15462, "负:run75"),
    (1024, 17495, "正:run36漏"),
]

for num, y_target, tag in CASES:
    stem = f"钻孔柱状图{num}"
    out = json.load(open(paths.RUNS_DIR / "table_reconstruct" / f"{stem}_行判定.json",
                         encoding="utf-8"))
    rows = out["rows"]
    sub = min((s for s in out["sub_rows"]), key=lambda s: abs(s["y_at_mid"] - y_target))
    if abs(sub["y_at_mid"] - y_target) > 3:
        print(f"{stem} y={y_target}: 找不到 sub(最近 {sub['y_at_mid']})")
        continue
    W, E, _ = track_rows.content_band(stem)
    gray = cv2.imread(str(paths.RAW_DIR / f"{stem}.JPG"), cv2.IMREAD_GRAYSCALE)
    lw = track_rows._era_line_width(rows, track_group.binarize(gray, track_group.PARAMS).T)
    ys_all = np.asarray([r["y_at_mid"] for r in rows], float)
    order = np.argsort(ys_all)
    idx = int(np.searchsorted(ys_all[order], sub["y_at_mid"]))
    top, bot = rows[order[idx - 1]], rows[order[idx]]
    pt, bt = np.asarray(top["poly"], float), np.asarray(bot["poly"], float)
    sp = np.asarray(sub["poly"], float)
    x_ref = float(np.median(sp[:, 0]))
    y_ref = float(np.interp(x_ref, sp[:, 0], sp[:, 1]))
    ytt = float(track_rows._era_row_ys(pt, [x_ref])[0])
    ybt = float(track_rows._era_row_ys(bt, [x_ref])[0])
    tt = (y_ref - ytt) / (ybt - ytt) if ybt > ytt else 0.5
    k0, k1 = max(0, idx - 4), min(len(rows), idx + 3)
    x_w = int(np.median([rows[j]["x"][0] for j in order[k0:k1]]))
    x_e = int(np.median([rows[j]["x"][1] for j in order[k0:k1]]))

    def ypred(x):
        return float(track_rows._era_row_ys(pt, [x])[0]) + tt * (
            float(track_rows._era_row_ys(bt, [x])[0]) - float(track_rows._era_row_ys(pt, [x])[0]))

    thick = track_rows.ERA_THICK * lw
    anchors = []
    for sgn, xa, xb in ((1, int(sub["x"][1]) + 1, x_e), (-1, int(sub["x"][0]) - 1, x_w)):
        x = xa
        while (x <= xb) if sgn > 0 else (x >= xb):
            y = ypred(x)
            if not track_rows._chord_in_band(W, E, y, x):
                r, yc = track_rows._era_ink_run(gray[:, x], y)
                if 0 < r <= thick and abs(yc - y) <= track_rows.ERA_DRIFT:
                    anchors.append((x, float(yc)))
                elif r > thick:
                    x2 = x + sgn
                    while ((x2 <= xb) if sgn > 0 else (x2 >= xb)) and abs(x2 - x) <= 200 \
                            and track_rows._era_ink_run(gray[:, x2], ypred(x2))[0] > thick:
                        x2 += sgn
                    x = x2 - sgn
            x += sgn
    # 画:x 300~2450,y 以轨迹为中心 ±55
    x_lo, x_hi = 240, 2450
    xs = np.arange(x_lo, x_hi)
    ys_tr = np.array([ypred(x) for x in xs])
    y_mid = float(np.median(ys_tr))
    y0, y1 = int(y_mid - 55), int(y_mid + 55)
    crop = cv2.imread(str(paths.RAW_DIR / f"{stem}.JPG"), cv2.IMREAD_GRAYSCALE)[y0:y1, x_lo:x_hi]
    viz = cv2.cvtColor(crop, cv2.COLOR_GRAY2BGR)
    for r, c in ((pt, (0, 0, 255)), (bt, (0, 0, 255)), (sp, (0, 165, 255))):
        for a, b in zip(r[:-1], r[1:]):
            cv2.line(viz, (int(a[0]) - x_lo, int(a[1]) - y0), (int(b[0]) - x_lo, int(b[1]) - y0),
                     c, 2, cv2.LINE_AA)
    traj = np.array([[int(x) - x_lo, int(ypred(x)) - y0] for x in xs if y0 <= ypred(x) <= y1])
    for a, b in zip(traj[:-1], traj[1:]):
        cv2.line(viz, tuple(a), tuple(b), (0, 255, 0), 1, cv2.LINE_AA)
    for x, yc in anchors:
        cv2.circle(viz, (x - x_lo, int(yc) - y0), 2, (255, 0, 0), -1)
    if W is not None:
        for edge, c in ((W, (0, 255, 255)), (E, (0, 255, 255))):
            ew = np.interp(np.arange(y0, y1), edge[:, 0], edge[:, 1]).astype(int) - x_lo
            for yy, xx in zip(range(y1 - y0), ew):
                if 0 <= xx < x_hi - x_lo:
                    viz[yy, xx] = c
    scale = 2
    viz = cv2.resize(viz, (viz.shape[1] * scale, viz.shape[0] * scale),
                     interpolation=cv2.INTER_NEAREST)
    p = paths.RUNS_DIR / "tmp" / "项④反例_20261005" / f"{num}_y{int(y_target)}_{tag.split(':')[0]}.png"
    p.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(p), viz)
    print(f"{stem} y={y_target} [{tag}]: 锚 {len(anchors)}, run_w={sum(1 for _ in anchors) and ''}"
          f"lw={lw:.1f} 轨迹y={y_mid:.0f} → {p.name}")
