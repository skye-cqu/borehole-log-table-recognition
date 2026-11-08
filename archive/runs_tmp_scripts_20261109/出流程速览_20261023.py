# 一次性:汇总管线各阶段典型叠加图到 outputs/流程速览_20261023/预览图。
# 小图原样复制;>5MB 的整图半分辨率转 JPG。来源账落 _预览来源.json。可重复跑(幂等)。
import json
import shutil
import sys
from pathlib import Path

import cv2

PROJ = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJ))
from src.core import paths  # noqa: E402

ARCHIVE = Path(r"D:\Skye\Documents\Work\高维智矿_资料库\归档资料\7.13杂活废弃产物")
PACK = ARCHIVE / "runs/阶段巡检包_20260923"
TRECON = ARCHIVE / "runs/table_reconstruct"
ATMP = ARCHIVE / "runs/tmp"
RTMP = paths.TMP_DIR
ERA = paths.ERA_CHAR_DIR
LINE = paths.OUTPUTS_DIR / "行列线数据集_列线分段_20260927" / "叠加图"

OUT = paths.SPEEDVIEW_DIR / "预览图"
OUT.mkdir(parents=True, exist_ok=True)
account, misses = {}, []

for st, t in [("钻孔柱状图1015", "1015"), ("钻孔柱状图1035", "1035"), ("钻孔柱状图1042", "1042")]:
    for src, dest in [
        (PACK / st / "00_原图.JPG", f"00_原图_{t}.jpg"),
        (PACK / st / "01_二值化.png", f"01_二值化_{t}.png"),
        (PACK / st / "02_细化.png", f"02_细化_{t}.png"),
        (PACK / st / "03_骨架追踪叠加.png", f"03_骨架追踪叠加_{t}.png"),
        (PACK / st / "12_行线判定.jpg", f"04_阶段4候选直画_{t}.jpg"),
        (PACK / st / ("05_纵向主框架叠加.png" if (PACK / st / "05_纵向主框架叠加.png").exists()
                     else "05_主分隔线拟合叠加.png"), f"05_纵向主框架_{t}.jpg"),
        (TRECON / f"{st}_定稿叠加图_预览.jpg", f"06_列线定稿_{t}.jpg"),
        (PACK / st / "08_闭合外框叠加.png", f"07_闭合外框_{t}.jpg"),
        (PACK / st / "10_表格矫正核对.png", f"08_表格矫正核对_{t}.jpg"),
        (PACK / st / "11_行列结构叠加.png", f"09_矫正系结构叠加_{t}.jpg"),
        (LINE / f"{st}.png", f"10_行列线现行_{t}.jpg"),
    ]:
        if not src.exists():
            misses.append(str(src))
            continue
        big = src.stat().st_size > 5 * 2**20 and src.suffix.lower() in {".png", ".jpg", ".jpeg"}
        if big:
            img = cv2.imread(str(src), cv2.IMREAD_COLOR)
            if img is None:
                misses.append(str(src))
                continue
            img = cv2.resize(img, (img.shape[1] // 2, img.shape[0] // 2), interpolation=cv2.INTER_AREA)
            d = (OUT / dest).with_suffix(".jpg")
            cv2.imwrite(str(d), img, [cv2.IMWRITE_JPEG_QUALITY, 82])
        else:
            d = OUT / dest
            shutil.copy2(src, d)
        account[d.name] = str(src)

extra = [
    (RTMP / "眼验_1015_采长r44-50.png", "11_内容_眼验_1015_采长r44-50.png"),
    (RTMP / "1033复核_x25_c7.png", "11_内容_复核_1033_x25.png"),
    (RTMP / "眼验_1033_倾角抽5格.png", "11_内容_眼验_1033_倾角抽5格.png"),
    (ERA / "钻孔柱状图1015" / "montage.png", "12_时代列montage_1015.png"),
    (ERA / "钻孔柱状图1023" / "montage.png", "12_时代列montage_1023.png"),
    (ERA / "钻孔柱状图1035" / "montage.png", "12_时代列montage_1035.png"),
    (ERA / "钻孔柱状图1015" / "字_00_y906.png", "12_时代列单字_1015_字00.png"),
    (ATMP / "合并验收_1015_r9-r20区域.png", "13_合并验收_1015_层号倾角r9-r20.png"),
    (ATMP / "合并验收_1015_倾角区.png", "13_合并验收_1015_倾角区.png"),
    (ATMP / "era视觉包v2_20261002" / "钻孔柱状图1015_时代行拼图.png", "13_时代合并_1015_拼图.png"),
    (ATMP / "项④核验包_20261005" / "1015_y8298.png", "10b_项④补全行_1015_y8298.png"),
    (ATMP / "项③弦包_20261005" / "钻孔柱状图1015_y12290_弦对比.png", "10b_项③弦修复_1015_y12290.png"),
    (RTMP / "mixline_20261022" / "1035_关键1比1_y898.png", "14_混轨_1035_关键.png"),
    (RTMP / "mixline_20261022" / "1023_关键1比1_y11122.png", "14_混轨_1023_关键.png"),
    (RTMP / "c1032_depth_r9.png", "14_1032截断_深度行r9.png"),
    (RTMP / "d1032_depth_trunc.png", "14_1032截断_整列普查.png"),
    (RTMP / "e1032_depth.png", "14_1032截断_深度列.png"),
]
mix42 = sorted((RTMP / "mixline_20261022").glob("1042_关键*.png"))
if mix42:
    extra.append((mix42[0], "14_混轨_1042_关键.png"))
else:
    k19 = sorted((RTMP / "mixline_20261022").glob("1019_关键*.png"))
    if k19:
        extra.append((k19[0], "14_混轨_1019_关键.png"))
for st in ("1023", "1035"):
    g = sorted((ERA / f"钻孔柱状图{st}").glob("字_00_*.png"))
    if g:
        extra.append((g[0], f"12_时代列单字_{st}_字00.png"))

for src, dest in extra:
    if not src.exists():
        misses.append(str(src))
        continue
    shutil.copy2(src, OUT / dest)
    account[dest] = str(src)

(OUT.parent / "_预览来源.json").write_text(
    json.dumps(account, ensure_ascii=False, indent=1), encoding="utf-8")
print(f"OK {len(account)} 张;缺 {len(misses)}:")
for m in misses:
    print("  MISS", m)
