"""项1 视觉核验包: 行判定叠加图上柱状带/水文带窗 1:1 裁片。

用法: python runs/tmp/render_band_pack.py 1015 1027
每图出: 带窗各 3 个高度(上/中/下三等分) 1:1 裁片 + 全表半分辨率 1 张。
窗口 = 带缘内外各留 140px(柱状带) / 200px(水文带), 裁片上注明 y 范围。
判读口径: 助手渲染, 供用户/视觉判读核验, 不作"正确"结论依据。
"""
import sys, json
from pathlib import Path
import numpy as np
import cv2

sys.path.insert(0, ".")
from src.core import paths

OUT = Path("runs/tmp/带掩膜视觉包_20260930")

# 本轮修复区的定点窗 (y中心, x0, x1, 标签)——带窗按三等分取不到的 specific 修复点
EXTRA = {
    "1042": [(15000, 280, 2480, "岩性区行尾修复")],
    "1035": [(17400, 2100, 2620, "深段行尾与带界(已知限制区)")],
    "1028": [(17206, 250, 2900, "底框东段重建")],
    "1015": [(17760, 250, 2900, "表底与框外装饰带")],
}


def crops(stem):
    j = json.loads((paths.RUNS_DIR / "table_reconstruct" / f"钻孔柱状图{stem}_行判定.json")
                   .read_text(encoding="utf-8"))
    bands = [(np.array(b[0], float), None if b[1] is None else np.array(b[1], float))
             for b in j.get("bands", [])]
    # 干净底图：原扫描 + 行判定折线，不带阶段3 追踪轨迹（那些彩色曲线是底图可视化，
    # 不是行检测输出，混在核验包里会干扰肉眼判读——2026-09-30 visual-judge 判读教训）
    from src.table import track_rows as tr
    viz = cv2.imread(str(paths.RAW_DIR / f"钻孔柱状图{stem}.JPG"))
    viz = cv2.cvtColor(viz, cv2.COLOR_GRAY2BGR) if viz.ndim == 2 else viz
    for r in j["rows"]:
        tr._draw_poly(viz, r["poly"], (0, 0, 255), 5)
    for r in j["sub_rows"]:
        tr._draw_poly(viz, r["poly"], (0, 140, 255), 3)
    ys_all = [r["y_at_mid"] for r in j["rows"]]
    y_lo, y_hi = int(min(ys_all)), int(max(ys_all))
    n = 0
    for bi, (w, e) in enumerate(bands, 1):
        wx0 = int(w[:, 1].min()) - (60 if e is not None else 200)
        wx1 = (int(e[:, 1].max()) + 60) if e is not None else int(w[:, 1].min()) + 620
        for tag, yq in [("上", 0.25), ("中", 0.5), ("下", 0.75)]:
            yc = int(y_lo + (y_hi - y_lo) * yq)
            c = viz[max(yc - 500, 0):yc + 500, max(wx0, 0):wx1]
            if c.size == 0:
                continue
            fp = OUT / f"{stem}_带{bi}_{tag}_y{yc}.png"
            cv2.imwrite(str(fp), c)
            print(fp, c.shape[1], "x", c.shape[0])
            n += 1
    for yc, x0, x1, tag in EXTRA.get(stem, []):
        c = viz[max(yc - 550, 0):yc + 550, max(x0, 0):x1]
        if c.size:
            fp = OUT / f"{stem}_定点_{tag}_y{yc}.png"
            cv2.imwrite(str(fp), c)
            print(fp, c.shape[1], "x", c.shape[0])
            n += 1
    half = cv2.resize(viz, (viz.shape[1] // 2, viz.shape[0] // 2), interpolation=cv2.INTER_AREA)
    fp = OUT / f"{stem}_全表_半分辨率.jpg"
    cv2.imwrite(str(fp), half, [cv2.IMWRITE_JPEG_QUALITY, 88])
    print(fp)
    return n


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    for s in sys.argv[1:]:
        print(f"== {s}: {crops(s)} 张裁片")
