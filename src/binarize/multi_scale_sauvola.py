# -*- coding: utf-8 -*-
"""阶段1：多尺度 Sauvola 二值化（scikit-image 官方 threshold_sauvola，C 实现）。

针对超大图片（约 3200 x 20000）采用分条处理 + 重叠晕圈，控制内存峰值。
多尺度：对多个窗口尺寸分别计算 Sauvola 阈值面，取平均后二值化。

输入：data/raw_images/*.JPG（只读）
输出：data/二值处理/<同名>.png（白底=255，墨迹/文字=0）

用法：
    python src/binarize/multi_scale_sauvola.py [文件名...]
    不带参数处理全部；指定文件名只处理这些（测试用）。
"""
import sys
import time
from pathlib import Path

import numpy as np
from PIL import Image, ImageOps
from skimage.filters import threshold_sauvola

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))
from src.core import paths
from src.core.batch import run_batch

WINDOW_SIZES = [15, 31, 63, 127]  # 多尺度窗口（必须为奇数）
K = 0.2                            # Sauvola 参数 k
HALO = max(WINDOW_SIZES) // 2      # 条带重叠晕圈，消除边界效应
STRIP_H = 3000                     # 每条带高度（像素行）

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff"}


def multi_scale_sauvola(gray_strip: np.ndarray) -> np.ndarray:
    """对条带做多尺度 Sauvola，返回布尔二值图（True=前景/墨迹亮）。"""
    acc = None
    for ws in WINDOW_SIZES:
        t = threshold_sauvola(gray_strip, window_size=ws, k=K)
        acc = t if acc is None else acc + t
    acc /= len(WINDOW_SIZES)
    return gray_strip > acc


def process(path: Path):
    """处理一张图：EXIF 校正 -> 分条多尺度 Sauvola -> 保存白底黑字 PNG。

    返回 (name, ok, info)，供 run_batch 收集。
    """
    t0 = time.time()
    name = path.name
    try:
        with Image.open(path) as im:
            im = ImageOps.exif_transpose(im)  # 应用 EXIF 旋转，方向正确
            gray = np.asarray(im.convert("L"))  # 全图灰度 uint8
        H, W = gray.shape
        out = np.empty((H, W), dtype=np.uint8)
        for y0 in range(0, H, STRIP_H):
            y1 = min(y0 + STRIP_H, H)
            ys = max(y0 - HALO, 0)
            ye = min(y1 + HALO, H)
            b = multi_scale_sauvola(gray[ys:ye])
            out[y0:y1] = np.where(b[y0 - ys:y1 - ys], 255, 0)
        Image.fromarray(out).save(paths.BINARIZED_DIR / (path.stem + ".png"),
                                  compress_level=6)
        return name, True, f"{W}x{H}  {time.time() - t0:.1f}s"
    except Exception as e:
        return name, False, f"{type(e).__name__}: {e}"


def main():
    paths.ensure_dirs(paths.BINARIZED_DIR)
    files = sorted(p for p in paths.RAW_DIR.iterdir()
                   if p.is_file() and p.suffix.lower() in IMAGE_EXTS)
    if len(sys.argv) > 1:  # 只处理指定文件名（测试用）
        files = [p for p in files if p.name in sys.argv[1:]]
    # 多尺度 Sauvola 单图峰值内存 1~2GB(3000x20000 float64 多份拷贝),8 并行在
    # 16GB 机器上 MemoryError(2026-10-25 实测 24/30 失败),压到 3 并行
    run_batch(files, process, max_workers=3)


if __name__ == "__main__":
    main()
