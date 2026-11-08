# -*- coding: utf-8 -*-
"""行带窗几何读(2026-11-11 用户处方):列界系统性截字 ~12.7% 实锤后的第三几何轴。

几何独立于单元格裁剪:x 取 desc 名义界的 ±150px 大余量(列界只作参考),
y 取行区间 ±8px 重叠。整行条带一次读,框级回收(box 中心/重叠过滤只作粗分配)。
出 runs/autoresearch_align/rowstrip_reads.json:
    {stem: {"行<r>": {"strip": str, "耗时s": f}}}
目标 = 定级账中非"可信·印证现值"的全部行(疑错/分裂/无收敛/同族多数/读数不足)。
"""
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.core import paths
from src.handwriting.reread import ROLE_KEEP, _ocr

OUT = paths.AUTORESEARCH_DIR / "rowstrip_reads.json"
PARTS = paths.AUTORESEARCH_DIR / "rowstrip_parts"
MX = 150              # 横向余量:列界降级为参考
MY = 8                # 纵向重叠
GRADE_SKIP = {("可信", "印证现值"), ("可信", "读截断(现值更全)")}


def target_rows():
    d = json.loads((paths.AUTORESEARCH_DIR / "多源定级_20261106" / "定级.json")
                   .read_text(encoding="utf-8"))
    per = {}
    for e in d["cells"]:
        if (e["级"], e.get("现值关系")) in GRADE_SKIP:
            continue
        per.setdefault(e["stem"], []).append(e["行"])
    return per


def worker(payload):
    stem, rows_ = payload
    try:
        import cv2
        hm = json.load(open(paths.RUNS_DIR / "table_reconstruct" /
                            f"钻孔柱状图{stem}_表头映射.json", encoding="utf-8"))
        keep = None
        for k in hm["keep"]:
            if k["name"] == ROLE_KEEP["desc"]:
                keep = sorted(k["x_in_band"])
        if not keep:
            return stem, False, "无desc列界"
        x0, x1 = int(keep[0]), int(keep[1])
        cache = json.loads(paths.AUTORESEARCH_ROWCACHE.read_text(encoding="utf-8"))
        ivs = {int(k2): tuple(float(a) for a in v)
               for k2, v in cache[f"钻孔柱状图{stem}"]["ivs"].items()}
        gray = cv2.imread(str(paths.RAW_DIR / f"钻孔柱状图{stem}.JPG"),
                          cv2.IMREAD_GRAYSCALE)
        W = gray.shape[1]
        xa, xb = max(0, x0 - MX), min(W, x1 + MX)
        ocr = _ocr()
        ev = {}
        t0 = time.time()
        for r in sorted(rows_):
            if r - 2 not in ivs:
                continue
            y0, y1 = (int(v) for v in ivs[r - 2])
            if y1 - y0 > 400:
                continue
            ya, yb = max(0, y0 - MY), min(gray.shape[0], y1 + MY)
            win = gray[ya:yb, xa:xb]
            if win.size == 0:
                continue
            res, _ = ocr(win)
            frags = []
            for box, t, _conf in (res or []):
                xs = sorted(p[0] for p in box)
                bl, br = xs[0] + xa, xs[-1] + xa
                if br < x0 - 60 or bl > x1 + 120:
                    continue                      # 粗分配:离desc名义界过远不收
                frags.append((bl, str(t).strip()))
            frags.sort()
            ev[f"行{r}"] = {"strip": " ".join(t for _, t in frags if t)}
        PARTS.mkdir(parents=True, exist_ok=True)
        (PARTS / f"{stem}.json").write_text(
            json.dumps(ev, ensure_ascii=False), encoding="utf-8")
        return stem, True, f"行带读{len(ev)}行 {round(time.time() - t0, 1)}s"
    except Exception as e:  # noqa: BLE001
        return stem, False, f"{type(e).__name__}: {e}"


def main(argv=None):
    per = target_rows()
    have = {p.stem for p in PARTS.glob("*.json")} if PARTS.exists() else set()
    items = [(s[5:], rs) for s, rs in sorted(per.items())
             if s[5:] not in have]          # 定级账键=全称,worker 吃数字图号
    n_cells = sum(len(rs) for _, rs in items)
    print(f"行带读目标 {n_cells} 行 / {len(items)} 图(已分片 {len(have)} 图跳过)")
    if not items:
        _merge()
        return
    from src.core import batch
    results = batch.run_batch(items, worker, max_workers=3)
    failed = [it for it, (_s, ok, _i) in zip(items, results) if not ok]
    if failed:
        retry = dict((s, (s, ok, info)) for s, ok, info in
                     batch.run_batch(failed, worker, max_workers=1))
        results = [retry.get(s, res) for s, res in
                   zip([it[0] for it in items], results)]
    _merge()
    for stem, ok, info in results:
        if not ok:
            print(f"  {stem} FAIL {info}")


def _merge():
    out = json.loads(OUT.read_text(encoding="utf-8")) if OUT.exists() else {}
    for pp in sorted(PARTS.glob("*.json")):
        out[f"钻孔柱状图{pp.stem}"] = json.loads(pp.read_text(encoding="utf-8"))
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1),
                   encoding="utf-8")
    print(f"合并 → {OUT.name}, {sum(len(v) for v in out.values())} 行")


if __name__ == "__main__":
    main(sys.argv[1:])
