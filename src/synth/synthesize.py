# -*- coding: utf-8 -*-
"""编排器:seed → 版式/断口/参数 → 干净图 → 弯曲 → 光度 → 三件产物(扫描图/GT/预览)。

用法:python src/synth/synthesize.py --start 0 --seeds 10   (run_batch 并行)
"""
import argparse
import sys
from pathlib import Path

import cv2
import numpy as np

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))
from src.core import paths
from src.core.batch import run_batch
from src.synth.degrade import PhotoParams, WarpParams, apply_photometric, apply_warp
from src.synth.layout import DEFAULT_SPEC, make_layout
from src.synth.make_gt import build_gt, save_gt
from src.synth.render import render_clean

GT_BLUE, GT_RED = (255, 128, 0), (0, 0, 255)
PNG_FAST = [int(cv2.IMWRITE_PNG_COMPRESSION), 1]   # 68MP 全幅 PNG,压缩级 1 保 60s 预算
# 并行度推导(2026-09-13 实测):68.6MP 单种子峰值 RSS=3.02GB(bleed=True 最坏种子,psutil
# 采样);本机 15.7GB×0.8 预算=12.6GB → 12.6/3.02=4.2 → 4 进程。8 进程(半核默认)曾
# 6/10 OOM(账本 M1.T9)。100 张批 4 进程 ≈6min < 15min 预算。
SYNTH_MAX_WORKERS = 4


def spec_for(seed: int):
    """版式钩子:画布尺寸唯一来源是 spec 本身。v1 恒标准全幅版式;变体在 M1.5 校准后接入。"""
    return DEFAULT_SPEC


def sample_params(seed: int):
    rng = np.random.default_rng(seed)
    wp = WarpParams(
        amp1=float(rng.uniform(20, 60)), wl1=float(rng.uniform(7000, 10000)),
        ph1=float(rng.uniform(0, 2 * np.pi)),
        amp2=float(rng.uniform(8, 18)), wl2=float(rng.uniform(2500, 4000)),
        ph2=float(rng.uniform(0, 2 * np.pi)),
        tilt=float(rng.uniform(-40, 40)),
    )
    pp = PhotoParams(blur_sigma=float(rng.uniform(0, 1.5)),
                     noise_sigma=float(rng.uniform(0, 6)),
                     bleed=bool(rng.random() < 0.7), lighting=bool(rng.random() < 0.8))
    return wp, pp


def synthesize_one(seed: int, out_root=None):
    root = Path(out_root) if out_root else paths.SYNTH_DIR
    scan_dir, gt_dir, prev_dir = (root / "scans", root / "gt", root / "preview")
    paths.ensure_dirs(scan_dir, gt_dir, prev_dir)
    try:
        rng = np.random.default_rng(seed)
        wp, pp = sample_params(seed)
        lay = make_layout(rng, spec_for(seed))
        clean = render_clean(lay)
        warped = apply_warp(clean, wp)
        final = apply_photometric(warped, rng, pp)
        name = f"synth_{seed:04d}"
        cv2.imwrite(str(scan_dir / f"{name}.png"), final, PNG_FAST)
        gt = build_gt(seed=seed, lay=lay, warp_params=wp, photo_params=pp,
                      shape=(final.shape[0], final.shape[1]))
        save_gt(gt, gt_dir)
        _save_preview(final, gt, prev_dir / f"{name}_preview.png")
        return (name, True, f"{final.shape[1]}x{final.shape[0]} "
                            f"lines={len(lay.lines)} cells={len(gt['cells'])}")
    except Exception as exc:  # noqa: BLE001
        return (f"synth_{seed:04d}", False, repr(exc))


def _save_preview(final: np.ndarray, gt: dict, out_path) -> None:
    vis = cv2.cvtColor(final, cv2.COLOR_GRAY2BGR)
    for ln in gt["lines"]:
        pts = np.array([[int(round(x)), int(round(y))] for x, y in ln["polyline_warp"]],
                       np.int32).reshape(-1, 1, 2)
        color = GT_BLUE if ln["role"] in ("frame_side", "frame_tb") else GT_RED
        cv2.polylines(vis, [pts], False, color, 2)
    h, w = vis.shape[:2]
    half = cv2.resize(vis, (w // 2, h // 2), interpolation=cv2.INTER_AREA)
    cv2.imwrite(str(out_path), half, PNG_FAST)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", type=int, default=0)
    ap.add_argument("--seeds", type=int, default=10)
    args = ap.parse_args()
    results = run_batch(list(range(args.start, args.start + args.seeds)), synthesize_one,
                        max_workers=SYNTH_MAX_WORKERS)
    fails = [r for r in results if not r[1]]
    raise SystemExit(1 if fails else 0)


if __name__ == "__main__":
    main()
