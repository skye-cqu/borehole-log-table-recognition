# -*- coding: utf-8 -*-
"""记分卡组装:三族(列线/侧线/上下框)三层(结构/几何/完整性)判分,JSON+MD 双产出。

管线输入规约:已回映射到扫描系的 {"columns": [折线..], "sides": {"left/right": ..,
"frame_tb": {"top/bottom": ..}}——score_from_files 负责从 6f 矫正映射.json 读 H_rect_to_src
并回映射;单测直喂 GT 自身墨采样(身份映射)。
"""
import numpy as np

from src.verify.match import match_family

# GT 角色 → 管线族键
FAMILY_ROLES = {"columns": ["column"], "sides": ["frame_side"], "frame_tb": ["frame_tb"]}


def apply_h_rect_to_src(h, pts):
    """矫正系 (u,v) 列表 → 扫描系 (x,y) 齐次映射。"""
    h = np.asarray(h, np.float64)
    out = []
    for u, v in pts:
        w = h[2, 0] * u + h[2, 1] * v + h[2, 2]
        out.append((float((h[0, 0] * u + h[0, 1] * v + h[0, 2]) / w),
                    float((h[1, 0] * u + h[1, 1] * v + h[1, 2]) / w)))
    return out


def score_seed(gt, pipeline, th) -> dict:
    """pipeline: {"columns":[..], "sides":{"left":..,"right":..,"top":..,"bottom":..}}。

    sides 值可以是单条折线或折线列表(管线分段绘制的碎段)。
    """
    families = {}
    fail_reasons = []
    sides_in = pipeline.get("sides", {})
    for fam, roles in FAMILY_ROLES.items():
        if fam == "columns":
            polys = list(pipeline.get("columns", []))
        else:
            raw = [sides_in.get(k) for k in ("left", "right")] if fam == "sides" \
                else [sides_in.get(k) for k in ("top", "bottom")]
            polys = [p for p in raw if p is not None]
        res = match_family(gt, roles[0], polys, th)
        families[fam] = res
        if res["missing"]:
            fail_reasons.append(f"{fam}: 缺线 {res['missing']}")
        if res["extras"]:
            fail_reasons.append(f"{fam}: 多余线 {[(e['index'], round(e['x']), round(e['y']))
                                            for e in res['extras']]}")
        if res["bridged_samples"]:
            fail_reasons.append(f"{fam}: 断口桥接采样 {res['bridged_samples']}")
        if res["uncovered"]:
            fail_reasons.append(f"{fam}: 账外删除采样 {len(res['uncovered'])}")
        for r in res["lines"]:
            if r["found"] and r["dev"]["p95"] is not None and r["dev"]["p95"] > th.dev_tau:
                fail_reasons.append(
                    f"{fam}/{r['line_id']}: p95={r['dev']['p95']:.1f}px > {th.dev_tau}px")
    return {
        "schema": "synth_gate_score_v1", "seed": gt["seed"], "pass": not fail_reasons,
        "thresholds": {k: getattr(th, k) for k in th.__dataclass_fields__},
        "families": families, "fail_reasons": fail_reasons,
    }


def render_md(card) -> str:
    verdict = "PASS" if card["pass"] else "FAIL"
    rows = []
    for fam, res in card["families"].items():
        devs = [r["dev"]["p95"] for r in res["lines"]
                if r["found"] and r["dev"]["p95"] is not None]
        worst = max(devs) if devs else float("nan")
        rows.append(f"| {fam} | {len(res['lines'])} | {len(res['missing'])} | "
                    f"{len(res['extras'])} | {res['bridged_samples']} | "
                    f"{len(res['uncovered'])} | {worst:.1f} |")
    reason_lines = "\n".join(f"- {r}" for r in card["fail_reasons"]) or "- 无"
    return (f"# 合成门禁记分卡 seed={card['seed']} — **{verdict}**\n\n"
            f"| 族 | GT线数 | 缺线 | 多余 | 桥接采样 | 账外删除 | 最差p95(px) |\n"
            f"| --- | --- | --- | --- | --- | --- | --- |\n" + "\n".join(rows) +
            f"\n\n## fail 明细\n{reason_lines}\n")
