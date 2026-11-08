# -*- coding: utf-8 -*-
"""1032 行带数多丢 1 条:定位是 drop_header_rows 还是 unstuck_chain。"""
import sys, json
from pathlib import Path
R = Path(r"D:\Skye\Documents\Work\高维智矿\7.13杂活")
sys.path.insert(0, str(R))
from src.table import era_chars as E
from src.table.track_rows import row_y
from src.table.finalize_tables import drop_header_rows, unstuck_chain
from openpyxl import load_workbook

for k in ["1015","1032","1042"]:
    stem = f"钻孔柱状图{k}"
    hm, rd = E._load_inputs(stem)
    midx = sum(rd["table_x"])/2.0
    rows_r = [r for r in rd["rows"] if row_y(r, midx) >= hm["band"][1]]
    x_era = sum(hm["keep"][0]["x_in_band"])/2
    ys = [row_y(r, x_era) for r in rows_r]
    p = R/"runs"/"table_reconstruct_重出_20261005_项④行线补全"/f"{stem}_还原.xlsx"
    ws = load_workbook(p).active
    n_data = ws.max_row - 1
    print("%s: B还原 数据行=%d  行判定数据带=%d  带-1=%d  差=%d" % (k, n_data, len(ys), len(ys)-1, n_data-(len(ys)-1)))
    data = list(ws.iter_rows(values_only=True))
    d2, y2, dropped = drop_header_rows(data, ys)
    print("   drop_header_rows 剔除行=%s  -> 剩 %d 行 / %d 界" % (dropped, len(d2), len(y2)))
    d3, y3, ops, led = unstuck_chain(d2, y2)
    print("   unstuck_chain 操作=%s  -> 剩 %d 行 / %d 界" % (ops, len(d3), len(y3)))
