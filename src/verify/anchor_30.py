# -*- coding: utf-8 -*-
"""30 张定稿锚点回归:freeze 固化基线,check 重跑后对账,交外差异=新偏离即 FAIL。

判定 4 语义:基线记录当前状态为下限;expected_fails.json 吸收已知例外(增删须用户确认)。
"""
import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from src.core import paths

TABLE_DIR = paths.RUNS_DIR / "table_reconstruct"
BASELINE_PATH = Path(__file__).parent / "baseline_30.json"   # 冻结参照物,随 expected_fails 入库

PRODUCT_PATTERNS = ["钻孔柱状图{s}_列结构定稿.json", "钻孔柱状图{s}_分割线.json",
                    "钻孔柱状图{s}_上下框.json", "钻孔柱状图{s}_闭合外框.json",
                    "钻孔柱状图{s}_矫正映射.json"]
STEMS = [str(s) for s in range(1015, 1045)]

# 阶段重跑命令(顺序即依赖序;均无参数=全量 30 张)
STAGE_CMDS = {
    "6a": [sys.executable, "src/table/finalize_columns.py"],
    "6c": [sys.executable, "src/table/bridge_gaps.py"],
    "6d": [sys.executable, "src/table/frame_topbottom.py"],
    "6e": [sys.executable, "src/table/close_frame.py"],
    "6f": [sys.executable, "src/table/extract_table.py"],
}
STAGE_ORDER = ["6a", "6c", "6d", "6e", "6f"]


def _md5(p: Path) -> str:
    return hashlib.md5(p.read_bytes()).hexdigest()


def freeze_tree(table_dir: Path, patterns, stems) -> dict:
    files = {}
    for s in stems:
        for pat in patterns:
            p = Path(table_dir) / pat.format(s=s)
            if p.exists():
                files[p.name] = _md5(p)
    return {"schema": "gate_anchor_baseline_v1", "dir": str(table_dir),
            "n_files": len(files), "files": files}


def load_expected() -> dict:
    ef = Path(__file__).parent / "expected_fails.json"
    return json.loads(ef.read_text(encoding="utf-8")) if ef.exists() else {"items": []}


def _absorbed(name: str, expected: dict) -> bool:
    """偏离文件是否被已知例外吸收:显式 files 列出,或 stem+patterns 双匹配。"""
    for item in expected.get("items", []):
        if name in item.get("files", []):
            return True
        stem = name.split("_")[0]                      # "钻孔柱状图1015"
        num = stem.replace("钻孔柱状图", "")
        stems = item.get("stems", [])
        pats = item.get("patterns", [])
        if pats and not any(p in name for p in pats):
            continue
        if "*" in stems or num in stems or stem in stems:
            return True
    return False


def check_tree(table_dir: Path, baseline: dict, expected: dict | None = None) -> dict:
    expected = expected or {"items": []}
    deviations, absorbed = [], 0
    for name, old_md5 in baseline["files"].items():
        p = Path(table_dir) / name
        if not p.exists():
            dev = {"file": name, "kind": "missing"}
        elif _md5(p) != old_md5:
            dev = {"file": name, "kind": "changed"}
        else:
            continue
        if _absorbed(name, expected):
            absorbed += 1
        else:
            deviations.append(dev)
    return {"pass": not deviations, "new_deviations": deviations,
            "absorbed": absorbed, "n_baseline": len(baseline["files"])}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["freeze", "check"])
    ap.add_argument("--stages", default=",".join(STAGE_ORDER),
                    help="check 前重跑的阶段,逗号分隔(默认全链 6a,6c,6d,6e,6f;none=只对账不重跑)")
    args = ap.parse_args()

    if args.cmd == "freeze":
        baseline = freeze_tree(TABLE_DIR, PRODUCT_PATTERNS, STEMS)
        BASELINE_PATH.write_text(json.dumps(baseline, ensure_ascii=False, indent=1),
                                 encoding="utf-8")
        print(f"基线冻结 {baseline['n_files']} 份产物 → {BASELINE_PATH}")
        return

    baseline = json.loads(BASELINE_PATH.read_text(encoding="utf-8"))
    for st in [s for s in args.stages.split(",") if s != "none"]:
        print(f"重跑阶段 {st} ...")
        r = subprocess.run(STAGE_CMDS[st], cwd=_PROJECT_ROOT)
        if r.returncode != 0:
            print(f"阶段 {st} 非零退出 {r.returncode}")
            raise SystemExit(3)
    res = check_tree(TABLE_DIR, baseline, load_expected())
    print(json.dumps({k: v for k, v in res.items() if k != "new_deviations"},
                     ensure_ascii=False))
    for d in res["new_deviations"]:
        print(f"  新偏离: {d['kind']} {d['file']}")
    raise SystemExit(0 if res["pass"] else 2)


if __name__ == "__main__":
    main()
