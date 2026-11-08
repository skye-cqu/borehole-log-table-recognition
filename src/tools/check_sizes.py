# -*- coding: utf-8 -*-
"""工具：打印二值处理目录下所有 PNG 的尺寸/类型/大小，用于核对输出一致性。

用法：
    python src/tools/check_sizes.py
"""
import sys
from pathlib import Path

import cv2

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))
from src.core import paths


def main():
    for p in sorted(paths.BINARIZED_DIR.iterdir()):
        if p.is_file() and p.suffix.lower() == '.png':
            img = cv2.imread(str(p), cv2.IMREAD_GRAYSCALE)
            if img is not None:
                print(f"{p.name}: {img.shape}, dtype={img.dtype}, "
                      f"filesize={p.stat().st_size / 1024:.1f}KB")
            else:
                print(f"{p.name}: 读取失败")


if __name__ == "__main__":
    main()
