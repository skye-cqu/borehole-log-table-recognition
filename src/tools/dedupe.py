# -*- coding: utf-8 -*-
"""runs/ 位图去重:内容相同的文件改为 NTFS 硬链接,磁盘只留一份实体。

零信息损失——每个路径仍然在,打开/浏览完全一样,只是不再各占一份空间;
想还原成独立文件: 复制粘贴回来即可(或删掉链接让脚本重生成)。
因此删除前无需"重放验证",腾空间与可还原同时成立。

只处理位图后缀;JSON/xlsx 一律不碰(它们的 mtime 是判读台账凭据)。
已是同一 inode 的文件跳过(巡检包本来就是硬链接,不重复计)。

用法: python src/tools/dedupe.py [--apply] [目录 ...]     # 无 --apply = 只出报告
"""
from __future__ import annotations

import hashlib
import os
import sys
from collections import defaultdict
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))
from src.core import paths  # noqa: E402

EXTS = {".png", ".jpg", ".jpeg", ".bmp", ".tif", ".tiff"}
MIN_SIZE = 4096          # 小文件链接收益低于开销


def scan(roots):
    by_size = defaultdict(list)
    for root in roots:
        for p in Path(root).rglob("*"):
            if p.suffix.lower() in EXTS and p.is_file():
                st = p.stat()
                if st.st_size >= MIN_SIZE:
                    by_size[st.st_size].append((p, st))
    groups = []
    for size, items in by_size.items():
        if len(items) < 2:
            continue
        by_hash = defaultdict(list)
        for p, st in items:
            by_hash[_hash(p)].append((p, st))
        for same in by_hash.values():
            if len({st.st_ino for _, st in same}) > 1:
                groups.append(same)
    return groups


def _hash(p: Path) -> bytes:
    h = hashlib.blake2b(digest_size=16)
    with open(p, "rb") as f:
        for blk in iter(lambda: f.read(1 << 20), b""):
            h.update(blk)
    return h.digest()


def main():
    argv = [a for a in sys.argv[1:] if not a.startswith("--")]
    apply = "--apply" in sys.argv
    roots = [Path(a) for a in argv] or [paths.RUNS_DIR]
    groups = scan(roots)
    dup, reclaim = 0, 0
    for g in groups:
        g.sort(key=lambda x: (len(str(x[0])), str(x[0])))   # 短路径留作实体
        keep, ino = g[0][0], g[0][1].st_ino
        for p, st in g[1:]:
            if st.st_ino == ino:
                continue                                    # 已是硬链接,不重复计
            dup += 1
            reclaim += st.st_size
            if apply:
                tmp = p.with_name(p.name + ".linktmp")
                os.link(keep, tmp)
                os.replace(tmp, p)                          # 原子替换,不留空档
    print(f"重复组 {len(groups)} 个,多余副本 {dup} 份,"
          f"可回收 {reclaim / 2**30:.1f} G  ({'已执行' if apply else '仅报告'})")


if __name__ == "__main__":
    main()
