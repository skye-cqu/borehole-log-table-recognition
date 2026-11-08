# -*- coding: utf-8 -*-
"""串联胶水:paths 沙箱 patch 往返 + 合成角色推导。"""
from src.core import paths
from src.synth.chain import sandbox_paths


def test_sandbox_paths_patch_and_restore(tmp_path):
    raw = tmp_path / "raw"
    with sandbox_paths(tmp_path) as s:
        assert paths.RAW_DIR == raw
        assert paths.BINARIZED_DIR == tmp_path / "二值处理"
        assert paths.SYNTH_GT_DIR == paths.SYNTH_DIR / "gt"   # import 期绑定的派生量不受影响
    assert paths.RAW_DIR != raw


def test_sandbox_layout_complete(tmp_path):
    with sandbox_paths(tmp_path) as s:
        assert s["stem_jpg"].name.endswith(".JPG")


def test_synth_finalize_maps_roles_by_geometry(tmp_path):
    """判定 separators/frames 按 x_at_mid 匹配 GT 列:内列→columns,侧框→frames。"""
    import json

    from src.synth.chain import synth_finalize
    judging = {
        "separators": [
            {"no": 1, "x_at_mid": 223.0, "y": [100, 14000], "segment_ids": [1, 2]},
            {"no": 2, "x_at_mid": 500.0, "y": [100, 14000], "segment_ids": [3]},
            {"no": 3, "x_at_mid": 700.0, "y": [100, 14000], "segment_ids": [4]},
        ],
        "frames": [{"x_at_mid": 60.0, "y": [90, 14010], "segment_ids": [9]},
                   {"x_at_mid": 3000.0, "y": [90, 14010], "segment_ids": [8]}],
        "others": [],
    }
    gt = {"lines": [
        {"line_id": "col_0", "role": "frame_side", "polyline_warp": [[60, 0], [60, 14000]]},
        {"line_id": "col_1", "role": "column", "polyline_warp": [[224, 0], [222, 14000]]},
        {"line_id": "col_2", "role": "column", "polyline_warp": [[500, 0], [500, 14000]]},
        {"line_id": "col_3", "role": "frame_side", "polyline_warp": [[3000, 0], [3000, 14000]]},
    ]}
    p = tmp_path / "judging.json"
    p.write_text(json.dumps(judging, ensure_ascii=False), encoding="utf-8")
    struct = synth_finalize(p, gt, tmp_path / "定稿.json")
    assert [c["src"] for c in struct["columns"]] == [1, 2]      # no.3(700) 离 GT 列远→不收
    assert [f["x_at_mid"] for f in struct["frames"]] == [60.0, 3000.0]
    # side 按位置派生(镜像已核验基线语义:真实定稿 frames 带 side=left/right)
    sides = {f["x_at_mid"]: f.get("side") for f in struct["frames"]}
    assert sides[60.0] == "left" and sides[3000.0] == "right"
