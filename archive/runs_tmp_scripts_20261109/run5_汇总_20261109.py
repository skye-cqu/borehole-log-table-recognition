# -*- coding: utf-8 -*-
"""run5 汇总:分裂 226 格判读(16 批+复核波)→ 采纳第三表。

verdict 以 text+xnorm 重算兜底(判读员口径漂移教训,C类同款):
  现值对 = xnorm(text)==xnorm(现值)
  读对   = xnorm(text) ∈ {xnorm(多数簇), xnorm(次簇)}
  都不对 = 其余
text 含 ⬜(截字未定)不写值只保护。复核文件覆盖同 tag 原判。
产出 判读_采纳_分裂_20261109.json + 分裂判读汇总_20261109.md。
"""
import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, r"D:\Skye\Documents\Work\高维智矿\7.13杂活")

from src.handwriting.rules import _xn
from difflib import SequenceMatcher

BASE = Path(r"D:\Skye\Documents\Work\高维智矿\7.13杂活\runs\autoresearch_align\多源定级_20261106")
V2 = BASE / "分裂判读包_20261109_v2"


def load_dispatch():
    disp = {}
    for b in range(16):
        f = V2 / f"分派_分裂_{b}.json"
        if f.exists():
            for e in json.loads(f.read_text(encoding="utf-8")):
                disp[e["tag"]] = e
    return disp


def load_results():
    res = {}
    for b in range(16):
        f = V2 / f"判读_结果_S_{b}.json"
        if not f.exists():                      # 批0-5 判于几何重做前,结果在 v1 目录
            f = V2.parent / "分裂判读包_20261109" / f"判读_结果_S_{b}.json"
        if f.exists():
            for e in json.loads(f.read_text(encoding="utf-8")):
                res[e["tag"]] = dict(e, 批=f"S{b}")
    f = V2 / "判读_结果_S_复核.json"
    if f.exists():
        for e in json.loads(f.read_text(encoding="utf-8")):
            if e["tag"] in res:
                res[e["tag"]]["批"] = res[e["tag"]]["批"] + "+复核"
            res[e["tag"]] = {**res.get(e["tag"], {}), **e}
    # 主会话修正已在 S10 内(1029_行14)
    return res


def recompute(e, d):
    text, cur = e.get("text", ""), d.get("现值", "")
    tn, cn = _xn(text), _xn(cur)
    if tn and tn == cn:
        return "现值对"
    cands = []
    for field in ("多数簇", "次簇"):
        v = d.get(field, "")
        # 簇字段形如 "文本(3票A)",取括号前文本
        body = v.split("(")[0].strip() if v else ""
        if body:
            cands.append(_xn(body))
    if tn and cands and any(tn == c for c in cands):
        return "读对"
    if tn and cn and SequenceMatcher(None, tn, cn).ratio() >= 0.999:
        return "现值对"
    return "都不对" if (tn or cn) else "现值对"


def main():
    disp = load_dispatch()
    res = load_results()
    missing = set(disp) - set(res)
    extra = set(res) - set(disp)
    print(f"分派 {len(disp)} / 结果 {len(res)} / 缺 {len(missing)} {sorted(missing)[:5]} / 多 {len(extra)}")
    adopt, stats_v, stats_t, blank = [], Counter(), Counter(), []
    for tag, d in sorted(disp.items()):
        e = res.get(tag, {})
        verdict = recompute(e, d)
        stats_v[verdict] += 1
        text = str(e.get("text", "")).strip()
        protect = verdict == "现值对" or "⬜" in text
        if "⬜" in text:
            blank.append(tag)
        adopt.append({
            "tag": tag,
            "组S": "分裂",
            "protect": protect,
            "新值": "" if protect else text,
            "种子现值": d.get("现值", ""),
            "判读现值": "",
            "来源": f"分裂判读v2({e.get('批', '?')})",
            "conf": e.get("conf", ""),
            "note": f"type={e.get('type', '')}",
        })
    out = BASE / "判读_采纳_分裂_20261109.json"
    out.write_text(json.dumps(adopt, ensure_ascii=False, indent=1), encoding="utf-8")
    n_write = sum(1 for a in adopt if not a["protect"])
    for a in adopt:
        if not a["protect"]:
            stats_t[a["note"]] += 1
    md = []
    md.append("# 分裂 226 格判读汇总(2026-11-09,run5)\n")
    md.append(f"- 池:实时重算分裂格 226(neither 144 / win 70 / rival 12),v2 贴框线多边形裁片\n")
    md.append(f"- verdict 重算终值:{dict(stats_v)}\n")
    md.append(f"- 采纳:写值 {n_write} + 保护 {len(adopt)-n_write}(含 ⬜ 截字 {len(blank)} 格:{blank})\n")
    md.append(f"- 写值 type:{dict(stats_t)}\n")
    md.append("- 判读波次:16 批(v1 裁片 6 批后用户指出裁窗缺陷,重做几何 v2;批10 首跑误用 v1 路径已重判)\n")
    md.append("- 复核波:v1 期翻案格 11 格独立重判,10 维持 + 1 推翻(1017_行61 读对→都不对)\n")
    md.append("- 主会话修正:1029_行14(泥质越界书写于列界左侧,行带读可证,都不对→现值对)\n")
    md.append("- 系统性发现:该写手区分⺮头(簿)与艹头(薄);1031_行92 无芯(心/芯视同);1033_行30 植物化**在**(次簇互证);"
              "1035 丰字似半(152/156/164 三格同形裁定);1027_行5 少并/云务状俗写照录;1028_行68 纸面偶漏含字照录\n")
    md.append("- 署名:助手视觉判读(用户授权流程),非用户人审,不支撑 100% 口径\n")
    (BASE / "分裂判读汇总_20261109.md").write_text("\n".join(md), encoding="utf-8")
    print(f"采纳表 {len(adopt)} 条 -> {out.name};写值 {n_write} 保护 {len(adopt)-n_write}")
    print("verdict:", dict(stats_v))


if __name__ == "__main__":
    main()
