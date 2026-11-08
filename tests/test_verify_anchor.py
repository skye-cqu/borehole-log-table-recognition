# -*- coding: utf-8 -*-
"""锚点工具:freeze 固化 md5 基线;check 对新树对账,交外差异=新偏离。"""
import json

from src.verify.anchor_30 import check_tree, freeze_tree

# 30 张定稿的 5 类产物相对 runs/table_reconstruct 的文件名模式
PRODUCT_PATTERNS = ["{s}_列结构定稿.json", "{s}_分割线.json", "{s}_上下框.json",
                    "{s}_闭合外框.json", "{s}_矫正映射.json"]


def _make_tree(root, tweak_last=False):
    root.mkdir(parents=True)
    for s in ("1015", "1016"):
        for pat in PRODUCT_PATTERNS:
            p = root / pat.format(s=s)
            body = {"stem": s, "kind": pat, "v": 1}
            if tweak_last and s == "1016" and "闭合外框" in pat:
                body["v"] = 2          # 人为制造一处新偏离
            p.write_text(json.dumps(body, ensure_ascii=False), encoding="utf-8")


def test_freeze_then_check_clean(tmp_path):
    tree = tmp_path / "base"
    _make_tree(tree)
    baseline = freeze_tree(tree, PRODUCT_PATTERNS, ("1015", "1016"))
    assert len(baseline["files"]) == 10
    res = check_tree(tree, baseline)
    assert res["new_deviations"] == [] and res["pass"] is True


def test_check_catches_new_deviation(tmp_path):
    base, changed = tmp_path / "base", tmp_path / "changed"
    _make_tree(base)
    _make_tree(changed, tweak_last=True)
    baseline = freeze_tree(base, PRODUCT_PATTERNS, ("1015", "1016"))
    res = check_tree(changed, baseline)
    assert res["pass"] is False
    assert len(res["new_deviations"]) == 1
    assert "1016_闭合外框.json" in res["new_deviations"][0]["file"]


def test_expected_fail_absorbs_known(tmp_path):
    base, changed = tmp_path / "base", tmp_path / "changed"
    _make_tree(base)
    _make_tree(changed, tweak_last=True)
    baseline = freeze_tree(base, PRODUCT_PATTERNS, ("1015", "1016"))
    ef = {"items": [{"id": "x", "stems": ["1016"], "what": "闭合外框",
                     "files": ["1016_闭合外框.json"]}]}
    res = check_tree(changed, baseline, expected=ef)
    assert res["pass"] is True and res["absorbed"] == 1
