# -*- coding: utf-8 -*-
"""识读窗修复全量重出(2026-11-03):30图 build_cells → REEMIT_DIR_20261103。
并行走 batch.run_batch(约束6),4进程(RapidOCR 单线程+33MP灰图,进程内存~200MB)。
任一图失败 exit 1(批处理纪律)。"""
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from src.core import paths, batch  # noqa: E402
from src.table.reconstruct_excel import build_cells, to_excel  # noqa: E402


def job(stem):
    sheet, meta = build_cells(stem)
    if sheet is None:
        return stem, False, str(meta)[:150]
    p = to_excel(stem, sheet, paths.REEMIT_DIR_20261103)
    return stem, True, (f"层{meta['n_layers']} 格{meta['n_cells']} "
                        f"有字格{meta['n_text_cells']} → {p.name}")


def main():
    stems = sorted(p.stem for p in paths.RAW_DIR.glob("钻孔柱状图*.JPG"))
    print(f"全量重出 {len(stems)} 图 → {paths.REEMIT_DIR_20261103}", flush=True)
    results = batch.run_batch([(s,) for s in stems], job, starmap=True, max_workers=4)
    bad = [r for _, ok, r in results if not ok]
    for s, ok, r in results:
        print(f"{'OK ' if ok else 'FAIL'} {s} {r}", flush=True)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
