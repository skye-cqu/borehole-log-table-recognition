# -*- coding: utf-8 -*-
"""Agnes 补读全量扫描(2026-11-06 用户批准):给缺 Agnes 源的 desc 格补图上读数。

目标 = 全库 desc 非空 且 pack_bridge 无 Agnes 读的格(跨族定级的前提)。
调用:agnes_post.ask(限速 3.2s/次,429/5xx 重试,temperature=0,
max_tokens≥4096 推理模型教训);单格单调用,格级断点续跑。
出 runs/autoresearch_align/agnes_resweep.json:
    {stem: {"行<r>": {"read": str, "耗时s": f}}}
裁窗与 RapidOCR 窄窗同几何(desc 列界+行区间,小 pad),原图 JPG 灰度裁片。
"""
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import numpy as np
from openpyxl import load_workbook

from src.core import paths
from src.handwriting import rules as R
from src.handwriting.cellcrop import crop_window
from src.handwriting.normalizers import norm_desc

OUT = paths.AUTORESEARCH_DIR / "agnes_resweep.json"

PROMPT = ("逐字转写图中手写的中文地质描述文字。只输出转写文本本身,"
          "不要解释、不要加标点、不要漏字;看不清的字用□占位。")

GROUP = 4          # 4 格堆叠一 call(免费档 RPM=20 是地板,砍调用数 4 倍)
SEP = 6            # 段间黑分隔线像素
TIMEOUT_S = 90
RETRIES = 2
BREAK_N = 4        # 连续失败熔断:API 劣化时不烧超时,整轮退出交重试环


def _targets():
    """{(stem, 行): 无 Agnes 读的 desc 非空格}。"""
    bridge = R._bridge()
    out = {}
    for p in sorted(paths.AUTORESEARCH_CANDIDATE_DIR.glob("*_整合.xlsx")):
        stem = p.name[: -len("_整合.xlsx")]
        rows = list(load_workbook(p, read_only=True).active.iter_rows(values_only=True))
        dcol = R.resolve_roles(rows[0]).get("desc")
        if dcol is None:
            continue
        for i, row in enumerate(rows[1:]):
            if not norm_desc(row[dcol] if dcol < len(row) else None):
                continue
            agnes = ((bridge.get(stem, {}).get(f"行{i + 2}") or {}).get("agnes")
                     or [])
            if not [a for a in agnes if a and str(a).strip()]:
                out[(stem, i + 2)] = True
    return out


