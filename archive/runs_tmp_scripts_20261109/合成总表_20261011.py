# -*- coding: utf-8 -*-
"""把 30 张整合 xlsx 合成一个总表:每图一个 sheet(sheet名=图号),样式/合并区/黄字全搬运。
用法: python runs/tmp/合成总表_20261011.py
"""
import sys
from copy import copy
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from src.core import paths  # noqa: E402
from openpyxl import Workbook, load_workbook  # noqa: E402

OUT = paths.RUNS_DIR / "全量整合_合订表_v7.xlsx"


def main():
    out_wb = Workbook()
    out_wb.remove(out_wb.active)
    total_yellow = total_merge = 0
    for k in range(1015, 1045):
        stem = f"钻孔柱状图{k}"
        src_p = paths.FINALIZE_FULL_DIR / f"{stem}_整合.xlsx"
        if not src_p.exists():
            print("SKIP", stem)
            continue
        src = load_workbook(src_p, rich_text=True).active   # rich text 字级红标必须带参读入
        ws = out_wb.create_sheet(title=str(k))
        for row in src.iter_rows():
            for c in row:
                t = ws.cell(row=c.row, column=c.column, value=c.value)
                # 样式表按工作簿-local,跨簿只能逐组件 copy(StyleProxy→实体对象)
                t.font = copy(c.font)
                t.fill = copy(c.fill)
                t.border = copy(c.border)
                t.alignment = copy(c.alignment)
                t.protection = copy(c.protection)
                t.number_format = c.number_format
        for m in src.merged_cells.ranges:
            ws.merge_cells(str(m))
        for col, dim in src.column_dimensions.items():
            ws.column_dimensions[col].width = dim.width
        for idx, dim in src.row_dimensions.items():
            ws.row_dimensions[idx].height = dim.height
        ws.freeze_panes = "A2"
        n_red = sum(1 for row in ws.iter_rows() for c in row
                    if (c.font and c.font.color and isinstance(c.font.color.rgb, str)
                        and c.font.color.rgb.endswith("FF0000"))
                    or (type(c.value).__name__ == "CellRichText"
                        and any(not isinstance(b, str) for b in c.value)))
        total_yellow += n_red
        total_merge += len(ws.merged_cells.ranges)
        print(f"{k}: {src.max_row}行 红{len(n_red if False else [0])*0+n_red} 合并{len(ws.merged_cells.ranges)}")
    out_wb.save(OUT)
    print("总表:", OUT, f"sheet={len(out_wb.sheetnames)} 红合计={total_yellow} 合并合计={total_merge}")


if __name__ == "__main__":
    main()
