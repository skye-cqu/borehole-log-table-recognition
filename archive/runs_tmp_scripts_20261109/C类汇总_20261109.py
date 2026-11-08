# -*- coding: utf-8 -*-
"""C类 858 格判读汇总(2026-11-09):合并 58 批结果+主会话统一裁决+采纳表。

输入: C类判读包_20261108/判读_结果_C_{0..57}.json + C类池_重推_20261108.json
输出: 判读_采纳_C类_20261109.json / C类判读汇总_20261109.md

主会话裁决(弱档·用户授权,详见 C类判读汇总_20261109.md):
  A 1019 火族短字=煤(语义铁证,批9 6格重裁)
  B 1023 行73/74/84/94 田→团(术语)
  C 1030 批29 7格 薄→簿(同格双证+参考链)
  D 1020_行103 呈肾状→呈鲕状(鱼旁)
  E 1027_行47 从→以(语义)
  F 1042 批50 欢→灰(行书灰,火底笔)
verdict 以 text(终值)经扩展归一化重算为准,与 agent 原判不同者入翻案清单。
"""
import json
import re
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, r"D:\Skye\Documents\Work\高维智矿\7.13杂活")
from src.handwriting.normalizers import norm_desc  # noqa: E402

OD = Path(r"D:\Skye\Documents\Work\高维智矿\7.13杂活\runs\autoresearch_align\多源定级_20261106")
PKG = OD / "C类判读包_20261108"

# 扩展归一化:机器归一 + agent 口径"视同"的变体字对(仅单字安全对;园/圆、簿/薄、脆/腕、万/方不等价)
VARIANT = str.maketrans({"夾": "夹", "長": "长", "佈": "布", "絲": "丝", "緻": "致",
                         "並": "并", "䗴": "蜓", "遂": "燧", "芯": "心", "鰓": "鳃"})


def xnorm(s):
    return norm_desc(s).translate(VARIANT)


