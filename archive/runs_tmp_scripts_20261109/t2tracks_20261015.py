# -*- coding: utf-8 -*-
import json, sys
from pathlib import Path
R = Path(r"D:\Skye\Documents\Work\高维智矿\7.13杂活")
d = json.loads((R/"runs/table_reconstruct/钻孔柱状图1042_全竖线判定.json").read_text(encoding="utf-8"))
print("track_nos:")
tn = d["track_nos"]
for k, v in tn.items():
    print("  %s: %s" % (k, v))
print()
print("columns_gidx:", d["columns_gidx"])
print("n_tracks=%s n_visible=%s n_panels=%s" % (d["n_tracks"], d["n_visible"], d["n_panels"]))
print()
print("merged_by_track:", d["merged_by_track"])
print()
print("== raws ==")
for i, raw in enumerate(d["raws"]):
    print("-- panel %d: parsed=%s n_tracks=%s" % (i, raw.get("parsed"), raw.get("n_tracks")))
    for m in raw.get("map", []):
        print("     ", json.dumps(m, ensure_ascii=False)[:300])
print()
print("crop:", d["crop"])
