# -*- coding: utf-8 -*-
"""并行 finalize(2026-11-04):30 图全量,批口径与既定链一致——
26 图 use_agnes=True,特图 1019/1030/1032/1042 use_agnes=False(--no-agnes 等价)。
图间独立(各写各的整合 xlsx/校正账/验收),并行走 batch.run_batch(约束6)。
任一图失败 exit 1。用法: python runs/tmp/parallel_finalize.py <日志文件>"""
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from src.core import paths, batch  # noqa: E402
from src.table.finalize_tables import finalize  # noqa: E402

NO_AGNES = {"钻孔柱状图1019", "钻孔柱状图1030", "钻孔柱状图1032", "钻孔柱状图1042"}


def job(stem):
    try:
        out = finalize(stem, use_agnes=stem not in NO_AGNES)
        n_app = sum(1 for e in (out or {}).get("校正账", [])
                    if isinstance(e, dict) and e.get("应用"))
        return stem, True, f"账{n_app}条应用"
    except Exception as e:  # noqa: BLE001
        return stem, False, repr(e)[:150]


def main():
    stems = sorted(p.stem for p in paths.RAW_DIR.glob("钻孔柱状图*.JPG"))
    print(f"并行 finalize {len(stems)} 图 (特图no-agnes: {sorted(s[-4:] for s in NO_AGNES)})",
          flush=True)
    results = batch.run_batch([(s,) for s in stems], job, starmap=True, max_workers=4)
    bad = [r for _, ok, r in results if not ok]
    for s, ok, r in results:
        print(f"{'OK ' if ok else 'FAIL'} {s} {r}", flush=True)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
