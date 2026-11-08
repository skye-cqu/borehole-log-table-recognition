# -*- coding: utf-8 -*-
"""98 格判读汇总:校验 8 个结果文件与分派一一对应,出统计 + 修复清单底稿。只读。"""
import json, collections, io, sys
from pathlib import Path

BASE = Path(r"D:\Skye\Documents\Work\高维智矿\7.13杂活\runs\autoresearch_align\多源定级_20261106")

disp, res = {}, {}
for i in range(8):
    for t in json.loads((BASE / f"判读_分派_{i}.json").read_text(encoding="utf-8")):
        assert t["tag"] not in disp, f"分派重复 {t['tag']}"
        disp[t["tag"]] = t
    for r in json.loads((BASE / f"判读_结果_{i}.json").read_text(encoding="utf-8")):
        assert r["tag"] not in res, f"结果重复 {r['tag']}"
        res[r["tag"]] = r

assert set(disp) == set(res), f"分派/结果 tag 不齐: 缺 {set(disp)-set(res)}  多 {set(res)-set(disp)}"
print(f"总格数: {len(res)} (分派 {len(disp)})")

vc = collections.Counter(r["verdict"] for r in res.values())
tc = collections.Counter(r["type"] for r in res.values())
cc = collections.Counter(r["conf"] for r in res.values())
print("verdict:", dict(vc))
print("type   :", dict(tc))
print("conf   :", dict(cc))

# 按批次交叉(便于与子代理汇报对账)
for i in range(8):
    tags = [t["tag"] for t in json.loads((BASE / f"判读_分派_{i}.json").read_text(encoding="utf-8"))]
    c = collections.Counter(res[t]["verdict"] for t in tags)
    print(f"  批次{i}: {dict(c)}")

# 修复候选
fix_zhong = [t for t, r in res.items() if r["verdict"] == "众读对"]
fix_text  = [t for t, r in res.items() if r["verdict"] == "都不对"]
print(f"\n修复候选: 众读对 {len(fix_zhong)} 格(采众读) + 都不对 {len(fix_text)} 格(采纸面转写)")

# 煤判层类:众读是否缺"煤"前缀
print("\n煤判层类 6 格(现值/众读/次读/行带读/纸面):")
for t in sorted(res):
    r = res[t]
    if "判层" in (r["纸面"] or "") or "判层" in disp[t].get("众读", ""):
        d = disp[t]
        print(f"  {t}: 现值={d['现值']!r} 众读={d['众读']!r} 次读={d.get('次读','')!r} 行带读={d.get('行带读','')!r} -> {r['verdict']} 纸面={r['纸面']!r}")

# 低置信/需留意的格
print("\nconf<高 的格:")
for t, r in sorted(res.items()):
    if r["conf"] != "高":
        print(f"  {t}: conf={r['conf']} verdict={r['verdict']}")

# 输出修复清单底稿
# 取值覆盖:众读缺"煤"前缀的 2 格改采次读/行带读(同为引擎读,与纸面全同)
OVERRIDE = {"1035_行68": "煤判层", "1041_行49": "煤判层"}
OVERRIDE_SRC = "次读+行带读(引擎读;众读缺'煤'前缀)"
NOTE = {
    "1034_行79": "conf中;'鲕'字定谳格(该字有无决定现值对错)",
    "1035_行12": "conf低;尾部花体两字按术语'瓣鳃'转写",
    "1027_行36": "'泥'为弱档单票,推翻三引擎一致'混'",
    "1044_行75": "text 经子代理原图加高裁窗核验+主会话 strip 抽核",
}
rows = []
for t in sorted(res):
    r, d = res[t], disp[t]
    if r["verdict"] == "现值对":
        continue
    if t in OVERRIDE:
        new, src = OVERRIDE[t], OVERRIDE_SRC
    else:
        new = d["众读"] if r["verdict"] == "众读对" else r["text"]
        src = "众读" if r["verdict"] == "众读对" else "纸面转写(弱档)"
    rows.append({"tag": t, "档": d.get("档", ""), "现值": d["现值"], "新值": new,
                 "来源": src, "type": r["type"], "conf": r["conf"], "备注": NOTE.get(t, "")})
out = BASE / "判读_修复清单底稿_20261108.json"
out.write_text(json.dumps(rows, ensure_ascii=False, indent=1), encoding="utf-8")
print(f"\n修复清单底稿 {len(rows)} 格 -> {out.name}")

# markdown 统计块(供分级索引.md 追加)
md = io.StringIO()
md.write("\n## 98 格弱档判读汇总(2026-11-08,助手视觉判读·用户授权)\n\n")
md.write("判读依据: 疑错人审包 98 格×双裁片(cell 单元格窗定本格范围 + strip 行带窗辨字/验截断),原图唯一真值;\n")
md.write("口径: verdict∈{现值对,众读对,都不对},截断守卫=cell 边界外尾巴不算错,现值规范化差异(小数点/标点)不计;\n")
md.write("署名: 助手视觉判读(弱档),主会话逐波抽核 7 格(1038/20、1037/52、1034/79、1035/12、1027/36、1041/49、1044/75)全部通过。\n\n")
md.write("| verdict | 格数 |\n|---|---|\n")
for k in ["现值对", "众读对", "都不对"]:
    md.write(f"| {k} | {vc[k]} |\n")
md.write(f"\ntype 分布: {dict(tc)};conf: {dict(cc)}\n\n")
md.write("明细文件: 判读_结果_0..7.json(98 条,与分派一一对应);修复清单底稿: 判读_修复清单底稿_20261108.json\n")
md.write(f"\n- 现值对 {vc['现值对']} 格: 表值不动,矛盾源于众读误读(字级)或串行,无须修复。\n")
md.write(f"- 众读对 {vc['众读对']} 格: 修复采**众读**(图上引擎读,守'被采文本=引擎读'纪律)。\n")
md.write(f"- 都不对 {vc['都不对']} 格: 两方均不符,修复候选=**纸面转写(助手弱档)**,须用户点头后入表并在校正账标注弱档来源。\n")
md.write("- 留意: 煤判层类 2 格(1035/68、1041/49)众读缺'煤'前缀(裁窗左缘截字),修复取值改采次读/行带读'煤判层'(同为引擎读)。\n")
(BASE / "判读_汇总块_20261108.md").write_text(md.getvalue(), encoding="utf-8")
print(f"汇总块 -> 判读_汇总块_20261108.md")