def worker(payload):
    """单图顺序补读(限速串行,无并行):吃 (stem全称, [行]),格级断点续跑。"""
    stem, rows_ = payload
    try:
        import cv2
        from src.table import agnes_post
        hm = json.load(open(paths.RUNS_DIR / "table_reconstruct" /
                            f"{stem}_表头映射.json", encoding="utf-8"))
        keep = None
        for k in hm["keep"]:
            if k["name"] == "岩性描述":
                keep = sorted(k["x_in_band"])
        if not keep:
            return stem, False, "无desc列界"
        x0, x1 = keep
        cache = json.loads(paths.AUTORESEARCH_ROWCACHE.read_text(encoding="utf-8"))
        ivs = {int(k): tuple(float(a) for a in v)
               for k, v in cache[stem]["ivs"].items()}
        gray = cv2.imread(str(paths.RAW_DIR / f"{stem}.JPG"),
                          cv2.IMREAD_GRAYSCALE)
        done = {}
        if OUT.exists():
            done = json.loads(OUT.read_text(encoding="utf-8")).get(stem, {})
        todo = []
        for r in sorted(rows_):
            if f"行{r}" in done or r - 2 not in ivs:
                continue
            y0, y1 = ivs[r - 2]               # ivs 键=数据行下标(reread.py 同款)
            if y1 - y0 > 400:
                continue                      # 巨行守卫
            todo.append(r)
        t0, n_new, consec_fail = time.time(), 0, 0
        for g0 in range(0, len(todo), GROUP):
            grp = todo[g0:g0 + GROUP]
            wins = []
            for r in grp:
                y0, y1 = ivs[r - 2]
                win = crop_window(gray, x0, x1, y0, y1, pad_l=8, pad_r=8)
                if win is None:
                    wins.append(None)
                    continue
                okj, buf = cv2.imencode(".jpg", win)
                wins.append(buf.tobytes() if okj else None)
            imgs = [w for w in wins if w]
            if not imgs:
                continue
            dec = [cv2.imdecode(np.frombuffer(w, np.uint8), cv2.IMREAD_COLOR)
                   for w in imgs]
            wmax = max(d.shape[1] for d in dec)
            parts = []
            for k, d in enumerate(dec):
                if k:
                    parts.append(np.zeros((SEP, wmax, 3), np.uint8))
                if d.shape[1] < wmax:
                    d = np.hstack([d, np.full((d.shape[0], wmax - d.shape[1], 3),
                                              255, np.uint8)])
                parts.append(d)
            canvas = np.vstack(parts)
            okc, bufc = cv2.imencode(".jpg", canvas)
            if not okc:
                continue
            prompt = (f"图中有{len(grp)}段手写中文地质描述,从上到下按顺序逐字转写。"
                      "只输出转写文本,段与段之间用一个换行分隔,不要段号、"
                      "不要解释、不要加标点;看不清的字用□占位。")
            try:
                resp = agnes_post.ask(prompt, image_jpeg=bufc.tobytes(),
                                      max_tokens=4096, timeout=TIMEOUT_S,
                                      retries=RETRIES)
                consec_fail = 0
            except Exception:
                consec_fail += 1
                if consec_fail >= BREAK_N:
                    return stem, False, (f"熔断:连续{BREAK_N}次调用失败"
                                         f"(已完成{n_new}格)")
                continue
            lines = [ln.strip() for ln in str(resp).strip().splitlines()
                     if ln.strip()]
            if len(lines) != len(grp):
                continue                      # 段数不齐=对不齐,宁缺(下轮重读)
            for r, ln in zip(grp, lines):
                if ln and ln not in ("□", "无"):
                    done[f"行{r}"] = {"read": ln, "耗时s": round(time.time() - t0, 1)}
                    n_new += 1
            out = json.loads(OUT.read_text(encoding="utf-8")) if OUT.exists() else {}
            out.setdefault(stem, {}).update(done)
            OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1),
                           encoding="utf-8")
        # 尾组/段数不齐宁缺的格:逐格单读兜底(同一批准范围内收尾)
        for r in todo:
            if f"行{r}" in done:
                continue
            y0, y1 = ivs[r - 2]
            win = crop_window(gray, x0, x1, y0, y1, pad_l=8, pad_r=8)
            if win is None:
                continue
            okj, buf = cv2.imencode(".jpg", win)
            if not okj:
                continue
            try:
                resp = agnes_post.ask(PROMPT, image_jpeg=buf.tobytes(),
                                      max_tokens=4096, timeout=TIMEOUT_S,
                                      retries=RETRIES)
                consec_fail = 0
            except Exception:
                consec_fail += 1
                if consec_fail >= BREAK_N:
                    return stem, False, (f"熔断:连续{BREAK_N}次调用失败"
                                         f"(单读阶段,已完成{n_new}格)")
                continue
            txt = str(resp).strip().splitlines()[0].strip() \
                if str(resp).strip() else ""
            if txt and txt not in ("□", "无"):
                done[f"行{r}"] = {"read": txt,
                                  "耗时s": round(time.time() - t0, 1)}
                n_new += 1
                out = (json.loads(OUT.read_text(encoding="utf-8"))
                       if OUT.exists() else {})
                out.setdefault(stem, {}).update(done)
                OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1),
                               encoding="utf-8")
        return stem, True, f"补读{n_new}格 {round(time.time() - t0, 1)}s"
    except Exception as e:  # noqa: BLE001
        return stem, False, f"{type(e).__name__}: {e}"


def main():
    tg = _targets()
    per = {}
    for stem, r in tg:
        per.setdefault(stem, []).append(r)
    print(f"缺 Agnes 源格 {len(tg)} / {len(per)} 图")
    from src.core import batch
    items = sorted(per.items())
    results = batch.run_batch(items, worker, max_workers=1)  # 限速串行
    for stem, ok, info in results:
        print(f"  {stem} {'OK' if ok else 'FAIL'} {info}")
    bad = [s for s, ok, _i in results if not ok]
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
