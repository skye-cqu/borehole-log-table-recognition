# -*- coding: utf-8 -*-
"""全阶段产物巡检包:把每张图在管线各阶段的输出收进一个目录,供用户逐阶段排查。

布局: runs/阶段巡检包_20260923/钻孔柱状图XXXX/
  00_原图.JPG                       data/raw_images(只读,硬链接)
  01_二值化.png                     data/二值处理(多尺度 Sauvola)
  02_细化.png                       data/thinning(Zhang-Suen)
  03_骨架追踪线段.json              阶段3 坐标数据(折线段)
  03_骨架追踪叠加.png               由线段 JSON 重渲染(红线白底,全分辨率)
  04_表格线候选.json                阶段4 候选线段坐标
  05_主分隔线拟合叠加.png           阶段5 拟合结果叠原图
  05_列线清洗叠加.png               列线清洗与结构识别(仅 1015/1027/1035/1044)
  05_纵向主框架叠加.png             纵向主框架恢复(仅 1015/1027/1035/1044)
  06_列线定稿叠加.png               列结构定稿叠原图(用户核验对象)
  07_全竖线叠加.png                 全竖线判定叠加
  08_闭合外框叠加.png               外框闭合叠加
  09_表格清洗.png                   表格主体清洗图(含 8 保留列)
  10_表格矫正核对.png               矫正图+左缘并排核对
  11_行列结构叠加.png               矫正系 行列网格 叠加
  12_行线判定.jpg                   行线判定(仅 26 张人审图)
  20_读数_agnes.json                Agnes 条带读数
  21_读数_单格重读.json             分歧格单格重读
  22_列结构定稿.json                列边界定稿(用户核验)
  23_待核清单.json                  分级/处置台账
  30_终版Excel.xlsx                 26 张=还原.xlsx;4 张补产=还原_补产终版.xlsx
  31_补产草案.xlsx                  仅 4 张补产(重建前草案,对照用)
根目录另放: README_巡检指南.md、视觉核验决策_20260916.json(4 张 409 格裁决台账)、
  repair_1032.py / repair_1042.py(结构重建脚本)。

实现: 已有产物一律 os.link 硬链接(零拷贝,文件夹挪动时自动变实体拷贝);
  缺失阶段在 README 的覆盖表中标注"未留存",不阻塞其余阶段。

用法: python src/tools/stage_audit_pack.py [编号 ...]   # 无参数=全 30 张
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))
from src.core import paths  # noqa: E402

import cv2  # noqa: E402

CODES = [f"{n}" for n in range(1015, 1045)]
TR = paths.RUNS_DIR / "table_reconstruct"
ACCEPT = paths.RUNS_DIR / "验收包"


def link(src: Path, dst: Path) -> bool:
    if not src.exists():
        return False
    dst.parent.mkdir(parents=True, exist_ok=True)
    if dst.exists():
        return True
    try:
        os.link(src, dst)
    except OSError:
        import shutil
        shutil.copy2(src, dst)
    return True


def render_skeleton(code: str, dst: Path) -> bool:
    src = paths.SKELETON_COORD_DIR / f"钻孔柱状图{code}.json"
    if not src.exists():
        return False
    d = json.loads(src.read_text(encoding="utf-8"))
    w, h = d["width"], d["height"]
    canvas = 255 * __import__("numpy").ones((h, w), dtype="uint8")
    for pl in d["polylines"]:
        pts = __import__("numpy").array(pl, dtype="int32")
        cv2.polylines(canvas, [pts], False, 0, 1)
    red = __import__("numpy").full((h, w, 3), 255, dtype="uint8")
    red[canvas == 0] = (0, 0, 255)
    dst.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(dst), red)
    return True


def collect(code: str) -> list[str]:
    stem = f"钻孔柱状图{code}"
    out = paths.STAGE_AUDIT_DIR / stem
    rows = []

    def put(stage: str, src: Path, name: str | None = None, alts=()):
        src = next((c for c in (src, *alts) if c.exists()), src)   # 同阶段产物有异名
        ok = link(src, out / (name or src.name))
        rows.append((stage, name or src.name, "√" if ok else "未留存"))

    put("00 原图", paths.RAW_DIR / f"{stem}.JPG", "00_原图.JPG")
    put("01 二值化", paths.BINARIZED_DIR / f"{stem}.png", "01_二值化.png")
    put("02 细化", paths.THINNING_DIR / f"{stem}.png", "02_细化.png")
    put("03 骨架追踪线段", paths.SKELETON_COORD_DIR / f"{stem}.json",
        "03_骨架追踪线段.json")
    viz = out / "03_骨架追踪叠加.png"
    if viz.exists() or render_skeleton(code, viz):
        rows.append(("03 骨架追踪叠加", viz.name, "√(重渲染)"))
    else:
        rows.append(("03 骨架追踪叠加", viz.name, "未留存"))
    put("04 表格线候选", paths.PROJECT_ROOT / "data/表格线候选识别处理/坐标数据"
        / f"{stem}.json", "04_表格线候选.json")
    put("05 主分隔线拟合叠加",
        paths.PROJECT_ROOT / "data/主分隔线拟合/叠加可视化图" / f"{stem}.png",
        "05_主分隔线拟合叠加.png")
    put("05 列线清洗叠加",
        paths.PROJECT_ROOT / "data/列线清洗与结构识别/叠加可视化图" / f"{stem}.png",
        "05_列线清洗叠加.png")
    put("05 纵向主框架叠加",
        paths.PROJECT_ROOT / "data/纵向主框架恢复/叠加可视化图" / f"{stem}.png",
        "05_纵向主框架叠加.png")
    put("06 列线定稿叠加", TR / f"{stem}_定稿叠加图.png", "06_列线定稿叠加.png")
    put("07 全竖线叠加", TR / f"{stem}_全竖线叠加图.png", "07_全竖线叠加.png")
    put("08 闭合外框叠加", TR / f"{stem}_闭合外框叠加图.png", "08_闭合外框叠加.png")
    put("09 表格清洗", ACCEPT / "表格清洗预览" / f"{stem}_表格清洗.png",
        "09_表格清洗.png")
    put("10 表格矫正核对", TR / f"{stem}_表格矫正_核对.png", "10_表格矫正核对.png")
    put("11 行列结构叠加", TR / f"{stem}_矫正结构叠加.png", "11_行列结构叠加.png")
    put("12 行线判定", ACCEPT / "行线" / f"{code}_行线判定.jpg", "12_行线判定.jpg")
    put("20 读数_agnes", TR / f"{stem}_agnes读数.json", "20_读数_agnes.json",
        alts=(TR / f"{stem}_agnes验收.json",))   # 26 张只有 验收 版
    put("21 读数_单格重读", TR / f"{stem}_单格重读.json", "21_读数_单格重读.json")
    put("22 列结构定稿", TR / f"{stem}_列结构定稿.json", "22_列结构定稿.json")
    put("23 待核清单", TR / f"{stem}_待核清单.json", "23_待核清单.json")
    final = TR / (f"{stem}_还原_补产终版.xlsx" if code in ("1018", "1030", "1032",
                                                           "1042")
                  else f"{stem}_还原.xlsx")
    put("30 终版Excel", final, "30_终版Excel.xlsx")
    if code in ("1018", "1030", "1032", "1042"):
        put("31 补产草案(重建前)", TR / f"{stem}_还原_补产草案.xlsx",
            "31_补产草案.xlsx")
    return rows


def main():
    argv = [a for a in sys.argv[1:] if a.isdigit()]
    codes = argv or CODES
    paths.ensure_dirs(paths.STAGE_AUDIT_DIR)
    for name in ("视觉核验决策_20260916.json", "repair_1032.py", "repair_1042.py"):
        src = TR / "视觉核验_20260916" / name
        if name == "视觉核验决策_20260916.json":
            src = TR / name
        link(src, paths.STAGE_AUDIT_DIR / name)
    cover: dict[str, dict[str, str]] = {}
    for code in codes:
        rows = collect(code)
        cover[code] = {stage: st for stage, _, st in rows}
        print(f"{code}: " + " ".join(f"{s.split()[0]}{st}" for s, _, st in rows))
    (paths.STAGE_AUDIT_DIR / "覆盖表.json").write_text(
        json.dumps(cover, ensure_ascii=False, indent=1), encoding="utf-8")
    print("覆盖表 ->", paths.STAGE_AUDIT_DIR / "覆盖表.json")


if __name__ == "__main__":
    main()
