# -*- coding: utf-8 -*-
"""pytest 公共 fixtures：注入项目根与真实候选数据路径。"""
import json
from pathlib import Path

import pytest

from src.synth.layout import LayoutSpec

PROJECT_ROOT = Path(__file__).resolve().parents[1]
CANDIDATE_COORD_DIR = PROJECT_ROOT / "data" / "表格线候选识别处理" / "坐标数据"
SAMPLE_JSON = CANDIDATE_COORD_DIR / "钻孔柱状图1015.json"


@pytest.fixture(scope="session")
def project_root():
    return PROJECT_ROOT


@pytest.fixture(scope="session")
def candidate_coord_dir():
    return CANDIDATE_COORD_DIR


@pytest.fixture(scope="session")
def sample_data():
    """真实 1015 候选数据（只读，不修改）。"""
    if not SAMPLE_JSON.exists():
        pytest.skip("候选样本 钻孔柱状图1015.json 不存在")
    with open(SAMPLE_JSON, "r", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture
def small_spec():
    """合成门禁小样版式:4 列 3 行,强制断口,几何能装进 800x1200 画布。"""
    return LayoutSpec(
        width=800, height=1200, x0=60, y_top=40, header_h=60,
        row_heights=(120, 120, 120),
        merge_spans=((0, 1),),
        faint_cols={1}, faint_rows={2},
        break_prob=1.0,          # 小样里强制每条竖线都有断口,便于断言
        col_gaps=(160, 160, 160),
    )


@pytest.fixture
def make_line():
    """构造一条 line 字典的工厂（默认是一条合格的纵向 high 段）。"""
    def _make(label="high", direction="vertical", length=100.0, direct_ratio=1.0,
              midx=100.0, midy=100.0, points=None, crossing_count=0, band_id=0,
              band_size=2, line_id=0):
        if points is None:
            points = [[int(midx), 0], [int(midx), int(length)]]
        return {
            "id": line_id,
            "label": label,
            "direction": direction,
            "length": length,
            "direct_ratio": direct_ratio,
            "angle": 90.0 if direction == "vertical" else 0.0,
            "pca_angle": 90.0 if direction == "vertical" else 0.0,
            "deflection": 0.0,
            "w_over_h": length,
            "bbox": [midx, 0.0, midx, length],
            "midx": midx,
            "midy": midy,
            "band_id": band_id,
            "band_size": band_size,
            "crossing_count": crossing_count,
            "span_coverage": 0.8,
            "geo_score": 0.8,
            "struct_score": 0.6,
            "final_score": 0.7,
            "points": points,
        }
    return _make
