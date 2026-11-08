# -*- coding: utf-8 -*-
"""M1.T0:门禁合成链在 68.6MP(3280x20941)上的性能验证,GO/NO-GO。

预算:单种子全链(弯曲 remap + 光度退化) <= 60s => GO。
用法:python src/synth/perf_check.py
"""
import time
import numpy as np
import cv2

W, H = 3280, 20941


def make_test_image() -> np.ndarray:
    img = np.full((H, W), 255, np.uint8)
    for x in range(200, 2920, 240):
        cv2.line(img, (x, 150), (x, 14050), 60, 4)
    for y in range(450, 14050, 900):
        cv2.line(img, (200, y), (2920, y), 60, 3)
    return img


def timed(label: str, fn) -> float:
    t0 = time.time()
    fn()
    dt = time.time() - t0
    print(f"{label}: {dt:.2f}s")
    return dt


def main() -> None:
    img = make_test_image()
    total = 0.0

    def warp() -> None:
        yy, xx = np.meshgrid(np.arange(H, dtype=np.float32),
                             np.arange(W, dtype=np.float32), indexing="ij")
        disp = (40 * np.sin(2 * np.pi * yy / 8000.0)).astype(np.float32)
        map_x, map_y = xx - disp, yy
        cv2.remap(img, map_x, map_y, cv2.INTER_LINEAR)

    def blur() -> None:
        cv2.GaussianBlur(img, (0, 0), 1.0)

    total += timed("warp(cv2.remap+场构造)", warp)
    total += timed("blur", blur)

    try:
        from augraphy.augmentations import BleedThrough, LightingGradient, SubtleNoise
        from augraphy.base import AugmentationSequence

        def aug() -> None:
            seq = AugmentationSequence([BleedThrough(), LightingGradient(), SubtleNoise()])
            seq(img)

        total += timed("augraphy(3个非几何增强子)", aug)
    except Exception as exc:  # noqa: BLE001
        print(f"augraphy 失败: {exc!r}")
        total += 999.0

    verdict = "GO" if total <= 60 else "NO-GO"
    print(f"\n总计 {total:.2f}s => {verdict}(预算 60s)")


if __name__ == "__main__":
    main()
