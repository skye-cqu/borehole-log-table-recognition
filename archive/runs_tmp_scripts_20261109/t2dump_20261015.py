# -*- coding: utf-8 -*-
import json, sys
import numpy as np, cv2
from pathlib import Path
R = Path(r"D:\Skye\Documents\Work\高维智矿\7.13杂活")
sys.path.insert(0, str(R))
from src.core import paths

def show(o, ind=0, maxd=2, maxk=9):
    pad = "  "*ind
    if isinstance(o, dict):
        for k,v in list(o.items())[:maxk]:
            if isinstance(v,(dict,list)):
                print("%s%s: %s(len=%d)" % (pad,k,type(v).__name__,len(v)))
                if ind<maxd and v: show(v, ind+1, maxd, maxk)
            else:
                print("%s%s: %r" % (pad,k,v))
    elif isinstance(o, list):
        print("%slist len=%d" % (pad,len(o)))
        if o and ind<maxd: show(o[0], ind+1, maxd, maxk)

d = json.loads((R/"runs/table_reconstruct/钻孔柱状图1042_全竖线判定.json").read_text(encoding="utf-8"))
print("===== 全竖线判定.json =====")
show(d, maxd=2, maxk=9)
print()
c = json.loads((R/"runs/table_reconstruct/钻孔柱状图1042_列结构定稿.json").read_text(encoding="utf-8"))
print("===== 列结构定稿.json columns =====")
for col in c.get("columns", []):
    print("  ", json.dumps(col, ensure_ascii=False)[:230])
print("  missing:", c.get("missing"))
print()
g = cv2.imread(str(paths.RAW_DIR/"钻孔柱状图1042.JPG"), cv2.IMREAD_GRAYSCALE)
ink = (g<128).astype(np.uint8)
print("===== 表头带 y=[730,945] x=[690,740] 每列暗像素 =====")
sub = ink[730:945, 690:740]
cs = sub.sum(axis=0)
for i,v in enumerate(cs):
    if v>=40: print("   x=%d 暗=%d/%d (%.0f%%)" % (690+i, v, sub.shape[0], 100.0*v/sub.shape[0]))
print()
print("===== x∈[690,745] 墨峰随 y 漂移 =====")
for y in range(760, 19900, 1200):
    w = ink[y-3:y+4, 690:745]
    cc = np.convolve(w.sum(axis=0), np.ones(3)/3.0, mode="same")
    print("   y=%-6d argmax x=%d (%.1f)" % (y, 690+int(np.argmax(cc)), cc.max()))
