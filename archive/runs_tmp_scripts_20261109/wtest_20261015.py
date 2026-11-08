# -*- coding: utf-8 -*-
import os, sys
from pathlib import Path
R = Path(r"D:\Skye\Documents\Work\高维智矿\7.13杂活")
for d in [R/"runs"/"tmp"/"_mk1", Path(os.environ.get("TEMP",""))/"_mk2"]:
    try:
        d.mkdir(parents=True, exist_ok=True)
        t = d/"x.txt"; t.write_text("hi", encoding="utf-8")
        print("OK 可写:", d, "->", t.read_text(encoding="utf-8"))
        t.unlink(); d.rmdir()
    except Exception as e:
        print("不可写:", d, "->", type(e).__name__, str(e)[:70])
print("TEMP env =", os.environ.get("TEMP"))
