# -*- coding: utf-8 -*-
"""多源定级器(全量扫描后跑):全库 desc 非空格按双族多源投票定级,零改动值。

票源(全图上证据):
  Agnes族 = pack_bridge 读1-3 + agnes_resweep 补读
  RapidOCR族 = multisource_reads 窄窗/宽窗/拼字
分级:
  可信   = 众读≥3票且双族都支持众读(机器定稿级)
  同族多数 = 众读≥2票但仅单族支持(暂定,缺第二族)
  分裂   = 两族多数读不同文(人审队列,出裁片)
  无收敛 = 无≥2票同文(人审队列)
  读数不足 = 总票<2
另列:可信级矛盾(众读≠现值) = 零参考可执行疑错清单。
出 runs/autoresearch_align/多源定级_20261106/{定级.json,分级索引.md}。
"""
import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from openpyxl import load_workbook

from src.core import paths
from src.handwriting import rules as R
from src.handwriting.normalizers import norm_desc

OD = paths.AUTORESEARCH_DIR / "多源定级_20261106"

RATIO = 0.85       # 长文(≥6字)同簇阈值:用户口径"差不多"(OCR 单字噪音不分裂)
SHORT = 6          # <6 字仍须全等(燧/爆同误教训:短串近似=同误温床)


def _ratio(a, b):
    from difflib import SequenceMatcher
    return SequenceMatcher(None, a, b).ratio()


def _clusters(items):
    """[(族, 文本)] → [簇[(族,文本)]]:长文 ratio≥RATIO 并簇,短文须全等。"""
    n = len(items)
    parent = list(range(n))

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for i in range(n):
        for j in range(i + 1, n):
            _, ti = items[i]
            _, tj = items[j]
            same = (ti == tj or
                    (len(ti) >= SHORT and len(tj) >= SHORT
                     and _ratio(ti, tj) >= RATIO))
            if same:
                a, b = find(i), find(j)
                if a != b:
                    parent[a] = b
    groups = {}
    for i in range(n):
        groups.setdefault(find(i), []).append(items[i])
    return sorted(groups.values(), key=len, reverse=True)


