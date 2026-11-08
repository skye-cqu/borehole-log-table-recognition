# -*- coding: utf-8 -*-
"""并行批处理公共入口。

统一的多进程调度（multiprocessing.Pool）+ 进度/结果输出，供各阶段脚本复用。
约定：worker 返回 (name, ok, info) 三元组——
  name: 文件/样本名；ok: 是否成功；info: 结果描述或错误信息。
"""
import time
from multiprocessing import Pool, cpu_count


def _run_one(payload):
    """子进程入口。Windows 走 spawn，打包函数必须是模块级的，所以 worker 和 starmap 标记随参数传进去。"""
    idx, worker, starmap, item = payload
    return idx, (worker(*item) if starmap else worker(item))


def run_batch(items, worker, *, starmap=False, max_workers=8):
    """对 items 并行调用 worker：**跑完一项立刻打一行**。

    原来是 pool.map 整批拿完再打印，长任务（比如 30 张表逐格识别）中途只有开头那句
    "共 N 项待处理"，看着就是卡死；用户因此以为没在跑。

    参数:
        items:      待处理项列表（starmap=True 时为参数元组列表）。
        worker:     处理函数；starmap=False 时接受单个项，否则接受一组参数。
        starmap:    是否将 items 的每个元组解包传给 worker。
        max_workers:并行度上限；实际取 min(上限, cpu_count()//2)。
    返回:
        list[tuple(name, ok, info)]，与 items 一一对应、顺序一致
        （打印按完成先后，返回值按输入顺序，这是有意的）。
    """
    if not items:
        print("没有待处理项。")
        return []
    n_workers = max(1, min(max_workers, cpu_count() // 2))
    print(f"共 {len(items)} 项待处理，使用 {n_workers} 个进程并行（本机 CPU：{cpu_count()}）",
          flush=True)

    chunksize = max(1, len(items) // (n_workers * 4))
    results = [None] * len(items)
    start = time.time()
    with Pool(processes=n_workers) as pool:
        for n_done, (idx, res) in enumerate(pool.imap_unordered(
                _run_one, ((i, worker, starmap, it) for i, it in enumerate(items)),
                chunksize=chunksize), 1):
            results[idx] = res
            name, ok, info = res
            print(f"  [{n_done}/{len(items)}] {'✓' if ok else '✗'} {name}  {info}"
                  f"（已用 {time.time() - start:.0f}s）", flush=True)
    elapsed = time.time() - start

    ok_cnt = sum(1 for _, ok, _ in results if ok)
    fail = len(results) - ok_cnt
    print(f"\n处理完成：成功 {ok_cnt} 项，失败 {fail} 项，耗时 {elapsed:.2f}s，"
          f"平均 {elapsed / max(1, len(items)):.2f}s/项", flush=True)
    if fail:
        # 任一项失败即整体失败(2026-10-25 教训:全链重跑时二值化 30 张全 MemoryError
        # 却退出码 0,后续阶段拿陈旧产物继续跑,假"一致"险些当真)。
        # 调用方如需容忍部分失败,请自行捕 SystemExit。
        bad = [(n, i) for n, ok, i in results if not ok]
        print("失败明细(前 5 条):", bad[:5], flush=True)
        raise SystemExit(1)
    return results
