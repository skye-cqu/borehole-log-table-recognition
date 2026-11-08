# -*- coding: utf-8 -*-
"""内容锚定触发器全量扫描:表头格 OCR 文本命中 >=2 个不同列名 → 该格跨越了缺失界。"""
import json, sys
from pathlib import Path
R = Path(r"D:\Skye\Documents\Work\高维智矿\7.13杂活")
sys.path.insert(0, str(R))
from src.core import paths
KEYCHAR = {"煤层标志层号": "煤", "柱状": "柱", "地质时代": "地", "深度": "深",
           "层厚": "层", "采长": "采", "倾角": "倾", "真厚": "真", "岩性描述": "岩"}

def names_in(text):
    if not text: return set()
    s = set()
    if "煤" in text or "标" in text or "层号" in text: s.add("煤层标志层号")
    if "柱" in text: s.add("柱状")
    for nm in ("地质时代", "深度", "层厚", "采长", "倾角", "真厚", "岩性描述"):
        if KEYCHAR[nm] in text: s.add(nm)
    return s

D = paths.RUNS_DIR/"table_reconstruct"
n = 0; hits = []
for f in sorted(D.glob("*_表头映射.json")):
    stem = f.name[:-len("_表头映射.json")]
    hm = json.loads(f.read_text(encoding="utf-8"))
    lv = hm.get("label_verify") or {}
    n += 1
    found = []
    for name, text in lv.items():
        ns = names_in(text)
        if len(ns) >= 2:
            found.append([name, text, sorted(ns)])
    # 也扫 keep 中每格的表头文本(不受 label_verify 键去重影响)
    if found:
        hits.append([stem, found, hm.get("header_src"), hm.get("sep_x_band")])
print("扫描 =", n)
print("命中 =", len(hits))
for stem, found, src, sx in hits:
    print("\n%s  header_src=%s" % (stem, src))
    print("  sep_x_band =", sx)
    for f in found:
        print("   格名=%-12s 文本=%-14r → 命中名 %s" % (f[0], f[1], f[2]))
