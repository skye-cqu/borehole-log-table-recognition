# -*- coding: utf-8 -*-
"""必错图(判定 3):对现行管线必须被判分抓出具体违规的对抗性合成配置。

4 类陷阱(设计 §6.1 v1 表);本模块实现前三类(1→6f 链可复现),
恒定x假线陷阱需 6j 级胶水(登记账本,后续)。
每类:spec 覆盖 → 合成 scan+GT → run_chain 全链 → 检查记分卡是否含预期违规。
"""
import dataclasses
import json
import sys
from pathlib import Path

import cv2
import numpy as np

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from src.core import paths
from src.synth.degrade import apply_photometric, apply_warp
from src.synth.layout import DEFAULT_SPEC, make_layout
from src.synth.make_gt import build_gt
from src.synth.render import render_clean
from src.synth.synthesize import PNG_FAST, sample_params

FAINT_COLS = ("col_3", "col_5")   # DEFAULT_SPEC.faint_cols 对应的 GT 线 id


def _synthesize(seed: int, spec, scan_path: Path, gt_path: Path) -> None:
    """与 synthesize_one 同流水线,但版式 spec 可覆盖(trap 变体)。"""
    rng = np.random.default_rng(seed)
    wp, pp = sample_params(seed)
    lay = make_layout(rng, spec)
    final = apply_photometric(apply_warp(render_clean(lay), wp), rng, pp)
    scan_path.parent.mkdir(parents=True, exist_ok=True)
    gt_path.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(scan_path), final, PNG_FAST)
    gt = build_gt(seed=seed, lay=lay, warp_params=wp, photo_params=pp,
                  shape=(final.shape[0], final.shape[1]))
    gt_path.write_text(json.dumps(gt, ensure_ascii=False), encoding="utf-8")


# 陷阱配置:名称 → (spec 覆盖, 预期违规判定 f(card)->str|None, 说明)
def _check_deco(card):
    """装饰框被误认:侧线族出现多余线或右框(col_11)缺失。"""
    s = card["families"]["sides"]
    if s["extras"]:
        return f"sides 多余线 {[(e['index'], round(e['x']), round(e['y'])) for e in s['extras']]}"
    if any(r["line_id"] == "col_11" for r in s["lines"] if not r["found"]):
        return "sides 缺线 col_11(装饰框干扰右缘重建)"
    return None


def _check_faint(card):
    """淡线被切断:淡列(col_3/col_5)被判缺线。"""
    miss = [r["line_id"] for r in card["families"]["columns"]["lines"]
            if not r["found"] and r["line_id"] in FAINT_COLS]
    return f"columns 缺淡列 {miss}" if miss else None


def _check_bridge(card):
    """断口被直线桥接:任一族出现断口桥接采样。"""
    hits = {fam: res["bridged_samples"] for fam, res in card["families"].items()
            if res["bridged_samples"]}
    return f"断口桥接采样 {hits}" if hits else None


TRAPS = {
    "deco": ({}, _check_deco,
             "装饰框紧贴右框(col_xs[-1]+80,真图1035式)——管线右缘被吸/被扰"),
    "faint": ({"faint_gray": 185}, _check_faint,
              "淡列灰度185=真图行规则线实测带内(172~196)亚阈值档——管线墨闸/二值化切断"),
    "bridge": ({"break_prob": 1.0}, _check_bridge,
               "所有线必带30~120px断口——6b趋势走廊桥接穿越断口区"),
}


def run_trap(name: str, seeds=(0, 1, 2)) -> dict:
    """跑单个陷阱的批量,返回 {'name', 'caught': n, 'seeds': [{seed, caught, evidence}]}。"""
    overrides, check, desc = TRAPS[name]
    spec = dataclasses.replace(DEFAULT_SPEC, **overrides)
    root = paths.SYNTH_DIR / "traps" / name
    from src.synth.chain import run_chain
    from src.verify.gate_config import DEFAULT_THRESHOLDS
    from src.verify.score_vs_gt import score_seed
    out = {"name": name, "desc": desc, "seeds": []}
    for seed in seeds:
        scan = root / "scans" / f"synth_{seed:04d}.png"
        gt_path = root / "gt" / f"synth_{seed:04d}_gt.json"
        if not scan.exists():
            _synthesize(seed, spec, scan, gt_path)
        gt = json.loads(gt_path.read_text(encoding="utf-8"))
        res = run_chain(seed, gt, scan, paths.CHAIN_DIR / f"trap_{name}_{seed:04d}")
        if res["rect_map"] is None:
            pipeline, ev = {}, None
        else:
            from src.verify.score_synthetic import load_pipeline_from_rect_map
            pipeline = load_pipeline_from_rect_map(res["rect_map"])
        card = score_seed(gt, pipeline, DEFAULT_THRESHOLDS)
        if res["rect_map"] is None:
            ev = f"stage_crash {[v for v in res['status'].values() if str(v).startswith('CRASH')]}"
        else:
            ev = check(card)
        out["seeds"].append({"seed": seed, "chain_status": res["status"],
                             "caught": ev is not None, "evidence": ev})
    out["caught"] = sum(1 for s in out["seeds"] if s["caught"])
    return out


def main() -> None:
    import sys
    names = sys.argv[1:] or list(TRAPS)
    report = [run_trap(n) for n in names]
    out = paths.SYNTH_SCORE_DIR / "trap_report.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")
    for t in report:
        print(f"trap {t['name']}: 抓获 {t['caught']}/{len(t['seeds'])}")
        for s in t["seeds"]:
            print(f"  seed{s['seed']}: caught={s['caught']} evidence={s['evidence']}")


if __name__ == "__main__":
    main()