def main():
    pool = json.loads((OD / "C类池_重推_20261108.json").read_text(encoding="utf-8"))
    pool_tags = {e["tag"] for e in pool}
    pool_by = {e["tag"]: e for e in pool}

    results = {}
    dup = []
    for i in range(58):
        p = PKG / f"判读_结果_C_{i}.json"
        for r in json.loads(p.read_text(encoding="utf-8")):
            if r["tag"] in results:
                dup.append((i, r["tag"]))
            results[r["tag"]] = r
    missing = pool_tags - set(results)
    extra = set(results) - pool_tags
    print(f"结果 {len(results)} 格;池 {len(pool_tags)};缺 {sorted(missing)};多 {sorted(extra)};重复 {dup}")
    if missing:
        sys.exit(1)

    # ---- 主会话统一裁决 ----
    patched = []
    fire = {"1019": [57, 60, 78, 82, 100, 102]}
    for stem, rows_ in fire.items():
        for r in rows_:
            tag = f"{stem}_行{r}"
            t = results[tag]["text"]
            t2 = re.sub(r"[灿丸灯炕点虬]", "煤", t)
            if t2 != t:
                results[tag]["text"] = t2
                patched.append((tag, "A火族→煤", t, t2))
    for r in (73, 74, 84, 94):
        tag = f"1023_行{r}"
        t = results[tag]["text"]
        t2 = t.replace("田块", "团块")
        if t2 != t:
            results[tag]["text"] = t2
            patched.append((tag, "B田→团", t, t2))
    for r in (3, 24, 26, 35, 41, 53, 56):
        tag = f"1030_行{r}"
        t = results[tag]["text"]
        t2 = t.replace("薄", "簿")
        if t2 != t:
            results[tag]["text"] = t2
            patched.append((tag, "C薄→簿", "", "1030批29重算"))
    tag = "1020_行103"
    t = results[tag]["text"]
    t2 = t.replace("肾状", "鲕状")
    if t2 != t:
        results[tag]["text"] = t2
        patched.append((tag, "D肾→鲕", t, t2))
    tag = "1027_行47"
    t = results[tag]["text"]
    t2 = t.replace("从暗煤", "以暗煤").replace("从亮煤", "以亮煤")
    if t2 != t:
        results[tag]["text"] = t2
        patched.append((tag, "E从→以", t, t2))
    for tag, r in results.items():
        if r["tag"].startswith("1042_") and "欢" in r["text"]:
            t2 = r["text"].replace("欢", "灰")
            patched.append((tag, "F欢→灰", "", "重算"))
            r["text"] = t2

    # ---- 扩展归一重算 verdict ----
    flips = []
    for tag, r in results.items():
        e = pool_by[tag]
        nt, nc, nr = xnorm(r["text"]), xnorm(e["cand"]), xnorm(e["ref"])
        v2 = "现值对" if nt == nc else ("参考对" if nt == nr else "都不对")
        if v2 != r["verdict"]:
            flips.append((tag, r["verdict"], v2))
        r["verdict2"] = v2

    cnt = Counter(r["verdict2"] for r in results.values())
    cnt_type = Counter(r["type"] for r in results.values())
    cnt_conf = Counter(r["conf"] for r in results.values())
    byfig = Counter()
    for tag, r in results.items():
        if r["verdict2"] != "现值对":
            byfig[tag.split("_行")[0]] += 1

    # ---- 采纳表 ----
    adopt = []
    for tag in sorted(pool_tags, key=lambda t: (t.split("_行")[0], int(t.split("_行")[1]))):
        r = results[tag]
        e = pool_by[tag]
        text = r["text"].strip()
        has_box = "⬜" in text
        if r["verdict2"] == "现值对" or has_box:
            adopt.append({"tag": tag, "组": "C", "protect": True, "新值": "",
                          "种子现值": e["cand"], "判读现值": "", "来源": "C类弱档判读",
                          "conf": r["conf"], "note": ("⬜占位" if has_box else "现值对维持")})
        else:
            adopt.append({"tag": tag, "组": "C", "protect": False, "新值": text,
                          "种子现值": e["cand"], "判读现值": "", "来源": "C类弱档判读",
                          "conf": r["conf"], "note": r["verdict2"]})
    (OD / "判读_采纳_C类_20261109.json").write_text(
        json.dumps(adopt, ensure_ascii=False, indent=1), encoding="utf-8")

    n_change = sum(1 for a in adopt if not a["protect"])
    md = ["# C类 858 格弱档判读汇总(2026-11-09,助手视觉判读·用户授权,弱档)", "",
          f"- 池 858 格=候选≠参考且双方非空(剔 98 定谳格);58 批×≤15 格,主会话逐波抽核 15 格",
          f"- verdict(终值重算): {dict(cnt)};type: {dict(cnt_type)};conf: {dict(cnt_conf)}",
          f"- 采纳表: 采纳写值 {n_change} 格 + 保护维持 {len(adopt)-n_change} 格 → 判读_采纳_C类_20261109.json",
          f"- 非现值对按图: {dict(sorted(byfig.items()))}", "",
          "## 主会话统一裁决(text 定稿+verdict 重算)"]
    md += [f"- {p[0]} {p[1]}: {p[2][:20]!r}→{p[3][:20]!r}" if p[2] else f"- {p[0]} {p[1]}" for p in patched]
    md += ["", f"## 翻案清单(verdict 重算≠agent 原判,{len(flips)} 格,以重算为准)"]
    md += [f"- {f[0]} {f[1]}→{f[2]}" for f in flips]
    md += ["", "## 写值范围与署名",
           "- 参考对/都不对 格写判读 text(纸面忠实转写,笔误照录:簿/脆/媒/半富/漆园等)",
           "- 现值对 与 ⬜占位 格保护维持(判读采纳规则 protect,四门让位)",
           "- 扩展归一化 = norm_desc + 变体表(夾/夹 長/长 佈/布 絲/丝 緻/致 並/并 䗴/蜓 遂/燧 芯/心);园/圆 簿/薄 脆/腕 不等价",
           "- 署名: 助手视觉判读(用户授权),弱档,不支撑 100% 口径"]
    (OD / "C类判读汇总_20261109.md").write_text("\n".join(md), encoding="utf-8")
    print(f"裁决 {len(patched)} 处;翻案 {len(flips)} 格;采纳 {n_change} 写值+{len(adopt)-n_change} 保护")
    for f in flips:
        print("  FLIP", f[0], f[1], "->", f[2])


if __name__ == "__main__":
    main()
