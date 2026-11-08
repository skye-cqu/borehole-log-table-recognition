# -*- coding: utf-8 -*-
"""阶段6：Agnes API 逐编号识图验收。
输入 {stem}_验收叠加图.png → 纵向 3 段 JPEG → agnes-2.5-flash（推理模型，
max_tokens≥4096 否则 content 为空）逐编号判定 column/content/frame/unknown；
跨段合并取最保守（任何段判 content/frame 即降级）。输出 {stem}_agnes验收.json。
key：runs/agnes_api_key.env → AGNES_API_KEY（不落代码）。"""
from __future__ import annotations

import base64
import json
import os
import re
import sys
import time
from pathlib import Path

import cv2
import requests

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.core import paths  # noqa: E402

_env = paths.RUNS_DIR / "agnes_api_key.env"
if _env.exists() and not os.environ.get("AGNES_API_KEY"):
    for line in _env.read_text(encoding="utf-8").strip().splitlines():
        k, _, v = line.partition("=")
        os.environ.setdefault(k.strip(), v.strip())

API_BASE = "https://apihub.agnes-ai.com/v1"
MODEL = "agnes-2.5-flash"
MAX_TOKENS = 20000
PROMPT = """你是表格列线验收员。图中：红色粗线+数字红圈=程序判定的"列分隔线"候选；灰色=外框；压暗变淡的线=内容线；橙色=存疑；细红横线=原图红笔标注（忽略）。
表格表头（多数图）：地质时代|煤层标志层号|深度|层厚|采长|倾角|真厚|柱状|岩性描述|简易水文曲线。柱状列内部两条贴近条带边与水文曲线区内部竖线属于内容线，不是列分隔线。
任务：对图中每个数字编号，判定该红线是否为真列分隔线：column（是）/ content（否，内容线误标）/ frame（否，外框）/ unknown（无法判断）。
并给出 missed：明显是真分隔线但无编号的竖线（没有则空表）。
只输出一个 JSON 对象，格式：{"numbers": {"1": "column", "2": "content"}, "missed": []}"""


def ask(jpeg_bytes, timeout=150, retries=3, prompt=None):
    """官方限制：免费用户 RPM=20（wiki/zh docs/code.md）。429/5xx 时等待后重试。"""
    key = os.environ["AGNES_API_KEY"]
    b64 = base64.b64encode(jpeg_bytes).decode("ascii")
    payload = {"model": MODEL, "temperature": 0, "max_tokens": MAX_TOKENS,
               "messages": [{"role": "user", "content": [
                   {"type": "text", "text": prompt or PROMPT},
                   {"type": "image_url",
                    "image_url": {"url": f"data:image/jpeg;base64,{b64}"}}]}]}
    for attempt in range(retries + 1):
        try:
            resp = requests.post(f"{API_BASE}/chat/completions", json=payload,
                                 headers={"Authorization": f"Bearer {key}",
                                          "Content-Type": "application/json"},
                                 timeout=timeout)
        except Exception:
            time.sleep(15 * (attempt + 1))
            continue
        if resp.status_code == 429:
            time.sleep(60)
            continue
        if resp.status_code >= 500:
            time.sleep(20 * (attempt + 1))
            continue
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"]
    raise RuntimeError("Agnes 重试次数耗尽")


def parse(content):
    m = re.search(r"\{.*\}", content, re.S)
    if not m:
        return None
    try:
        d = json.loads(m.group(0))
        return d.get("numbers"), d.get("missed", [])
    except Exception:
        return None


def verify(stem, bands=1):
    viz = cv2.imread(str(paths.RUNS_DIR / "table_reconstruct" / f"{stem}_验收叠加图.png"))
    H, W = viz.shape[:2]
    merged, missed, raw = {}, [], []
    prio = {"content": 0, "frame": 1, "unknown": 2, "column": 3}
    # 用户指定：不用整图，只取顶部 图宽×图宽 方形区域
    bands = 1
    x1 = W
    y1 = min(H, W)
    ok, jpeg = cv2.imencode(".jpg", viz[0:y1, 0:x1], [cv2.IMWRITE_JPEG_QUALITY, 85])
    content = ask(jpeg.tobytes())
    raw.append(content[:200])
    parsed = parse(content)
    if parsed:
        nums, ms = parsed
        for n, r in (nums or {}).items():
            n = str(int(n))
            r = r if r in prio else "unknown"
            merged[n] = min(merged.get(n, "column"), r, key=lambda x: prio[x])
        missed.extend(ms or [])
    out = {"image": stem, "numbers": merged, "missed": sorted(set(missed)),
           "columns": sorted(int(k) for k, v in merged.items() if v == "column"),
           "bands_parsed": 1 if parsed else 0, "raw_head": raw,
           "crop": [0, 0, x1, y1]}
    json.dump(out, open(paths.RUNS_DIR / "table_reconstruct" / f"{stem}_agnes验收.json",
                        "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    return out


def main():
    stems = sys.argv[1:] or ["钻孔柱状图1019"]
    if stems == ["--all"]:
        from concurrent.futures import ThreadPoolExecutor, as_completed
        stems = sorted(p.stem for p in paths.CANDIDATE_COORD_DIR.glob("*.json"))
        # 官方限制：免费用户 RPM=20。单次调用约 1-2 分钟，8 并发实际 RPM≈4-8，合规。
        with ThreadPoolExecutor(max_workers=8) as ex:
            futs = {ex.submit(verify, s): s for s in stems}
            for fu in as_completed(futs):
                s = futs[fu]
                try:
                    o = fu.result()
                    print(s, "column:", o["columns"], "解析:", o["bands_parsed"], flush=True)
                except Exception as e:
                    print(s, "FAIL", repr(e)[:100], flush=True)
        return
    for stem in stems:
        o = verify(stem)
        print(stem, "column:", o["columns"], "missed:", o["missed"][:3],
              "段解析:", o["bands_parsed"], "/ 1")


if __name__ == "__main__":
    main()
