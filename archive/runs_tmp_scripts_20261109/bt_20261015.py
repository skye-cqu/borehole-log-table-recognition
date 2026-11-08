# -*- coding: utf-8 -*-
"""测试:pytest tmp_path 失败是否与 basetemp 目录的创建方式有关。
自建 basetemp 并立即验证可列举,再让 pytest 用它。"""
import os
from pathlib import Path
R = Path(r"D:\Skye\Documents\Work\高维智矿\7.13杂活")
bt = R/"runs"/"tmp"/"_bt_pre"
bt.mkdir(parents=True, exist_ok=True)
(bt/".keep").write_text("x", encoding="utf-8")
print("自建 basetemp:", bt, "可列举=", [p.name for p in bt.iterdir()])
