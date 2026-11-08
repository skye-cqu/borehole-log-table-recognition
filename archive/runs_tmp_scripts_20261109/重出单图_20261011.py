# -*- coding: utf-8 -*-
"""单图重出整合表(交付门禁修复链):finalize --only N。
拒裁图 bands=[] 无 Agnes 秒级;有名带图 use_agnes=True 单图 ~1 分钟。
用法: python runs/tmp/重出单图_20261011.py --only 1030
"""
import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from src.core import paths  # noqa: E402
from src.table.finalize_tables import finalize  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", type=int, required=True, help="图号,如 1030")
    ap.add_argument("--no-agnes", action="store_true")
    a = ap.parse_args()
    stem = f"钻孔柱状图{a.only}"
    if not (paths.REEMIT_DIR_20261005B / f"{stem}_还原.xlsx").exists():
        print("缺 B 目录还原表:", stem)
        return 2
    rep = finalize(stem, use_agnes=not a.no_agnes)
    if "error" in rep:
        print(stem, "finalize 失败:", rep["error"])
        return 1
    print(stem, "重出完成:", {k: rep[k] for k in rep if k in ("行数", "时代带行", "账条数")})
    return 0


if __name__ == "__main__":
    sys.exit(main())
