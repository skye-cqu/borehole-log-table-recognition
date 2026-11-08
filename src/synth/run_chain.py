# -*- coding: utf-8 -*-
"""合成图全链打分 CLI:合成→阶段1→6f(paths 沙箱)→ GT 记分卡。

用法:python src/synth/run_chain.py --seed 0
"""
import argparse
import json
import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from src.core import paths
from src.verify.gate_config import DEFAULT_THRESHOLDS
from src.verify.score_vs_gt import render_md, score_seed
from src.verify.score_synthetic import load_pipeline_from_rect_map


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, required=True)
    args = ap.parse_args()
    from src.synth.chain import run_chain
    gt = json.loads((paths.SYNTH_GT_DIR / f"synth_{args.seed:04d}_gt.json")
                    .read_text(encoding="utf-8"))
    scan = paths.SYNTH_SCAN_DIR / f"synth_{args.seed:04d}.png"
    work = paths.CHAIN_DIR / f"synth_{args.seed:04d}"
    res = run_chain(args.seed, gt, scan, work)
    print("stages:", res["status"])
    if res["rect_map"] is None:
        # 管线中途崩溃:空管线记分 = 全部 GT 缺线;崩溃阶段进 fail_reasons 置顶
        card = score_seed(gt, {}, DEFAULT_THRESHOLDS)
        card["fail_reasons"] = [
            f"stage_crash {k}: {v}" for k, v in res["status"].items()
            if str(v).startswith("CRASH")] + card["fail_reasons"]
        card["pass"] = False
    else:
        pipeline = load_pipeline_from_rect_map(res["rect_map"])
        card = score_seed(gt, pipeline, DEFAULT_THRESHOLDS)
    out = paths.SYNTH_SCORE_DIR
    out.mkdir(parents=True, exist_ok=True)
    (out / f"synth_{args.seed:04d}_chain_score.json").write_text(
        json.dumps(card, ensure_ascii=False, indent=1), encoding="utf-8")
    (out / f"synth_{args.seed:04d}_chain_score.md").write_text(render_md(card), encoding="utf-8")
    print(f"chain score: pass={card['pass']} fail_reasons={card['fail_reasons'][:6]}")


if __name__ == "__main__":
    main()
