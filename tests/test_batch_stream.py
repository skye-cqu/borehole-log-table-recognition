# -*- coding: utf-8 -*-
"""batch.run_batch 改流式打印后，返回值的顺序纪律必须还在。"""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from src.core.batch import run_batch          # noqa: E402


def slow(item):
    """完成顺序故意跟输入顺序相反：先来的项睡得久。"""
    n, sleep = item
    time.sleep(sleep)
    return n, True, f"slept {sleep}"


def slow_pair(n, sleep):
    return slow((n, sleep))


def test_返回值按输入顺序而打印按完成顺序():
    items = [(1, 0.6), (2, 0.3), (3, 0.0), (4, 0.15)]
    res = run_batch(items, slow, max_workers=4)
    assert [r[0] for r in res] == [1, 2, 3, 4]        # 与 items 一一对应
    assert all(r[1] for r in res)
    assert res[0][2] == "slept 0.6"                   # 内容没串位


def test_starmap同样可用():
    res = run_batch([(5, 0.0), (6, 0.1)], slow_pair, starmap=True, max_workers=2)
    assert [r[0] for r in res] == [5, 6]
