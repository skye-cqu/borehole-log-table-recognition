# -*- coding: utf-8 -*-
"""fail 违规点放大裁片:扫描图原貌 + GT 线叠加,一违规点一图(大图验收三件套的自动化)。"""
from pathlib import Path

import cv2
import numpy as np

CROP = 512   # 裁片半边长 px(全分辨率)


def save_violation_crops(scan, gt, card, out_dir, scale=2) -> list:
    """对 card 内账外删除点出裁片;返回写入路径列表(每种子最多 20 张,防爆炸)。"""
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    vis = cv2.cvtColor(scan, cv2.COLOR_GRAY2BGR)
    for ln in gt["lines"]:
        if ln["role"] == "row":
            continue
        pts = np.array(ln["samples_warp"], np.int32).reshape(-1, 1, 2)
        color = (255, 128, 0) if ln["role"] in ("frame_side", "frame_tb") else (0, 0, 255)
        cv2.polylines(vis, [pts], False, color, 2)
    h, w = scan.shape[:2]
    spots = [(v["x"], v["y"], f"uncovered_{v['line_id']}")
             for fam in card["families"].values() for v in fam["uncovered"]]
    spots += [(e["x"], e["y"], f"extra_{e['index']}")
              for fam in card["families"].values() for e in fam["extras"]]
    written = []
    for k, (x, y, tag) in enumerate(spots[:20]):
        x0, x1 = max(0, int(x) - CROP), min(w, int(x) + CROP)
        y0, y1 = max(0, int(y) - CROP), min(h, int(y) + CROP)
        crop = vis[y0:y1, x0:x1]
        crop = cv2.resize(crop, (crop.shape[1] * scale, crop.shape[0] * scale),
                          interpolation=cv2.INTER_NEAREST)
        p = out / f"crop_{k:02d}_{tag}_{int(x)}_{int(y)}.png"
        cv2.imwrite(str(p), crop)
        written.append(str(p))
    return written
