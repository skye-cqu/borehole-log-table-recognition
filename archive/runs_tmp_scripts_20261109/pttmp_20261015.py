# -*- coding: utf-8 -*-
import os, stat
from pathlib import Path
R = Path(r"D:\Skye\Documents\Work\高维智矿\7.13杂活")
d = R/".pytest_tmp"
print(".pytest_tmp 存在:", d.exists())
if d.exists():
    try:
        print("  iterdir:", [p.name for p in d.iterdir()][:10])
    except Exception as e:
        print("  iterdir FAIL:", type(e).__name__, str(e)[:80])
    try:
        print("  rmdir:", (d.rmdir(), "OK")[1])
    except Exception as e:
        print("  rmdir FAIL:", type(e).__name__, str(e)[:80])
print()
# pytest 配置
for f in ["pytest.ini","setup.cfg","pyproject.toml","tox.ini"]:
    p = R/f
    if p.exists():
        t = p.read_text(encoding="utf-8", errors="replace")
        if "pytest" in t or "basetemp" in t or "tmp" in t:
            print("==", f, "==")
            print(t[:700])
