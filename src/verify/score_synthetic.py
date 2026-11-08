# -*- coding: utf-8 -*-
"""合成门禁判分 CLI(M2a:路径显式;M2b 由链式胶水接管)。

用法:
  python src/verify/score_synthetic.py --seed 3
      → GT 自比(管线=GT 墨采样,身份映射):验判分管线头部/裁片管道,必须 PASS
  python src/verify/score_synthetic.py --seed 3 --rect-map PATH
      → 以 6f 矫正映射.json 的 lines_rect 为管线输出(经 H_rect_to_src 回扫描系)判分
"""
import argparse
import json
import sys
from pathlib import Path

import cv2
import numpy as np

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from src.core import paths
from src.verify.crops import save_violation_crops
from src.verify.gate_config import DEFAULT_THRESHOLDS
from src.verify.score_vs_gt import apply_h_rect_to_src, render_md, score_seed


def load_pipeline_from_rect_map(rect_map_path):
    """6f 矫正映射.json → 扫描系管线折线(列线/侧线/上下框)。"""
    m = json.loads(Path(rect_map_path).read_text(encoding="utf-8"))
    h = np.array(m["H_rect_to_src"], np.float64)

    def to_src(pts):
        return [list(q) for q in apply_h_rect_to_src(h, pts)]

    lr = m["lines_rect"]
    return {"columns": [to_src(c["pts"]) for c in lr["columns"]],
            "sides": {k: to_src(v) for k, v in lr["sides"].items()}}


def gt_self_pipeline(gt):
    """GT 自比:管线=GT 墨采样(断口除外),按 line_id 对号入座。"""
    def ink(line_id):
        ln = [l for l in gt["lines"] if l["line_id"] == line_id][0]
        smp = ln["samples_warp"]
        brk = ln["samples_in_break"]
        return [p for p, b in zip(smp, brk) if not b]

    n = len(gt["layout"]["col_xs"]) - 1
    return {
        "columns": [ink(l["line_id"]) for l in gt["lines"] if l["role"] == "column"],
        "sides": {"left": ink("col_0"), "right": ink(f"col_{n}"),
                  "top": ink("top"), "bottom": ink("bottom")},
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, required=True)
    ap.add_argument("--rect-map", default=None, help="6f 矫正映射.json;缺省=GT自比(管道自检)")
    ap.add_argument("--gt-dir", default=str(paths.SYNTH_GT_DIR))
    ap.add_argument("--scan-dir", default=str(paths.SYNTH_SCAN_DIR))
    ap.add_argument("--out-dir", default=str(paths.SYNTH_SCORE_DIR))
    args = ap.parse_args()

    gt_p = Path(args.gt_dir) / f"synth_{args.seed:04d}_gt.json"
    scan_p = Path(args.scan_dir) / f"synth_{args.seed:04d}.png"
    gt = json.loads(gt_p.read_text(encoding="utf-8"))
    scan = cv2.imread(str(scan_p), cv2.IMREAD_GRAYSCALE)
    assert scan is not None, f"扫描图缺失 {scan_p}"

    if args.rect_map:
        pipeline = load_pipeline_from_rect_map(args.rect_map)
        mode = f"rect_map={args.rect_map}"
    else:
        pipeline = gt_self_pipeline(gt)
        mode = "gt_self_check"

    card = score_seed(gt, pipeline, DEFAULT_THRESHOLDS)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / f"synth_{args.seed:04d}_score.json").write_text(
        json.dumps(card, ensure_ascii=False, indent=1), encoding="utf-8")
    (out_dir / f"synth_{args.seed:04d}_score.md").write_text(render_md(card), encoding="utf-8")
    crops = []
    if not card["pass"]:
        crops = save_violation_crops(scan, gt, card, out_dir / "crops")
    print(f"seed={args.seed} mode={mode} pass={card['pass']} "
          f"fail_reasons={len(card['fail_reasons'])} crops={len(crops)}")
    raise SystemExit(0 if card["pass"] else 2)


if __name__ == "__main__":
    main()
