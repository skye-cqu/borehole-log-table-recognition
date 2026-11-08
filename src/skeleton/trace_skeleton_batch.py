# -*- coding: utf-8 -*-
"""阶段3：对 thinning 结果执行 LingDong-/skeleton-tracing，输出 polylines 坐标 + 可视化图。

- 算法：官方 SWIG 封装的 C 版本；Windows/Python 3.12运行时位于 src/vendor/
- 输入：data/thinning/*.png（黑线白底，Zhang-Suen 细化结果）
- 输出：
    data/LingDong-skeleton-tracing处理/坐标数据/<name>.json
    data/LingDong-skeleton-tracing处理/可视化图/<name>.png

用法：
    python src/skeleton/trace_skeleton_batch.py
"""
import json
import sys
from pathlib import Path

import cv2
import numpy as np

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))
from src.core import paths
from src.core.batch import run_batch

IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".bmp", ".tiff", ".tif"}

# 已验证的Windows/Python 3.12运行时。
# 上游源码仍保留在 src/third_party/skeleton-tracing，但运行时不再污染子模块。
SWIG_DIR = str(
    _PROJECT_ROOT / "src" / "vendor" / "skeleton_tracing_py312_win_amd64"
)


def process_image(input_path: Path):
    """对单张细化图执行 skeleton tracing，输出坐标 JSON + 可视化 PNG。

    返回 (name, ok, info)。
    """
    filename = input_path.name
    stem = input_path.stem
    coord_path = paths.SKELETON_COORD_DIR / f"{stem}.json"
    viz_path = paths.SKELETON_VIZ_DIR / f"{stem}.png"

    try:
        # 确保子进程能 import 官方 SWIG 扩展
        if SWIG_DIR not in sys.path:
            sys.path.insert(0, SWIG_DIR)
        import trace_skeleton

        img = cv2.imread(str(input_path), cv2.IMREAD_GRAYSCALE)
        if img is None:
            return filename, False, "无法读取图像"

        # 反相：线条(0)->非零(前景)，背景(255)->0
        # from_numpy 以非零像素为前景，且会原地修改数组，故传副本
        fg = cv2.bitwise_not(img)
        polys = trace_skeleton.from_numpy(fg.copy())

        # ---- 坐标数据 (JSON) ----
        # 格式：{"image": <name>, "width": W, "height": H,
        #        "num_polylines": N, "num_points": M,
        #        "polylines": [[ [x,y], [x,y], ... ], ...]}
        num_points = sum(len(p) for p in polys)
        coord_data = {
            "image": filename,
            "width": int(img.shape[1]),
            "height": int(img.shape[0]),
            "num_polylines": len(polys),
            "num_points": num_points,
            "polylines": [[[int(x), int(y)] for (x, y) in p] for p in polys],
        }
        with open(coord_path, "w", encoding="utf-8") as f:
            json.dump(coord_data, f, ensure_ascii=False)

        # ---- 可视化图 (PNG) ----
        # 白底随机彩色绘制 polylines，便于人工区分不同线段
        viz = np.full_like(img, 255)
        rng = np.random.RandomState(0)  # 固定种子保证可复现
        for poly in polys:
            color = int(rng.randint(0, 256))
            pts = np.array(poly, dtype=np.int32)
            cv2.polylines(viz, [pts], False, color, 1, cv2.LINE_8)
        cv2.imwrite(str(viz_path), viz)

        return filename, True, f"polylines={len(polys)} points={num_points}"
    except Exception as e:
        return filename, False, f"{type(e).__name__}: {e}"


def main():
    paths.ensure_dirs(paths.SKELETON_COORD_DIR, paths.SKELETON_VIZ_DIR)
    image_paths = sorted(p for p in paths.THINNING_DIR.iterdir()
                         if p.is_file() and p.suffix.lower() in IMAGE_EXTS)
    if not image_paths:
        print(f"未在 {paths.THINNING_DIR} 中找到可处理的图像文件。")
        return
    print(f"使用官方 SWIG C 扩展：{SWIG_DIR}")
    run_batch(image_paths, process_image)


if __name__ == "__main__":
    main()
