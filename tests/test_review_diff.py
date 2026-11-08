# -*- coding: utf-8 -*-
"""review_diff:两代数据集数据级 diff。"""
from src.tools.review_diff import diff_cols, diff_rows


def _ds(rows, cols=(), edges=()):
    lines = []
    for rid, pts in rows:
        lines.append({"kind": "row", "line_id": rid, "points": pts})
    for i, (cid, pts, backing) in enumerate(cols, 1):
        lines.append({"kind": "col", "line_id": f"C{i:03d}", "col_index": i,
                      "backing": backing, "points": pts})
    for i, (side, pts) in enumerate(edges, 1):
        lines.append({"kind": "edge", "line_id": f"E{i:03d}", "side": side, "points": pts})
    return {"image": "t", "width": 3200, "height": 18661, "lines": lines,
            "n_row_segs": len(rows), "n_col_segs": len(cols), "n_edge_segs": len(edges)}


def test_rows_identical_zero_drift():
    pts = [[100.0, 500.0], [900.0, 500.5]]
    r = diff_rows(_ds([("R001", pts)]), _ds([("R001", [list(p) for p in pts])]))
    assert r["n_moved"] == 0 and r["added"] == [] and r["removed"] == []
    assert r["residual"]["max"] == 0.0


def test_rows_moved_added_removed():
    old = _ds([("R001", [[0.0, 0.0], [10.0, 0.0]]),
               ("R002", [[0.0, 5.0], [10.0, 5.0]])])
    new = _ds([("R001", [[0.0, 0.0], [10.0, 0.0]]),
               ("R002", [[0.0, 9.0], [10.0, 9.0]]),
               ("R003", [[0.0, 20.0], [10.0, 20.0]])])
    r = diff_rows(old, new)
    assert [m["line_id"] for m in r["moved"]] == ["R002"]
    assert r["moved"][0]["d"] == 4.0
    assert r["added"] == ["R003"] and r["removed"] == []


def test_rows_point_count_mismatch_counts_as_moved():
    r = diff_rows(_ds([("R001", [[0.0, 0.0], [10.0, 0.0]])]),
                  _ds([("R001", [[0.0, 0.0], [5.0, 0.0], [10.0, 0.0]])]))
    assert r["n_moved"] == 1 and r["moved"][0]["why"] == "点数不同"


def test_cols_account_counts_backing():
    a = _ds([], cols=[(1, [[5.0, 0.0], [5.0, 100.0]], "frag")],
            edges=[("left", [[0.0, 0.0], [0.0, 100.0]])])
    b = _ds([], cols=[(1, [[5.0, 0.0], [5.0, 60.0]], "frag"),
                      (1, [[5.0, 60.0], [5.0, 100.0]], "fill")],
            edges=[("left", [[0.0, 0.0], [0.0, 100.0]])])
    r = diff_cols(a, b)
    assert r["old"]["col_segs"] == 1 and r["new"]["col_segs"] == 2
    assert r["new"]["backing"] == {"frag": 1, "fill": 1, "extend": 0}
    assert r["old"]["edge_segs"] == 1 and r["new"]["edge_segs"] == 1
