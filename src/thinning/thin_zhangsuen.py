# -*- coding: utf-8 -*-
"""阶段2：Zhang-Suen 细化（二值处理 -> thinning）。

输入：data/二值处理/*.png（白底黑字）
输出：data/thinning/<同名>.png（黑线白底，与输入极性相反）

用法：
    python src/thinning/thin_zhangsuen.py
"""
import sys
from pathlib import Path

import cv2

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))
from src.core import paths
from src.core.batch import run_batch

IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".bmp", ".tiff", ".tif"}


def process_image(input_path: Path):
    """对单张二值图做 Zhang-Suen 细化。返回 (name, ok, info)。"""
    filename = input_path.name
    output_path = paths.THINNING_DIR / filename
    try:
        img = cv2.imread(str(input_path), cv2.IMREAD_GRAYSCALE)
        if img is None:
            return filename, False, f"无法读取图像: {input_path}"

        # 原图为白底黑线；thinning 以非零像素为前景，先反相使线条变白
        fg = cv2.bitwise_not(img)
        _, fg = cv2.threshold(fg, 127, 255, cv2.THRESH_BINARY)

        # OpenCV contrib 官方封装的 Zhang-Suen 细化算法
        thinned = cv2.ximgproc.thinning(fg, None, cv2.ximgproc.THINNING_ZHANGSUEN)

        # 反相回黑线白底，与原图极性一致
        cv2.imwrite(str(output_path), cv2.bitwise_not(thinned))
        return filename, True, "ok"
    except Exception as e:
        return filename, False, str(e)


def main():
    paths.ensure_dirs(paths.THINNING_DIR)
    image_paths = sorted(p for p in paths.BINARIZED_DIR.iterdir()
                         if p.is_file() and p.suffix.lower() in IMAGE_EXTS)
    if not image_paths:
        print(f"未在 {paths.BINARIZED_DIR} 中找到可处理的图像文件。")
        return
    run_batch(image_paths, process_image)


if __name__ == "__main__":
    main()
