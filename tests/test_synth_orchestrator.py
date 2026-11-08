# -*- coding: utf-8 -*-
"""编排:seed 决定一切;产物三件齐;参数采样在约束带内。"""
import json

from src.synth.synthesize import synthesize_one, sample_params


def test_sample_params_within_bands():
    for seed in (1, 2, 3):
        wp, pp = sample_params(seed)
        assert 20 <= wp.amp1 <= 60 and 0 <= abs(wp.tilt) <= 40
        assert 0 <= pp.blur_sigma <= 1.5 and 0 <= pp.noise_sigma <= 6


def test_synthesize_one_small(tmp_path, monkeypatch, small_spec):
    monkeypatch.setattr("src.synth.synthesize.spec_for", lambda seed: small_spec)
    name, ok, info = synthesize_one(42, out_root=tmp_path)
    assert ok, info
    scan = tmp_path / "scans" / f"{name}.png"
    gt = tmp_path / "gt" / f"{name}_gt.json"
    prev = tmp_path / "preview" / f"{name}_preview.png"
    assert scan.exists() and gt.exists() and prev.exists()
    g = json.loads(gt.read_text(encoding="utf-8"))
    assert g["seed"] == 42 and g["image_size"] == [1200, 800]


def test_deterministic_outputs(tmp_path, monkeypatch, small_spec):
    # 同 seed 两次全链,GT 与扫描图字节级一致(小图跑,确定性不依赖图幅)
    monkeypatch.setattr("src.synth.synthesize.spec_for", lambda seed: small_spec)
    _, ok1, info1 = synthesize_one(7, out_root=tmp_path)
    assert ok1, info1
    a = (tmp_path / "gt" / "synth_0007_gt.json").read_bytes()
    pa = (tmp_path / "scans" / "synth_0007.png").read_bytes()
    (tmp_path / "gt" / "synth_0007_gt.json").unlink()
    (tmp_path / "scans" / "synth_0007.png").unlink()
    _, ok2, info2 = synthesize_one(7, out_root=tmp_path)
    assert ok2, info2
    b = (tmp_path / "gt" / "synth_0007_gt.json").read_bytes()
    pb = (tmp_path / "scans" / "synth_0007.png").read_bytes()
    assert a == b and pa == pb   # GT 与扫描图都字节级一致
