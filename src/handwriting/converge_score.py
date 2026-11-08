# -*- coding: utf-8 -*-
"""收敛分级打分器(segment5 主指标,零参考)。

对候选表全部非空 desc 格,用图上多源读数(RapidOCR 窄/宽/拼字 + Agnes + 行带窗)
按 multisource_grade 同款相似度聚类投票,按"候选值与最强读簇的收敛关系"打分:

  印证现值  双族1.0 / 单族双几何0.7 / 同族多数0.4 / 分裂0.1
  读截断(候选更全,截断守卫) 0.8 / 0.6 / 0.3 / 0.1
  矛盾现值 / 无收敛 / 读数不足  0.0

输出 METRIC conv=<mean> 与分项计数(仅落 LOG);不读参考表,不写任何表。
"""
import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from openpyxl import load_workbook  # noqa: E402

from src.core import paths  # noqa: E402
from src.handwriting import rules as R  # noqa: E402
from src.handwriting.rules import _xn  # noqa: E402  # 变体等价归一(与判读采纳守卫同口径)
from src.handwriting.multisource_grade import (  # noqa: E402
    RATIO, _clusters, _ratio)
from src.handwriting.normalizers import norm_desc  # noqa: E402

TIER_W = {"可信(双族)": 1.0, "可信(单族双几何)": 0.7, "同族多数": 0.4, "分裂": 0.1}


def main():
    bridge = R._bridge()
    ms = json.loads((paths.AUTORESEARCH_DIR / "multisource_reads.json")
                    .read_text(encoding="utf-8"))
    rsp = paths.AUTORESEARCH_DIR / "rowstrip_reads.json"
    strip = json.loads(rsp.read_text(encoding="utf-8")) if rsp.exists() else {}
    rs_p = paths.AUTORESEARCH_DIR / "agnes_resweep.json"
    resweep = json.loads(rs_p.read_text(encoding="utf-8")) if rs_p.exists() else {}
    cl_p = paths.AUTORESEARCH_DIR / "colreads.json"
    colread = json.loads(cl_p.read_text(encoding="utf-8")) if cl_p.exists() else {}

    tiers, rels = Counter(), Counter()
    total, s_sum = 0, 0.0
    judged = R._judged_map()
    for p in sorted(paths.AUTORESEARCH_CANDIDATE_DIR.glob("*_整合.xlsx")):
        stem = p.name[: -len("_整合.xlsx")]
        rows = list(load_workbook(p, read_only=True).active.iter_rows(values_only=True))
        dcol = R.resolve_roles(rows[0]).get("desc")
        if dcol is None:
            continue
        rk_map = ms.get(stem, {})
        rs_map = resweep.get(stem, {})
        br_map = bridge.get(stem, {})
        st_map = strip.get(stem, {})
        cl_map = colread.get(stem, {})
        for i, row in enumerate(rows[1:]):
            r = i + 2
            cur_n = _xn(row[dcol] if dcol < len(row) else None)
            if not cur_n:
                continue
            jd = judged.get((stem, r))
            if jd is not None:
                # 判读定谳格(三表):证据分级判读>机器投票;守卫寻址自校验
                # (现值须与 种子现值/新值/判读现值链 之一 xnorm 全等,漂移即走正常打分)
                seeds = ([jd.get("种子现值", ""), str(jd.get("新值", ""))]
                         + str(jd.get("判读现值", "")).split("|"))
                if cur_n in (_xn(x) for x in seeds if x):
                    tiers["判读定谳"] += 1
                    rels["定谳"] += 1
                    total += 1
                    s_sum += 1.0
                    continue
            rk = f"行{r}"
            fam_a = [_xn(a) for a in
                     ((br_map.get(rk) or {}).get("agnes") or []) if a]
            if (rs_map.get(rk) or {}).get("read"):
                fam_a.append(_xn(rs_map[rk]["read"]))
            fam_a = [x for x in fam_a if len(x) >= 2]
            m = rk_map.get(rk) or {}
            fam_b = [_xn(m.get(k)) for k in ("tight", "loose", "montage")]
            # run6 列读器:desc 列整段大窗一次多行识别+行线折线归行(同 RapidOCR 族)
            col_n = _xn(cl_map.get(rk) or "")
            if col_n and len(col_n) >= 2:
                fam_b.append(col_n)
            fam_b = [x for x in fam_b if len(x) >= 2]
            strip_n = _xn((st_map.get(rk) or {}).get("strip"))
            votes = ([("A", x) for x in fam_a] + [("B", x) for x in fam_b]
                     + ([("S", strip_n)] if strip_n and len(strip_n) >= 2 else []))
            clusters = _clusters(votes) if votes else []
            win = clusters[0] if clusters else []
            win_n = win[0][1] if win else ""
            win_fams = {f for f, _ in win}
            rival = clusters[1] if len(clusters) > 1 else []
            if len(votes) < 2:
                tier = "读数不足"
            elif len(win) >= 3 and {"A", "B"} <= win_fams:
                tier = "可信(双族)"
            elif len(win) >= 3 and {"B", "S"} <= win_fams:
                tier = "可信(单族双几何)"
            elif len(win) >= 2:
                tier = ("分裂" if rival and len(rival) >= 2
                        and {f for f, _ in rival} - win_fams else "同族多数")
            else:
                tier = "无收敛"
            tiers[tier] += 1
            if win_n == cur_n or _ratio(win_n, cur_n) >= RATIO:
                rel = "印证现值"
            elif win_n and win_n in cur_n:
                rel = "读截断"
            else:
                rel = "矛盾/无收敛"
            rels[rel] += 1
            w = TIER_W.get(tier, 0.0)
            if tier == "读数不足":
                # 单票印证=弱证据(run4 定性:23/25 补读格无第二票):给弱分
                w = 0.3 if rel == "印证现值" else (0.24 if rel == "读截断" else 0.0)
            elif rel == "读截断":
                w *= 0.8
            elif rel != "印证现值":
                w = 0.0
            total += 1
            s_sum += w
    conv = s_sum / total if total else 0.0
    print(f"收敛分级: conv={conv:.4f} over {total} 非空desc格")
    print(f"  tiers={dict(tiers)}")
    print(f"  rels={dict(rels)}")
    print(f"METRIC conv={conv:.4f}")


if __name__ == "__main__":
    main()
