# -*- coding: utf-8 -*-
"""final 清理(2026-11-09):删可重跑中间产物,保留原图+输出结果+运行时依赖。

删:判读裁片包(可由 pkg 脚本+原图重跑)、Agnes 复读证据(可 reread.py 重跑)、
    结构 json 历史迭代版(R2/R3)、era 裁片、tmp 大件
留:seed/candidate、根 json(converge/rules 运行时依赖)、判读三表等账本 json、
    人工裁定验收页、table_reconstruct 终版 json(红字重出依赖)、用户参考表
移:参考表 → data/(用户输入数据与原图同处),paths.py 同步
归档:runs/tmp/*.py → archive/runs_tmp_scripts_20261109/(脚本=代码,不删)
"""
import shutil
import sys
from pathlib import Path

ROOT = Path(r"D:\Skye\Documents\Work\高维智矿\7.13杂活")
RUNS = ROOT / "runs"
MS = RUNS / "autoresearch_align/多源定级_20261106"

DELETE_DIRS = [
    MS / "同族判读包_r9", MS / "C类判读包_20261108", MS / "分裂判读包_20261109_v2",
    MS / "血统分叉判读包_r11", MS / "尾池判读包_r10", MS / "分裂判读包_20261109",
    MS / "疑错人审包", MS / "尾池判读包_r12",
    RUNS / "autoresearch_align/multisource_parts",
    RUNS / "autoresearch_align/rowstrip_parts",
    RUNS / "Agnes全列复读_20261028",
    RUNS / "Agnes全列复读_20261028_重读对照",
    RUNS / "era_chars_20261010",
]
DELETE_TMP = ["裁决暂存旧3", "判读拼图", "diag_win", "_漂移版备份_20261026",
              "裁决暂存_识读窗修复", "_B列乱码裁决单_1019.png", "裁决暂存旧",
              "裁决暂存旧2"]

total = 0
for d in DELETE_DIRS + [RUNS / "tmp" / t for t in DELETE_TMP]:
    if not d.exists():
        continue
    size = sum(f.stat().st_size for f in d.rglob("*") if f.is_file()) / 1e6
    total += size
    if d.is_dir():
        shutil.rmtree(d)
    else:
        d.unlink()
    print(f"删 {d.relative_to(ROOT)}  {size:.0f}MB")

# 结构 json 历史迭代版
for p in RUNS.glob("table_reconstruct/*_R[23].json"):
    total += p.stat().st_size / 1e6
    p.unlink()
print("删 结构json历史迭代版 R2/R3")

# tmp 剩余非脚本大件(>512KB 的非 py 文件)
tmp = RUNS / "tmp"
for p in sorted(tmp.rglob("*")):
    if p.is_file() and p.suffix != ".py" and p.stat().st_size > 512 * 1024:
        sz = p.stat().st_size / 1e6
        total += sz
        p.unlink()
        print(f"删 tmp大件 {p.relative_to(ROOT)}  {sz:.1f}MB")
for d in sorted((x for x in tmp.rglob("*") if x.is_dir()), reverse=True):
    try:
        d.rmdir()
    except OSError:
        pass

# 参考表 → data/
src = RUNS / "参考表_1015-1044_20261011"
dst = ROOT / "data/参考表_1015-1044_20261011"
if src.exists():
    shutil.move(str(src), str(dst))
    print("移 参考表 ->", dst.relative_to(ROOT))

# tmp 脚本归档
arc = ROOT / "archive/runs_tmp_scripts_20261109"
arc.mkdir(parents=True, exist_ok=True)
n = 0
for p in sorted(tmp.glob("*.py")):
    shutil.move(str(p), str(arc / p.name))
    n += 1
print(f"归档 runs/tmp 脚本 {n} 个 -> archive/runs_tmp_scripts_20261109")
print(f"合计释放 ~{total:.0f}MB")
