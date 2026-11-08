# -*- coding: utf-8 -*-
"""门禁阈值 A/B：同一把尺子量 5 种组合，看"抓歪"和"误杀真行"各吃掉多少。

每档 subprocess 跑 track_rows（环境变量在 import 期读，必须换进程），产物 JSON
按档挪到 runs/tmp/ab/，再与 rollback/行判定_门禁前_20260924 的层界按 y±12px 对齐，
分"保住/丢了/新增"。丢了的才是代价，抓没抓到 1027 y=10886 那条 6.6% 爬升链单独点名。
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from src.core import paths  # noqa: E402

OUT = ROOT / "runs" / "tmp" / "ab"
BASE = ROOT / "rollback" / "行判定_门禁前_20260924"
TR = ROOT / "src" / "table" / "track_rows.py"
VARIANTS = [                                  # (名字, SKEW, RISE_FRAC)
    ("默认 3%+抖1/4行", "0.03", "0.25"),
    ("只斜率 3%", "0.03", "99"),
    ("只斜率 5%", "0.05", "99"),
    ("5%+抖1/4行", "0.05", "0.25"),
    ("只抖 1/4行", "9", "0.25"),
    ("无门禁", "9", "99"),
]


def load(p):
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def run(code, skew, rise, tag):
    env = dict(os.environ, SKEW=skew, RISE_FRAC=rise)
    subprocess.run([sys.executable, str(TR), code], env=env, cwd=ROOT,
                   check=True, capture_output=True)
    d = paths.RUNS_DIR / "table_reconstruct"
    dst = OUT / f"{tag}.json"
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy(d / f"钻孔柱状图{code}_行判定.json", dst)
    return load(dst)


def matched(base_rows, rows, tol=12.0):
    """贪心按 y 对齐：返回 (保住的基数, 丢, 新增)。"""
    used = set()
    keep = 0
    for b in base_rows:
        for i, r in enumerate(rows):
            if i in used or abs(r["y_at_mid"] - b["y_at_mid"]) > tol:
                continue
            used.add(i)
            keep += 1
            break
    return keep, len(base_rows) - keep, len(rows) - keep


def ramped(o):
    """1027 那条祸害：斜率离中位 >4% 的层界还有几条。"""
    return [r for r in o["rows"] if abs(r.get("slope", 0)) > 0.04]


for code in ("1027", "1040"):
    b = load(BASE / f"钻孔柱状图{code}_行判定.json")
    nb = len(b["rows"])
    print(f"\n=== {code}  门禁前层界 {nb}，链 {b['n_chains']} ===")
    print(f"{'档位':<16}{'层界':>5}{'保住':>5}{'丢了':>5}{'新增':>5}"
          f"{'剔链':>5}{'偏线':>5}{'行高':>5}{'容差':>5}{'歪层界':>6}")
    for tag, skew, rise in VARIANTS:
        o = run(code, skew, rise, f"{code}_{tag}")
        k, lost, new = matched(b["rows"], o["rows"])
        print(f"{tag:<16}{len(o['rows']):>5}{k:>5}{lost:>5}{new:>5}"
              f"{o['n_chains_stepped']:>5}{len(o['off_grid']):>5}"
              f"{o['row_h']:>5.0f}{o['step_tol']:>5.0f}{len(ramped(o)):>6}")
