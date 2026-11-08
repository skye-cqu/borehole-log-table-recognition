# -*- coding: utf-8 -*-
"""6b v3:表头映射边界几何来自 _分割线 真段(单一真源)。"""
from src.table import header_assign as ha

EXPECTED = ["地质时代", "煤层标志层号", "深度", "层厚", "采长", "倾角", "真厚", "岩性描述"]


def test_determine_v3_1015_full_layout(tmp_path, monkeypatch):
    # 定稿产物只读:determine() 会写 {stem}_表头映射.json,这里改到临时目录,
    # 否则跑测试会覆盖 30 张定稿基线(runs/ 虽被 gitignore,但基线是不可再生资产)。
    monkeypatch.setattr(ha.paths, "RUNS_DIR", tmp_path / "runs")
    (tmp_path / "runs" / "table_reconstruct").mkdir(parents=True)
    o = ha.determine("钻孔柱状图1015")
    names = [c["name"] for c in o["columns"]]
    assert names == EXPECTED, names
    assert o["keep"] and all("left_sep" in c and "right_sep" in c for c in o["keep"])
    # v3 新增:边界真段几何,供 build_cells 直接插值;与 sep_x_band 同长同序(x 升序)
    assert len(o["sep_pts"]) == len(o["sep_x_band"])
    for b in o["sep_pts"]:
        assert b["ys"] and len(b["ys"]) == len(b["xs"])
        assert b["ys"] == sorted(b["ys"])
    # 表头底界 band 落在图幅上部
    assert 100 < o["band"][1] < 3000


def test_sep_bounds_true_segments_only():
    """边界来自 line_parts 真段:不含被剔的带内碎片;ys 升序。"""
    bounds = ha._sep_bounds("钻孔柱状图1015")
    assert len(bounds) >= 9          # 9 条列线 + 左右框边
    kinds = {b["kind"] for b in bounds}
    assert "column" in kinds
    for b in bounds:
        assert len(b["ys"]) == len(b["xs"]) >= 2
        assert b["ys"] == sorted(b["ys"])