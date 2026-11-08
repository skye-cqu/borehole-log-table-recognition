# -*- coding: utf-8 -*-
"""make_manifest:生成/对照 产物目录指纹。"""
import json

from src.tools.make_manifest import NAME, check, make


def _mk(root):
    (root / "a.txt").write_text("hello", encoding="utf-8")
    (root / "sub").mkdir()
    (root / "sub" / "b.json").write_text("{}", encoding="utf-8")


def test_make_then_check_clean(tmp_path):
    _mk(tmp_path)
    make(tmp_path)
    assert (tmp_path / NAME).exists()
    assert check(tmp_path) == {"added": [], "missing": [], "changed": []}


def test_check_detects_change_add_remove(tmp_path):
    _mk(tmp_path)
    make(tmp_path)
    (tmp_path / "a.txt").write_text("tampered", encoding="utf-8")
    (tmp_path / "c.txt").write_text("new", encoding="utf-8")
    (tmp_path / "sub" / "b.json").unlink()
    r = check(tmp_path)
    assert r["changed"] == ["a.txt"]
    assert r["added"] == ["c.txt"]
    assert r["missing"] == ["sub/b.json"]


def test_manifest_excludes_itself_and_respects_glob(tmp_path):
    _mk(tmp_path)
    make(tmp_path, globs=("*.json",))
    man = json.load(open(tmp_path / NAME, encoding="utf-8"))
    assert list(man["files"]) == ["sub/b.json"]
    # check 必须与 make 同一 glob 范围对照
    assert check(tmp_path, globs=("*.json",)) == {"added": [], "missing": [], "changed": []}


def test_code_commit_recorded(tmp_path):
    _mk(tmp_path)
    make(tmp_path)
    man = json.load(open(tmp_path / NAME, encoding="utf-8"))
    assert man["generated_by"] == "src/tools/make_manifest.py"
    assert man["code_commit"] and man["code_commit"] != "unknown"


def test_audit_against_manifest_exit_codes(tmp_path):
    """audit_line_dataset --against-manifest:干净过、漂移退 1。"""
    import sys

    from src.tools import audit_line_dataset

    _mk(tmp_path)
    make(tmp_path)
    sys.argv = ["audit_line_dataset.py", str(tmp_path), "--against-manifest"]
    try:
        audit_line_dataset.main()
        code_clean = 0
    except SystemExit as e:
        code_clean = e.code
    assert code_clean == 0

    (tmp_path / "a.txt").write_text("drift", encoding="utf-8")
    try:
        audit_line_dataset.main()
        code_bad = 0
    except SystemExit as e:
        code_bad = e.code
    assert code_bad == 1
