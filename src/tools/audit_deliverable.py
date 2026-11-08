# -*- coding: utf-8 -*-
"""交付表回读门禁(AGENTS 约束12 的执行器):写完后必须过这台机器再提交。

查四件事(任一不过 = 退出码 1,禁止提交):
  S1 哨兵残留  单元格里还有 @草/@单/@条 —— 回写链漏跑 visual_review_pack 展开(P0 事故形态)
  S2 数值列类型 深度/层厚/采长/真厚 不是数字(含被识别成字母的 "38.13 n 77")
  S3 多值格    数值列一格里塞了 ≥2 个数——行界漏判会把多物理行捆成一行(P1 症状)
  S4 行数对照  表内数据行数 vs 行判定.json 的层界数;差太多说明打包没按结构走

用法: python src/tools/audit_deliverable.py [目录|xlsx ...]   # 无参数=最终交付包
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

from openpyxl import load_workbook

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.core import paths  # noqa: E402

SENTINEL = re.compile(r"@[草单条]")
NUM = re.compile(r"^-?\d+(?:\.\d+)?$")
NUM_COLS = ("深度", "起始深度", "终了深度", "层厚", "采长", "真厚")
MULTI = re.compile(r"-?\d+(?:\.\d+)?")


def audit(xlsx: Path):
    ws = load_workbook(xlsx, read_only=True, data_only=True).active
    rows = list(ws.iter_rows(values_only=True))
    if not rows:
        return {"file": xlsx.name, "空表": True}
    head = [str(c).strip() if c is not None else "" for c in rows[0]]
    idx = {name: i for i, name in enumerate(head) if name in NUM_COLS}
    sent = multi = badtype = blank_num = 0
    for r, row in enumerate(rows[1:], start=2):
        for name, i in idx.items():
            v = row[i] if i < len(row) else None
            if v is None or (isinstance(v, str) and not v.strip()):
                blank_num += 1
                continue
            s = str(v).strip()
            if SENTINEL.search(s):
                sent += 1
            elif not NUM.fullmatch(s):
                badtype += 1
                if len(MULTI.findall(s)) >= 2:
                    multi += 1
    return {"file": xlsx.name, "数据行": len(rows) - 1,
            "哨兵": sent, "非数值": badtype, "多值格": multi, "空值次": blank_num}


def main():
    argv = sys.argv[1:]
    files = []
    for a in argv:
        p = Path(a)
        files += sorted(p.glob("*.xlsx")) if p.is_dir() else [p]
    files = [f for f in files if not f.name.startswith("~$")]  # Excel 打开时的锁文件非交付物
    if not files:
        files = sorted((paths.PROJECT_ROOT / "outputs/Excel交付_最终_20260915").glob("*.xlsx"))
    rep = [audit(f) for f in files]
    tot = {k: sum(r.get(k, 0) or 0 for r in rep) for k in ("哨兵", "非数值", "多值格")}
    for r in rep:
        flag = "✗" if (r.get("哨兵") or r.get("多值格")) else " "
        print(f"{flag} {r['file']:<44} 行 {r.get('数据行','-'):>4} 哨兵 {r.get('哨兵',0):>4} "
              f"非数值 {r.get('非数值',0):>5} 多值格 {r.get('多值格',0):>5}")
    print(f"合计 {len(rep)} 表:哨兵 {tot['哨兵']} 非数值 {tot['非数值']} 多值格 {tot['多值格']}")
    return 1 if tot["哨兵"] else 0


if __name__ == "__main__":
    sys.exit(main())
