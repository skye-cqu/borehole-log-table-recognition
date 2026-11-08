# -*- coding: utf-8 -*-
"""物理退化。几何只有一条路:自研位移场,图像与 GT 用同一函数变换
(M0 约束:Augraphy 几何类增强器不回传坐标映射,禁用于门禁路径)。

约定:dst(x,y) = src(x - disp_x(x,y), y - disp_y(x,y)),故理想点 p 在结果图中的
新位置 = p + disp(p)——warp_point 与 remap 严格一致,有往返自检测试保证。
"""
from dataclasses import dataclass

import cv2
import numpy as np


@dataclass(frozen=True)
class WarpParams:
    amp1: float
    wl1: float
    ph1: float     # 主弯曲(长波)
    amp2: float
    wl2: float
    ph2: float     # 次弯曲(短波)
    tilt: float    # 总倾斜 px(右端相对左端 y 位移)


def displacement(shape, p: WarpParams):
    """全幅位移场。注意与 warp_point 公式逐项同源(往返自检测试强制)。"""
    h, w = shape
    yy, xx = np.meshgrid(np.arange(h, dtype=np.float32),
                         np.arange(w, dtype=np.float32), indexing="ij")
    disp_x = p.amp1 * np.sin(2 * np.pi * yy / p.wl1 + p.ph1) \
        + p.amp2 * np.sin(2 * np.pi * yy / p.wl2 + p.ph2)
    disp_y = p.tilt * (xx - w / 2.0) / w
    return disp_x.astype(np.float32), disp_y.astype(np.float32), yy, xx


def apply_warp(img: np.ndarray, p: WarpParams) -> np.ndarray:
    disp_x, disp_y, yy, xx = displacement(img.shape, p)
    return cv2.remap(img, xx - disp_x, yy - disp_y, cv2.INTER_LINEAR,
                     borderMode=cv2.BORDER_CONSTANT, borderValue=255)


def warp_point(x: float, y: float, p: WarpParams, shape) -> tuple[float, float]:
    h, w = shape   # 与 displacement 同源,保证 GT 映射与 remap 严格一致
    dx = p.amp1 * float(np.sin(2 * np.pi * y / p.wl1 + p.ph1)) \
        + p.amp2 * float(np.sin(2 * np.pi * y / p.wl2 + p.ph2))
    dy = p.tilt * (x - w / 2.0) / w
    return (float(x + dx), float(y + dy))


def warp_polyline(pts, p: WarpParams, shape):
    return [warp_point(x, y, p, shape) for x, y in pts]


@dataclass(frozen=True)
class PhotoParams:
    blur_sigma: float
    noise_sigma: float
    bleed: bool        # 自研透印(Augraphy BleedThrough 68.6MP 批量 OOM,PROVEN-DEAD 见 M1.T9)
    lighting: bool     # 自研 OpenCV 光照梯度(Augraphy LightingGradient 68.6MP OOM,PROVEN-DEAD)


def _lighting_gradient(img: np.ndarray, rng: np.random.Generator) -> np.ndarray:
    """自研灰度不均:随机圆心大尺度径向衰减乘法(代替 OOM 的 Augraphy LightingGradient)。"""
    h, w = img.shape
    cx, cy = rng.uniform(0, w), rng.uniform(0, h)
    yy, xx = np.meshgrid(np.arange(h, dtype=np.float32),
                         np.arange(w, dtype=np.float32), indexing="ij")
    r = np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2) / np.hypot(w, h)
    gain = 0.65 + 0.35 * np.clip(r / rng.uniform(0.3, 0.8), 0, 1)  # 中心亮 1.0 → 边缘 ≥0.65
    return np.clip(img.astype(np.float32) * gain, 0, 255).astype(np.uint8)


def _bleed_through(img: np.ndarray, rng: np.random.Generator) -> np.ndarray:
    """自研透印:背面墨迹=整页镜像+重模糊,按低对比 alpha 压暗正面。

    单通道 uint8/float32 实现,68MP 峰值内存 <1GB(Augraphy 内部三通道 float64
    多副本 1.65GB/份,8 进程批量 OOM,PROVEN-DEAD)。确定性由 rng 直控。
    """
    ghost = cv2.GaussianBlur(cv2.flip(img, -1), (0, 0), float(rng.uniform(6, 12)))
    alpha = np.float32(rng.uniform(0.1, 0.2))
    out = img.astype(np.float32)
    out -= alpha * (np.float32(255.0) - ghost.astype(np.float32))
    return np.clip(out, 0, 255).astype(np.uint8)


def apply_photometric(img: np.ndarray, rng: np.random.Generator, pp: PhotoParams) -> np.ndarray:
    out = img
    if pp.blur_sigma > 0:
        k = int(pp.blur_sigma * 4) * 2 + 1
        out = cv2.GaussianBlur(out, (k, k), pp.blur_sigma)
    if pp.noise_sigma > 0:
        noise = rng.standard_normal(out.shape, dtype=np.float32) * np.float32(pp.noise_sigma)
        out = np.clip(out.astype(np.float32) + noise, 0, 255).astype(np.uint8)
    if pp.lighting:
        out = _lighting_gradient(out, rng)
    if pp.bleed:
        out = _bleed_through(out, rng)
    return np.ascontiguousarray(out)
