# 一次性:用现行(含 20261023 修复)分割线.json 在原图上画 1015 列线定稿,
# 替换 流程速览 第5步的米色老渲染(预览图/crop_06_列线定稿.jpg,9-05 定稿叠加图_预览,修复前)。
# 裁窗与 crop_00 同:[0:5600, 0:3200] → 800x1400;配色/线宽同 emit_line_dataset.py。
from pathlib import Path
import json
import sys

import cv2
import numpy as np

PROJ = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJ))

STEM = "1015"
RECON = PROJ / "runs/table_reconstruct"
RAW = PROJ / f"data/raw_images/钻孔柱状图{STEM}.JPG"
OUT = PROJ / f"outputs/流程速览_20261023/预览图/crop_06_列线定稿.jpg"

COL = (255, 90, 0)    # 蓝=列线
EDGE = (0, 220, 0)    # 绿=表左右边
FILL = (255, 220, 0)  # 青=有账桥接段
EXT = (0, 165, 255)   # 橙=有账外延段
W = 3

rec = json.loads((RECON / f"钻孔柱状图{STEM}_分割线.json").read_text(encoding="utf-8"))
gray = cv2.imread(str(RAW), cv2.IMREAD_GRAYSCALE)  # 灰度底,同 emit_line_dataset.overlay()
assert gray is not None, RAW
img = cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)


def poly(im, pts, col):
    a = np.rint(np.asarray(pts, float)).astype(np.int32).reshape(-1, 1, 2)
    cv2.polylines(im, [a], False, col, W, cv2.LINE_AA)


n_fill = n_ext = 0
for ln in rec["lines"]:
    col = EDGE if ln["kind"] == "edge" else COL
    poly(img, ln["pts"], col)
    for f in ln.get("fills") or []:
        pts = f["fill"] if isinstance(f, dict) else f
        poly(img, pts, FILL)
        n_fill += 1
    for e in ln.get("extends") or []:
        pts = e.get("ext") if isinstance(e, dict) else e
        if pts:
            poly(img, pts, EXT)
            n_ext += 1

txt = ("blue=col-line  green=edge LR  cyan=bridged-fill  orange=extend  "
       f"(现行 分割线.json 含 20261023 修复, fills={n_fill} ext={n_ext})")
for c, wid in (((0, 0, 0), 6), ((255, 255, 255), 2)):
    cv2.putText(img, txt, (20, 60), cv2.FONT_HERSHEY_SIMPLEX, 1.2, c, wid, cv2.LINE_AA)

crop = img[0:5600, 0:3200]
crop = cv2.resize(crop, (800, 1400), interpolation=cv2.INTER_AREA)
cv2.imwrite(str(OUT), crop, [cv2.IMWRITE_JPEG_QUALITY, 90])
print("OK", OUT, crop.shape)

acc = OUT.parent.parent / "_预览来源.json"
account = json.loads(acc.read_text(encoding="utf-8")) if acc.exists() else {}
account["crop_06_列线定稿.jpg"] = (
    f"runs/tmp/出crop06_列线定稿现行_20261024.py <- runs/table_reconstruct/钻孔柱状图{STEM}_分割线.json"
    " + data/raw_images(现行定稿,含10-23修复;米色老渲染=归档 06_列线定稿_1015.jpg)")
acc.write_text(json.dumps(account, ensure_ascii=False, indent=1), encoding="utf-8")
