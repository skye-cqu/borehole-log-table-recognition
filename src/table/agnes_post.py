# -*- coding: utf-8 -*-
"""Agnes 后处理客户端(整合表管线用):文本校对 + 时代条带视觉复读。

免费档限制 RPM=20(wiki/zh docs/code.md):RateLimiter 强制任意两次调用 ≥3.2s。
agnes-2.5-flash 为推理模型,max_tokens≥4096 否则 content 为空(实测教训)。
key:runs/agnes_api_key.env → AGNES_API_KEY(不落代码)。"""
import os
import time

import requests

API_BASE = "https://apihub.agnes-ai.com/v1"
MODEL = "agnes-2.5-flash"
MIN_GAP = 3.2          # RPM=20 → 单调用间隔下限 s
_last = [0.0]


def _key():
    if not os.environ.get("AGNES_API_KEY"):
        from src.core import paths
        envf = paths.RUNS_DIR / "agnes_api_key.env"
        if envf.exists():
            for line in envf.read_text(encoding="utf-8").strip().splitlines():
                k, _, v = line.partition("=")
                os.environ.setdefault(k.strip(), v.strip())
    return os.environ["AGNES_API_KEY"]


def _throttle():
    wait = MIN_GAP - (time.monotonic() - _last[0])
    if wait > 0:
        time.sleep(wait)
    _last[0] = time.monotonic()


def ask(prompt, image_jpeg=None, max_tokens=8192, timeout=180, retries=3, mime="image/jpeg"):
    """一次调用(文本或视觉);429/5xx 等待重试;返回 content 字符串。
    mime 可换 image/png(时代带整块复读走无损,原始像素不缩放)。"""
    key = _key()
    content = [{"type": "text", "text": prompt}]
    if image_jpeg is not None:
        import base64
        b64 = base64.b64encode(image_jpeg).decode("ascii")
        content.append({"type": "image_url",
                        "image_url": {"url": f"data:{mime};base64,{b64}"}})
    payload = {"model": MODEL, "temperature": 0, "max_tokens": max_tokens,
               "messages": [{"role": "user", "content": content}]}
    for attempt in range(retries + 1):
        _throttle()
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
            _last[0] = time.monotonic()
            continue
        if resp.status_code >= 500:
            time.sleep(20 * (attempt + 1))
            continue
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"]
    raise RuntimeError("Agnes 重试次数耗尽")
