# -*- coding: utf-8 -*-
import os, shutil
from pathlib import Path
R = Path(r"D:\Skye\Documents\Work\高维智矿\7.13杂活")
for n in [".pytest_tmp", "runs/tmp/_pt", "runs/tmp/_pt2", "runs/tmp/_mk1", "runs/tmp/_ls1"]:
    d = R/n
    ex = d.exists()
    ls = None
    if ex:
        try:
            os.listdir(d); ls = "可列举"
        except Exception as e:
            ls = "列举失败 %s" % type(e).__name__
        try:
            shutil.rmtree(d); rm = "已删除"
        except Exception as e:
            rm = "删除失败 %s" % type(e).__name__
    else:
        rm = "-"
    print("%-20s 存在=%-5s %-22s %s" % (n, ex, ls, rm))
