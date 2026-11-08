# 一次性:20261024 修复重跑后刷新流程速览文档图。
# 1) crop_10 系列(1035/1042 变了;1015 未动):现行叠加图顶部同窗裁片,与既有系列同规格;
# 2) 10b_修复对照_1042:柱状洞区竖带,展示"剔错轨+线性补口"现状(直补,无钩)。
from pathlib import Path

import cv2

PROJ = Path(__file__).resolve().parents[2]
LINE = PROJ / "outputs/行列线数据集_列线分段_20260927/叠加图"
OUT = PROJ / "outputs/流程速览_20261023/预览图"

for stem in ("1035", "1042"):
    img = cv2.imread(str(LINE / f"钻孔柱状图{stem}.png"))
    h, w = img.shape[:2]
    win = img[0:int(1400 * w / 800), :]
    cv2.imwrite(str(OUT / f"crop_10_行列线_{stem}.jpg"),
                cv2.resize(win, (800, 1400), interpolation=cv2.INTER_AREA),
                [cv2.IMWRITE_JPEG_QUALITY, 88])
    print(f"crop_10 {stem} OK")

# 10b:1042 数值列+柱状左缘(x 0..1150,与旧 10b 同取景;含 22° 那些行),y 5850..13850
img = cv2.imread(str(LINE / "钻孔柱状图1042.png"))
band = img[5850:13850, 0:1150]
band = cv2.resize(band, (550, int(band.shape[0] * 550 / band.shape[1])),
                  interpolation=cv2.INTER_AREA)
cv2.imwrite(str(OUT / "10b_修复对照_1042_柱状洞区_修复后.jpg"), band,
            [cv2.IMWRITE_JPEG_QUALITY, 88])
print("10b OK", band.shape)
