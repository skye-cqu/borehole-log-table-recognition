# -*- coding: utf-8 -*-
"""出表分片驱动(2026-10-26):绕开 multiprocessing.Pool(spawn 池在夜窗口两次实测零产出,
py-spy 证实 worker 在 rec 推理里龟速)——直接单进程顺序调用 reemit_tables.worker。

用法: python runs/tmp/出表_分片_20261026.py 1015 1024 1033 ...
每张打一行耗时;任一张失败退出码 1(熔断语义与 batch.run_batch 一致)。
"""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.tools import reemit_tables  # noqa: E402


def main():
    stems = [f"钻孔柱状图{a}" for a in sys.argv[1:]]
    bad = []
    for stem in stems:
        t = time.time()
        name, ok, info = reemit_tables.worker(stem)
        print(f"{stem} {'✓' if ok else '✗'} {time.time()-t:.0f}s {info}", flush=True)
        if not ok:
            bad.append(stem)
    if bad:
        print(f"失败: {bad}", flush=True)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
