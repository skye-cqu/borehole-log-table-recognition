# -*- coding: utf-8 -*-
import os
from pathlib import Path
R = Path(r"D:\Skye\Documents\Work\高维智矿\7.13杂活")
d = R/"runs"/"tmp"/"_ls1"
try:
    d.mkdir(parents=True, exist_ok=True)
    print("mkdir OK:", d)
except Exception as e:
    print("mkdir FAIL:", type(e).__name__, str(e)[:60])
for op, fn in [("iterdir", lambda: list(d.iterdir())),
               ("scandir", lambda: list(os.scandir(d))),
               ("listdir", lambda: os.listdir(d))]:
    try:
        fn(); print("  %-8s OK" % op)
    except Exception as e:
        print("  %-8s FAIL %s: %s" % (op, type(e).__name__, str(e)[:60]))
try:
    d.rmdir(); print("rmdir OK")
except Exception as e:
    print("rmdir FAIL:", type(e).__name__, str(e)[:60])
