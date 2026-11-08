# -*- coding: utf-8 -*-
"""产物目录 manifest 指纹(设计 reports/调研_阻塞与开发界方案_20260930.md §4.2)。

make:  逐文件 md5 → 目录下 _manifest.json(generated_by/code_commit/files)。
check: 现有文件对照 manifest → 新增/缺失/变更;有漂移退出码 1。
globs: 只收匹配的相对路径(fnmatch),缺省全部文件;_manifest.json 自身永不入账。

用法:
  python src/tools/make_manifest.py make  <目录> [--glob 模式]...
  python src/tools/make_manifest.py check <目录> [--glob 模式]...
"""
from __future__ import annotations

import argparse
import fnmatch
import hashlib
import json
import subprocess
import sys
from pathlib import Path

NAME = "_manifest.json"
_ROOT = Path(__file__).resolve().parents[2]


def _md5(p: Path) -> str:
    h = hashlib.md5()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _code_commit() -> str:
    try:
        return subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=_ROOT,
                              capture_output=True, text=True, check=True).stdout.strip()
    except Exception:                                # noqa: BLE001
        return "unknown"


def _files(root: Path, globs: tuple[str, ...]) -> dict[str, str]:
    out = {}
    for p in sorted(root.rglob("*")):
        if not p.is_file() or p.name == NAME:
            continue
        rel = p.relative_to(root).as_posix()
        if globs and not any(fnmatch.fnmatch(rel, g) for g in globs):
            continue
        out[rel] = _md5(p)
    return out


def make(root: str | Path, globs: tuple[str, ...] = ()) -> Path:
    root = Path(root)
    out = {"generated_by": "src/tools/make_manifest.py", "code_commit": _code_commit(),
           "files": _files(root, globs)}
    root.mkdir(parents=True, exist_ok=True)
    (root / NAME).write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    return root / NAME


def check(root: str | Path, globs: tuple[str, ...] = ()) -> dict:
    root = Path(root)
    old = json.load(open(root / NAME, encoding="utf-8"))["files"]
    now = _files(root, globs)
    return {"added": sorted(set(now) - set(old)),
            "missing": sorted(set(old) - set(now)),
            "changed": sorted(k for k in set(now) & set(old) if now[k] != old[k])}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=("make", "check"))
    ap.add_argument("root")
    ap.add_argument("--glob", action="append", default=[])
    a = ap.parse_args()
    if a.cmd == "make":
        print(f"manifest → {make(a.root, tuple(a.glob))}")
        return
    r = check(a.root, tuple(a.glob))
    print(json.dumps(r, ensure_ascii=False, indent=1))
    sys.exit(1 if (r["added"] or r["missing"] or r["changed"]) else 0)


if __name__ == "__main__":
    main()
