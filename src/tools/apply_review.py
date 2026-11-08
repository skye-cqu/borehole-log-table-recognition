# -*- coding: utf-8 -*-
"""人审回写:把用户在复核包中择定的读数写回 4 张补产终版 xlsx。

输入 JSON 结构(层号 1 起,列名与表头一致):
  {
    "1018": {"3:深度": "48.53 49.30", "5:岩性描述": "表土。"},
    "1030": {...}
  }
用法: python src/tools/apply_review.py 人审回写.json [--rest-confirm]
效果: 更新 runs 终版 xlsx;待核清单对应处置改为"用户人审确认(回写)";
      留空值=确认保留草案(不写单元格,仅落账)。
      --rest-confirm: 点选页契约"未点的行视为确认草案"——把 JSON 中出现的图
      里其余仍"待人审"的格整体落账为"用户人审确认(确认草案)",不改值。
      仅在用户回传的是复核页整份导出/整份模板时加此旗;散句零星择定不加。
      打印各图剩余待人审数。之后重跑 package_final.py 同步交付包。

来源口径(--as):落账的处置前缀,默认"用户人审确认"。助手视觉判读等非人工
      来源必须显式传 --as "助手视觉判读",不得冒用人工确认口径。
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))
from src.core import paths  # noqa: E402

NUM_RE = re.compile(r"^-?\d+(\.\d+)?$")
STEMS4 = ("1018", "1030", "1032", "1042")
DEFAULT_PROV = "用户人审确认"


def main():
    argv = [a for a in sys.argv[1:] if not a.startswith("--")]
    rest = "--rest-confirm" in sys.argv[1:]
    prov = DEFAULT_PROV
    if "--as" in sys.argv[1:]:
        prov = sys.argv[1:][sys.argv[1:].index("--as") + 1]
    if not argv:
        print(__doc__)
        return
    rev = json.loads(Path(argv[0]).read_text(encoding="utf-8"))
    from openpyxl import Workbook, load_workbook
    for code, cells in rev.items():
        if code not in STEMS4:
            print(f"{code}: 非 4 张补产图,跳过")
            continue
        stem = f"钻孔柱状图{code}"
        xp = paths.RUNS_DIR / "table_reconstruct" / f"{stem}_还原_补产终版.xlsx"
        wb = load_workbook(xp)
        ws = wb.active
        header = [c.value for c in ws[1]]
        fp = paths.RUNS_DIR / "table_reconstruct" / f"{stem}_待核清单.json"
        flags = json.loads(fp.read_text(encoding="utf-8"))
        n_ok = 0
        for key, val in cells.items():
            li_s, name = str(key).split(":", 1)
            li, j = int(li_s), header.index(name)
            val_s = str(val).strip()
            if val_s == "@EMPTY":       # 显式清空:本格实无手写内容(如 OCR 误读表头)
                ws.cell(row=li + 1, column=j + 1, value=None)
                fell = "@EMPTY(清除)"
            elif val_s:  # 留空=确认草案:不改单元格(草案本就在格内)
                v = float(val_s) if NUM_RE.match(val_s) else str(val)
                ws.cell(row=li + 1, column=j + 1, value=v)
                fell = val_s
            else:
                fell = "(确认草案)"
            for f in flags:
                if f["层"] == li and f["列"] == name and f["处置"] == "待人审":
                    f["处置"] = f"{prov}(回写)"
                    f["判读来源"] = prov
                    f["人审择定"] = fell
                    break
            n_ok += 1
        n_rest = 0
        if rest:
            for f in flags:
                if f["处置"] == "待人审":
                    f["处置"] = f"{prov}(确认草案)"
                    f["判读来源"] = prov
                    f["人审择定"] = "(未点选,确认草案)"
                    n_rest += 1
        wb.save(xp)
        fp.write_text(json.dumps(flags, ensure_ascii=False, indent=1),
                      encoding="utf-8")
        still = sum(1 for f in flags if f["处置"] == "待人审")
        msg = f"{stem}: 回写 {n_ok} 格 [来源 {prov}]"
        msg += f",其余 {n_rest} 格确认为草案" if rest else ""
        msg += f",剩待人审 {still}"
        print(msg)
    print("重跑 python src/tools/package_final.py 可同步交付包。")


if __name__ == "__main__":
    main()
