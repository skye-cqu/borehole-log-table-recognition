# -*- coding: utf-8 -*-
"""证据裁片:同一块区域,原图 vs 现行行判定叠加,给人眼看"线在,角色错"。

用法: python runs/tmp/make_evidence_crop.py 1019 6862 8629
"""
import sys
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
from core import paths                                          # noqa: E402

code, y0, y1 = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
stem = f"钻孔柱状图{code}"
gray = cv2.imread(str(paths.RAW_DIR / f"{stem}.JPG"), cv2.IMREAD_GRAYSCALE)
ov = cv2.imread(str(paths.RUNS_DIR / "table_reconstruct" / f"{stem}_行判定.png"))
x0, x1 = 200, 1750
m = 45
a = cv2.cvtColor(gray[y0 - m:y1 + m, x0:x1], cv2.COLOR_GRAY2BGR)
b = ov[y0 - m:y1 + m, x0:x1].copy()
gap = np.full((a.shape[0], 12, 3), 40, np.uint8)
img = np.hstack([a, gap, b])
k = 900 / img.shape[1]
img = cv2.resize(img, None, fx=k, fy=k, interpolation=cv2.INTER_AREA)
for txt, x in (("原图", x0), ("叠加:红=层界 橙=子行线", x0 + 12 + a.shape[1])):
    cv2.putText(img, txt, (int(x * k), 30), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 0, 255), 2)
out = paths.RUNS_DIR / "tmp" / f"证据_{code}_{y0}-{y1}.png"
cv2.imwrite(str(out), img, [cv2.IMWRITE_PNG_COMPRESSION, 6])
print(out, img.shape)
