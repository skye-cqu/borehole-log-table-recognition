# -*- coding: utf-8 -*-
import json
from pathlib import Path
R = Path(r"D:\Skye\Documents\Work\高维智矿\7.13杂活")
TR = R/"runs"/"table_reconstruct"
print("##### 表头映射生成元信息(header_src / ok / warnings / 键集)")
for k in ["1015","1017","1019","1020","1023","1025","1028","1030","1032","1033","1042"]:
    p = TR/f"钻孔柱状图{k}_表头映射.json"
    if not p.exists(): print(f"  {k}: 无"); continue
    d = json.load(open(p, encoding="utf-8"))
    keys = sorted(d.keys())
    print("  %s keys=%s" % (k, keys))
    print("      header_src=%r ok=%r n_sep=%r warnings=%s" % (
        d.get("header_src"), d.get("ok"), d.get("n_sep"), json.dumps(d.get("warnings"), ensure_ascii=False)[:150]))
