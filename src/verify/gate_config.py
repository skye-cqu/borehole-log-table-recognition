# -*- coding: utf-8 -*-
"""门禁阈值冻结载体。改任何值必须:先实测推导 → 登记 gate_ledger → 再改这里(AGENTS.md 门禁约束)。

初始值推导(2026-09-13,均挂既有实测):
- dev_tau=3px:goal 判定 2 初始值,取现行管线两先例中位——line_check 全线贴合 p95≤2.5px、
  6g 切口贴线 p95≤5px;
- detect_tau=15px:线级"存在性"判定半径,=5×dev_tau,容忍采样离散步进与线宽(4~6px)之半;
- match_min_found_frac=0.95:一条 GT 线 95% 墨采样达标才算"找到"(与 goal 的 95% 口径一致);
- extra_frac=0.5:管线折线过半点距全体 GT 墨采样 >detect_tau 判"无中生有";
- sample_step=20px:GT 采样步长,保证 3px 偏差窗口内不漏采(远小于线宽与判定半径)。
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class GateThresholds:
    sample_step: float = 20.0
    dev_tau: float = 3.0
    detect_tau: float = 15.0
    match_min_found_frac: float = 0.95
    extra_frac: float = 0.5


DEFAULT_THRESHOLDS = GateThresholds()
