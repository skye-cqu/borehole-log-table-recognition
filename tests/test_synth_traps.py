# -*- coding: utf-8 -*-
"""必错图判据:预期违规检查函数必须能区分"抓到"与"没抓到"。"""
from src.synth.traps import FAINT_COLS, TRAPS, _check_bridge, _check_deco, _check_faint


def _card(sides_missing=(), sides_extras=(), cols_missing=(), bridged=0):
    def fam(lines, extras, bridged_n):
        return {"lines": [{"line_id": lid, "found": lid not in lines,
                           "dev": {"p95": None}} for lid in lines],
                "missing": list(lines), "extras": list(extras),
                "bridged_samples": bridged_n, "uncovered": []}
    return {"families": {
        "columns": fam(cols_missing, [], bridged if False else 0),
        "sides": fam(sides_missing, sides_extras, 0),
        "frame_tb": fam((), [], bridged),
    }}


def test_traps_registry_wellformed():
    assert set(TRAPS) == {"deco", "faint", "bridge"}
    for overrides, check, desc in TRAPS.values():
        assert isinstance(overrides, dict) and callable(check) and desc


def test_check_deco_catches_extras_and_right_missing():
    extra = [{"index": 0, "x": 3014.0, "y": 7111.0}]
    assert _check_deco(_card(sides_extras=extra))
    assert _check_deco(_card(sides_missing=("col_11",)))
    assert _check_deco(_card()) is None


def test_check_faint_catches_only_faint_cols():
    assert _check_faint(_card(cols_missing=FAINT_COLS))
    assert _check_faint(_card(cols_missing=("col_7",))) is None


def test_check_bridge_catches_bridged_samples():
    assert _check_bridge(_card(bridged=12))
    assert _check_bridge(_card()) is None