def main():
    bridge = R._bridge()
    ms = json.loads((paths.AUTORESEARCH_DIR / "multisource_reads.json")
                    .read_text(encoding="utf-8"))
    rsp = paths.AUTORESEARCH_DIR / "rowstrip_reads.json"
    strip = json.loads(rsp.read_text(encoding="utf-8")) if rsp.exists() else {}
    rs_p = paths.AUTORESEARCH_DIR / "agnes_resweep.json"
    resweep = json.loads(rs_p.read_text(encoding="utf-8")) if rs_p.exists() else {}
    rows_out = []
    tiers = Counter()
    verdicts = Counter()
    geos = Counter()
    actionable = []
    for p in sorted(paths.AUTORESEARCH_CANDIDATE_DIR.glob("*_整合.xlsx")):
        stem = p.name[: -len("_整合.xlsx")]
        rows = list(load_workbook(p, read_only=True).active.iter_rows(values_only=True))
        dcol = R.resolve_roles(rows[0]).get("desc")
        if dcol is None:
            continue
        rk_map = ms.get(stem, {})
        rs_map = resweep.get(stem, {})
        br_map = bridge.get(stem, {})
        for i, row in enumerate(rows[1:]):
            r = i + 2
            raw = row[dcol] if dcol < len(row) else None
            cur_n = norm_desc(raw)
            if not cur_n:
                continue
            rk = f"行{r}"
            fam_a = [norm_desc(a) for a in
                     ((br_map.get(rk) or {}).get("agnes") or []) if a]
            if (rs_map.get(rk) or {}).get("read"):
                fam_a.append(norm_desc(rs_map[rk]["read"]))
            fam_a = [x for x in fam_a if len(x) >= 2]   # 单字读无鉴别力,不入票
            m = rk_map.get(rk) or {}
            fam_b = [norm_desc(m.get(k)) for k in ("tight", "loose", "montage")]
            fam_b = [x for x in fam_b if len(x) >= 2]
            strip_n = norm_desc((strip.get(stem, {}).get(rk) or {}).get("strip"))
            # 行带窗=第三几何轴(引擎同为RapidOCR,几何独立;列界±150px不切字)
            votes = ([("A", x) for x in fam_a] + [("B", x) for x in fam_b]
                     + ([("S", strip_n)] if strip_n and len(strip_n) >= 2 else []))
            clusters = _clusters(votes) if votes else []
            win = clusters[0] if clusters else []
            win_n = win[0][1] if win else ""
            win_votes = len(win)
            win_fams = {f for f, _ in win}
            all_fams = {f for f, _ in votes}
            rival = clusters[1] if len(clusters) > 1 else []
            strip_in_win = "S" in win_fams
            strip_voted = "S" in all_fams
            if len(votes) < 2:
                tier = "读数不足"
            elif win_votes >= 3 and {"A", "B"} <= win_fams:
                tier = "可信(双族)"          # 两引擎族共同支持=章程硬标准
            elif win_votes >= 3 and {"B", "S"} <= win_fams:
                tier = "可信(单族双几何)"    # 同引擎两套几何+≥3票,暂定可信
            elif win_votes >= 2:
                if (rival and len(rival) >= 2
                        and {f for f, _ in rival} - win_fams):
                    tier = "分裂"
                else:
                    tier = "同族多数"
            else:
                tier = "无收敛"
            geo = ("几何互证" if strip_in_win else
                   "几何异读" if strip_voted else "无行带读")
            tiers[tier] += 1
            # 可信级与现值的关系(截断守卫:读⊂现值=裁窗截尾,非矛盾)
            verdict = ""
            if tier.startswith("可信"):
                if win_n == cur_n or _ratio(win_n, cur_n) >= RATIO:
                    verdict = "印证现值"
                elif win_n in cur_n:
                    verdict = "读截断(现值更全)"
                else:
                    verdict = "矛盾现值"
            ent = {"stem": stem, "行": r, "级": tier, "票数": len(votes),
                   "众读n": win_n, "现值n": cur_n,
                   "众读票": win_votes,
                   "次读n": (rival[0][1] if rival else ""),
                   "次读票": len(rival),
                   "A族读": fam_a, "B族读": fam_b,
                   "行带读n": (strip_n or ""), "几何": geo,
                   "现值关系": verdict}
            if verdict == "矛盾现值":
                ent["疑错"] = True
                if tier == "可信(双族)":
                    actionable.append(ent)      # 双族矛盾才进疑错主清单
            rows_out.append(ent)
    for e in rows_out:
        if e.get("现值关系"):
            verdicts[e["现值关系"]] += 1
        geos[e["几何"]] += 1
    OD.mkdir(exist_ok=True)
    (OD / "定级.json").write_text(json.dumps(
        {"tiers": dict(tiers), "verdicts": dict(verdicts), "geos": dict(geos),
         "cells": rows_out, "可信级矛盾": actionable},
        ensure_ascii=False, indent=1), encoding="utf-8")
    lines = ["# 多源定级(含行带几何轴,2026-11-11)", "",
             f"相似度聚类阈值: 长文 ratio≥{RATIO} 并簇,短文(<{SHORT}字)须全等;",
             "矛盾判据带截断守卫(读⊂现值=裁窗截尾,非矛盾);",
             "几何轴: S=行带窗读(横向±150px,列界降级参考)加入投票簇。", "",
             "| 级 | 格数 |", "|---|---|"]
    for k, v in sorted(tiers.items()):
        lines.append(f"| {k} | {v} |")
    lines += ["", "## 几何轴", "", "| 关系 | 格数 |", "|---|---|"]
    for k, v in geos.most_common():
        lines.append(f"| {k} | {v} |")
    lines += ["", "## 可信级 vs 现值", "", "| 关系 | 格数 |", "|---|---|"]
    for k, v in verdicts.most_common():
        lines.append(f"| {k} | {v} |")
    lines += ["", f"**可信级矛盾(零参考可执行疑错)**:{len(actionable)} 格:",
              "", "| 图/行 | 现值 | 众读 | 票 | 次读票 |", "|---|---|---|---|---|"]
    for e in actionable:
        lines.append(f"| {e['stem']}/行{e['行']} | {e['现值n'][:24]} | "
                     f"{e['众读n'][:24]} | {e['众读票']} | {e['次读票']} |")
    (OD / "分级索引.md").write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps(dict(tiers), ensure_ascii=False))
    print("几何", json.dumps(dict(geos), ensure_ascii=False))
    print("现值关系", json.dumps(dict(verdicts), ensure_ascii=False),
          "可信级矛盾", len(actionable))


if __name__ == "__main__":
    main()
