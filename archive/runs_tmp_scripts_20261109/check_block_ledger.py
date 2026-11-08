# -*- coding: utf-8 -*-
"""块账备份+对比(2026-11-03):识读窗修复后重 crop 前,备份旧块账到 rollback/,
重 crop 后逐图对比块界(行范围/块数)是否漂移;漂移图需重读 Agnes 块。
用法: python runs/tmp/check_block_ledger.py backup|compare
"""
import json
import shutil
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from src.core import paths  # noqa: E402

BK = PROJECT_ROOT / "rollback" / "识读窗修复_块账备份_20261103"


def backup():
    BK.mkdir(parents=True, exist_ok=True)
    n = 0
    for vp in sorted(paths.AGNES_REREAD_DIR_20261028.glob("*/块账.json")):
        shutil.copy2(vp, BK / vp.parent.name / "块账.json")
        n += 1
    print(f"备份 {n} 份块账 → {BK}")


def sig(账):
    return json.dumps([[b["k"], b["file"], list(b["行"])] for b in 账["blocks"]],
                      ensure_ascii=False, sort_keys=True)


def compare():
    chg = same = 0
    for vp in sorted(paths.AGNES_REREAD_DIR_20261028.glob("*/块账.json")):
        old_p = BK / vp.parent.name / "块账.json"
        if not old_p.exists():
            print("无备份", vp.parent.name)
            continue
        old = json.loads(old_p.read_text(encoding="utf-8"))
        new = json.loads(vp.read_text(encoding="utf-8"))
        if sig(old) == sig(new):
            same += 1
        else:
            chg += 1
            ob, nb = old["blocks"], new["blocks"]
            print(f"{vp.parent.name[-4:]}: 块数 {len(ob)}→{len(nb)}")
            for a, b in zip(ob, nb):
                if list(a["行"]) != list(b["行"]):
                    print(f"   块{a['k']}: {list(a['行'])} → {list(b['行'])}")
    print(f"块账一致 {same} 漂移 {chg}")


if __name__ == "__main__":
    {"backup": backup, "compare": compare}[sys.argv[1]]()
