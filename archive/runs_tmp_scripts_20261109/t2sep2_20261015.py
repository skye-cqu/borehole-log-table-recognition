# -*- coding: utf-8 -*-
import json, sys
from pathlib import Path
R = Path(r"D:\Skye\Documents\Work\高维智矿\7.13杂活")
sys.path.insert(0, str(R))

d = json.loads((R/"runs/table_reconstruct/钻孔柱状图1042_分割线.json").read_text(encoding="utf-8"))
print("分割线.json 顶层键:", list(d.keys()))
for k, v in d.items():
    if isinstance(v, list):
        print("  %s: list(len=%d)" % (k, len(v)))
        if v: print("     样本:", json.dumps(v[0], ensure_ascii=False)[:260])
    elif isinstance(v, dict):
        print("  %s: dict(len=%d) keys=%s" % (k, len(v), list(v.keys())[:8]))
    else:
        print("  %s: %r" % (k, v))

print()
print("== 找 x 落在 [650,780] 的分隔线候选 ==")
def scan(obj, path=""):
    hits = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            hits += scan(v, path + "/" + str(k))
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            hits += scan(v, path + "[%d]" % i)
    elif isinstance(obj, (int, float)):
        if 650 <= obj <= 780:
            hits.append((path, obj))
    return hits
h = scan(d)
seen = {}
for p, v in h:
    seen.setdefault(round(v, 1), []).append(p)
for v in sorted(seen):
    print("   x=%-7.1f 出现%d次  例:%s" % (v, len(seen[v]), seen[v][0][:100]))
