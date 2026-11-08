# -*- coding: utf-8 -*-
"""4 张补产图的 Agnes 第二引擎逐层转写 + 与 RapidOCR 草案对账。

行/列几何完全复用 rebuild4_excel 的边界方案(用户核验定稿+宽度指纹)与行判定,
只做内容层第二引擎:逐层全表宽裁条(画红色列界线)→ agnes-2.5-flash 逐列转写
→ 与草案 RapidOCR 读数对账;分歧格再单格重读一次;数字关系式(真厚=层厚×cos倾角,
层厚=相邻深度差)可裁定时按关系式裁定,否则保留 RapidOCR 读数并列待核清单。
API key 只从环境变量 AGNES_API_KEY 读取(缺省时从 runs/agnes_api_key.env 载入进程内),
不写入本文件与任何输出。

用法:
  python src/tools/agnes4_verify.py pilot 1018 0    # 单层试转写,存裁片图+打印
  python src/tools/agnes4_verify.py run             # 4 张全量逐层(断点续跑)
  python src/tools/agnes4_verify.py reconcile       # 对账 → 最终 xlsx + 待核清单
"""
from __future__ import annotations

import base64
import json
import math
import os
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import cv2
import requests

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.core import paths  # noqa: E402
from src.tools.rebuild4_excel import (  # noqa: E402
    NUM_RE, STEMS4, _chain_x, load_chart,
)

API_BASE = "https://apihub.agnes-ai.com/v1"
MODEL = "agnes-2.5-flash"
MAX_TOKENS = 16384     # agnes 含长 reasoning;4096 曾出现 content 为空
WORKERS = int(os.environ.get("AGNES_WORKERS", "4"))
REL_TOL = 0.02         # 真厚互证容差(判定6 实测:已核验集 87% ≤0.02m)

TOL_SIGN = "±0.02m"


def _ensure_key():
    if not os.environ.get("AGNES_API_KEY"):
        envf = PROJECT_ROOT / "runs" / "agnes_api_key.env"
        if envf.exists():
            for line in envf.read_text(encoding="utf-8").splitlines():
                if line.startswith("AGNES_API_KEY="):
                    os.environ["AGNES_API_KEY"] = line.split("=", 1)[1].strip()
                    break
    if not os.environ.get("AGNES_API_KEY"):
        raise RuntimeError("AGNES_API_KEY 未设置")


def ask_agnes(jpeg_bytes, prompt, timeout=150):
    key = os.environ["AGNES_API_KEY"]
    b64 = base64.b64encode(jpeg_bytes).decode("ascii")
    payload = {
        "model": MODEL, "temperature": 0, "max_tokens": MAX_TOKENS,
        "messages": [{"role": "user", "content": [
            {"type": "text", "text": prompt},
            {"type": "image_url",
             "image_url": {"url": f"data:image/jpeg;base64,{b64}"}},
        ]}],
    }
    t0 = time.perf_counter()
    try:
        resp = requests.post(
            f"{API_BASE}/chat/completions", json=payload,
            headers={"Authorization": f"Bearer {key}",
                     "Content-Type": "application/json"}, timeout=timeout)
    except Exception as e:  # noqa: BLE001
        return None, {"ok": False, "error": f"exc:{type(e).__name__}"}
    info = {"latency_s": round(time.perf_counter() - t0, 1),
            "status": resp.status_code}
    if resp.status_code != 200:
        info["ok"] = False
        info["error"] = f"http_{resp.status_code}"
        return None, info
    try:
        content = resp.json()["choices"][0]["message"]["content"] or ""
    except Exception:
        info.update(ok=False, error="bad_payload")
        return None, info
    info["ok"] = True
    return content, info


def parse_json_obj(content):
    if not content:
        return None
    m = re.search(r"\{[^{}]*\}", content, re.S)
    if not m:
        return None
    try:
        obj = json.loads(m.group(0))
        return obj if isinstance(obj, dict) else None
    except json.JSONDecodeError:
        return None


def build_prompt(names):
    return (
        "这是地质钻孔柱状图数据表格中的一行(一个层),已按列边界裁出,红色竖线是列界。"
        f"列从左到右依次为:{'、'.join(names)}。\n"
        "请逐列转写格内全部手写/印刷内容,规则:\n"
        "1) 数字逐字符照抄,保留小数点;一格内有多个读数时用一个空格分隔。\n"
        "2) 无文字的格(柱状图案/曲线/空白)输出空字符串。\n"
        "3) 不要推测、不要修正疑似错字,照实转写。\n"
        '只输出严格 JSON,键为上述列名,例如 {"深度":"12.34","层厚":"2.10"}'
    )


def chart_geometry(n):
    """行界、列界链、裁条外沿——pilot/run/reconcile 共用。"""
    stem, jd, st, hm_old, seg_all, gray, bs, cols = load_chart(n)
    rd = json.loads((paths.RUNS_DIR / "table_reconstruct" / f"{stem}_行判定.json")
                    .read_text(encoding="utf-8"))
    band = hm_old["band"]
    rows_y = [r["y_at_mid"] for r in rd["rows"] if r["y_at_mid"] >= band[1]]
    keep = [c for c in cols if c["keep"]]
    return {"stem": stem, "gray": gray, "bs": bs, "seg_all": seg_all,
            "rows_y": rows_y, "keep": keep}


def strip_of(g, li, draw_sep=True):
    """第 li 层全表宽裁条(BGR,画红列界);返回 (img, [各keep列界x(裁片系)])。"""
    y_top, y_bot = g["rows_y"][li], g["rows_y"][li + 1]
    y_mid = (y_top + y_bot) / 2
    xs = []
    for b in g["bs"]:
        x = _chain_x(g["seg_all"], b["ids"], y_mid)
        xs.append(x if x is not None else b["x"])
    x_lo, x_hi = min(xs), max(xs)
    crop = g["gray"][int(y_top) + 4:int(y_bot) - 3, int(x_lo) + 3:int(x_hi) - 3]
    vis = cv2.cvtColor(crop, cv2.COLOR_GRAY2BGR)
    marks = []
    if draw_sep:
        for b in g["bs"]:
            x = _chain_x(g["seg_all"], b["ids"], y_mid)
            x = x if x is not None else b["x"]
            xi = int(round(x - x_lo - 3))
            if 2 <= xi < vis.shape[1] - 2:
                cv2.line(vis, (xi, 0), (xi, vis.shape[0] - 1), (0, 0, 255), 2)
    keep_x = [_chain_x(g["seg_all"], g["bs"][c["li"]]["ids"], y_mid) or g["bs"][c["li"]]["x"]
              for c in g["keep"]]
    keep_x = [x - x_lo - 3 for x in keep_x]
    return vis, keep_x


def read_layer(g, li):
    """单层 → Agnes 逐列读数 dict(缺列补 ""),附 info。"""
    vis, _ = strip_of(g, li)
    ok, buf = cv2.imencode(".jpg", vis, [int(cv2.IMWRITE_JPEG_QUALITY), 88])
    names = [c["name"] for c in g["keep"]]
    content, info = ask_agnes(buf.tobytes(), build_prompt(names))
    obj = parse_json_obj(content)
    readings = {n: str(obj.get(n, "")).strip() if obj else None for n in names}
    if obj is None:
        readings = None
    return readings, info, content


def cmd_pilot(n, li):
    _ensure_key()
    g = chart_geometry(n)
    vis, _ = strip_of(g, li)
    png = paths.RUNS_DIR / "table_reconstruct" / f"pilot_{n}_layer{li}.png"
    cv2.imwrite(str(png), vis)
    t0 = time.perf_counter()
    readings, info, raw = read_layer(g, li)
    print(f"{g['stem']} 层{li} y[{g['rows_y'][li]:.0f},{g['rows_y'][li+1]:.0f}] "
          f"→ {png.name}")
    print(f"info={info} 总耗时 {time.perf_counter()-t0:.0f}s")
    print("读数:", json.dumps(readings, ensure_ascii=False))
    print("--- raw 前600字 ---")
    print((raw or "")[:600])


def _run_chart(n):
    g = chart_geometry(n)
    out = paths.RUNS_DIR / "table_reconstruct" / f"{g['stem']}_agnes读数.json"
    nl = len(g["rows_y"]) - 1
    data = {"stem": g["stem"], "model": MODEL,
            "columns": [c["name"] for c in g["keep"]],
            "layers": [None] * nl}
    if out.exists():
        old = json.loads(out.read_text(encoding="utf-8"))
        if old.get("layers") and len(old["layers"]) == nl:
            data["layers"] = old["layers"]
    todo = [i for i, v in enumerate(data["layers"])
            if not (v and v.get("readings"))]
    print(f"{g['stem']}: {nl} 层,待转写 {len(todo)}", flush=True)
    lock_hist = []

    def work(i):
        info = {}
        for attempt in range(5):
            readings, info, _ = read_layer(g, i)
            if readings is not None:
                return i, readings, info
            wait = 25 if info.get("error") == "http_429" else 3 * (attempt + 1)
            time.sleep(wait)
        return i, None, info

    with ThreadPoolExecutor(max_workers=WORKERS) as ex:
        futs = {ex.submit(work, i): i for i in todo}
        for fu in as_completed(futs):
            i, readings, info = fu.result()
            data["layers"][i] = {"readings": readings, "info": info}
            lock_hist.append(info.get("latency_s") or 0)
            done = len(lock_hist)
            if done % 10 == 0 or done == len(todo):
                out.write_text(json.dumps(data, ensure_ascii=False, indent=1),
                               encoding="utf-8")
                print(f"  {g['stem']} {done}/{len(todo)} "
                      f"latency均值 {sum(lock_hist)/len(lock_hist):.0f}s", flush=True)
    out.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    bad = sum(1 for v in data["layers"] if not v)
    print(f"{g['stem']}: 完成,失败层 {bad} → {out.name}", flush=True)


def cmd_run():
    _ensure_key()
    for stem in STEMS4:
        _run_chart(int(stem[-4:]))


# ---------------- 对账 ----------------

def _norm(s):
    if s is None:
        return ""
    s = str(s)
    tbl = str.maketrans("０１２３４５６７８９．，", "0123456789.,")
    return s.translate(tbl).replace(" ", "").strip()


_PUNCT_RE = re.compile(r"[^\w\u4e00-\u9fff]+", re.S)


def _strip_punct(s):
    return _PUNCT_RE.sub("", str(s))


def _tokens(s):
    return [t for t in re.split(r"\s+", str(s).strip()) if t]


def _has_digit(s):
    return any(c.isdigit() for c in str(s))


def _tok_eq(x, y):
    a, b = _as_num(x), _as_num(y)
    if a is not None and b is not None:
        return abs(a - b) < 1e-9
    return _strip_punct(x) == _strip_punct(y)


def _agree(rapid, agnes):
    """数字格(含多读数)逐 token 数值比较;纯文本格去标点全等。
    小数点在数字比较中永不忽略(10.40 vs 1040 必须算分歧)。"""
    a = str(rapid if rapid is not None else "").strip()
    b = str(agnes if agnes is not None else "").strip()
    if not a and not b:
        return True
    ta, tb = _tokens(a), _tokens(b)
    if ta and tb and len(ta) == len(tb) and all(_tok_eq(x, y) for x, y in zip(ta, tb)):
        return True
    if not _has_digit(a) and not _has_digit(b):
        return bool(_strip_punct(a)) and _strip_punct(a) == _strip_punct(b)
    return False


def _as_num(s):
    t = re.sub(r"[°。％%]", "", _norm(str(s)))
    try:
        return float(t)
    except (TypeError, ValueError):
        return None


def _thickness_ok(t, ang, th):
    a, b, c = _as_num(t), _as_num(ang), _as_num(th)
    if None in (a, b, c) or abs(b) > 89:
        return None
    return abs(c * math.cos(math.radians(b)) - a) <= REL_TOL


def _depth_ok(rows_num, i, d_val):
    """层厚_i = d_i - d_{i-1}(已核验集行内吻合 90.8%);i=0 无判据返 None。"""
    d = _as_num(d_val)
    if d is None or i < 1:
        return None if d is None else False
    d_prev = _as_num(rows_num[i - 1].get("深度"))
    t = _as_num(rows_num[i].get("层厚"))
    if d_prev is None or t is None:
        return None
    return abs(d - d_prev - t) <= REL_TOL


def read_cell(g, li, name):
    """分歧格单格重读: tight crop,只读一格。"""
    y_top, y_bot = g["rows_y"][li], g["rows_y"][li + 1]
    y_mid = (y_top + y_bot) / 2
    c = next(c for c in g["keep"] if c["name"] == name)
    x0 = _chain_x(g["seg_all"], g["bs"][c["li"]]["ids"], y_mid) or c["x0"]
    x1 = _chain_x(g["seg_all"], g["bs"][c["ri"]]["ids"], y_mid) or c["x1"]
    gray = g["gray"]
    crop = gray[int(y_top) + 4:int(y_bot) - 3, int(min(x0, x1)) + 3:int(max(x0, x1)) - 3]
    if crop.size == 0 or crop.shape[0] < 8 or crop.shape[1] < 8:
        return ""          # 几何退化(边界链中点重合等):视作空格读数
    ok, buf = cv2.imencode(".jpg", crop, [int(cv2.IMWRITE_JPEG_QUALITY), 92])
    prompt = (f"这是表格中一个单元格,列名[{name}]。转写格内全部手写/印刷内容;"
              "数字逐字符照抄保留小数点,多个读数用空格分隔,空白格输出空字符串,"
              "不要推测。只输出严格 JSON: {\"值\":\"...\"}")
    info = {}
    for k in range(4):
        content, info = ask_agnes(buf.tobytes(), prompt)
        obj = parse_json_obj(content)
        if obj is not None and "值" in obj:
            return str(obj["值"]).strip()
        time.sleep(40 if info.get("error") == "http_429" else 2 * (k + 1))
    return None


def cmd_reconcile():
    _ensure_key()
    from openpyxl import Workbook, load_workbook
    summary = {}
    for stem in STEMS4:
        n = int(stem[-4:])
        g = chart_geometry(n)
        aj = json.loads((paths.RUNS_DIR / "table_reconstruct" / f"{stem}_agnes读数.json")
                        .read_text(encoding="utf-8"))
        draft = paths.RUNS_DIR / "table_reconstruct" / f"{stem}_还原_补产草案.xlsx"
        wb = load_workbook(draft)
        ws = wb.active
        rows = list(ws.iter_rows(values_only=True))
        header, table = list(rows[0]), [list(r) for r in rows[1:]]
        names = header
        flags = []
        n_agree = n_cell = 0
        disputes = []          # (li, j, name, rapid, agr)
        for li, row in enumerate(table):
            ag = (aj["layers"][li] or {}).get("readings") if li < len(aj["layers"]) else None
            if ag is None:
                flags.append({"层": li + 1, "列": "-", "草案": "(Agnes层失败)",
                              "agnes": None, "处置": "待人审"})
                continue
            for j, name in enumerate(names):
                n_cell += 1
                rapid = row[j]
                agr = ag.get(name, "")
                if _agree(rapid, agr):
                    n_agree += 1
                else:
                    disputes.append((li, j, name, rapid, agr))
        # 并行单格重读(增量存盘,断点续)
        rj = paths.RUNS_DIR / "table_reconstruct" / f"{stem}_单格重读.json"
        reads = {}
        if rj.exists():
            reads = json.loads(rj.read_text(encoding="utf-8"))
        todo = [(li, j) for li, j, *_ in disputes
                if reads.get(f"{li}:{j}") is None]
        print(f"{stem}: 格 {n_cell} 一致 {n_agree} 分歧 {len(disputes)} "
              f"重读 {len(todo)}", flush=True)
        with ThreadPoolExecutor(max_workers=WORKERS) as ex:
            futs = {}
            for li, j, nm, *_ in disputes:
                key = f"{li}:{j}"
                if reads.get(key) is not None:
                    continue
                futs[ex.submit(read_cell, g, li, nm)] = key
            done_n = 0
            for fu in as_completed(futs):
                key = futs[fu]
                reads[key] = fu.result()
                done_n += 1
                if done_n % 20 == 0 or done_n == len(futs):
                    rj.write_text(json.dumps(reads, ensure_ascii=False),
                                  encoding="utf-8")
                    print(f"  {stem} 重读 {done_n}/{len(futs)}", flush=True)
        rj.write_text(json.dumps(reads, ensure_ascii=False), encoding="utf-8")
        # 裁定
        rows_num = [dict(zip(names, r)) for r in table]
        for li, j, name, rapid, agr in disputes:
            cell_read = reads.get(f"{li}:{j}")
            # 单格重读失败/空读时,条带读数作为第二 Agnes 读数候选参与裁定
            cand3 = cell_read if cell_read else (agr or None)
            if cell_read and _agree(rapid, cell_read):
                n_agree += 1
                continue
            pick, how = None, None
            if name == "真厚" and cand3 is not None:
                ok_r = _thickness_ok(table[li][names.index("层厚")],
                                     table[li][names.index("倾角")], rapid)
                ok_a = _thickness_ok(table[li][names.index("层厚")],
                                     table[li][names.index("倾角")], cand3)
                if ok_r and not ok_a:
                    pick, how = rapid, "关系式裁定留草案"
                elif ok_a and not ok_r:
                    pick, how = cand3, "关系式裁定改Agnes"
            if name == "深度" and cand3 is not None:
                ok_r = _depth_ok(rows_num, li, rapid)
                ok_a = _depth_ok(rows_num, li, cand3)
                if ok_r and not ok_a:
                    pick, how = rapid, "深度差裁定留草案"
                elif ok_a and not ok_r:
                    pick, how = cand3, "深度差裁定改Agnes"
            if pick is None and cell_read is not None \
                    and _agree(agr, cell_read) and _norm(agr):
                pick, how = cell_read, "Agnes双读一致采纳"
            if pick is None:
                pick = rapid
                how = "待人审"
            if isinstance(pick, str) and NUM_RE.match(pick.strip()):
                pick = float(pick)
            table[li][j] = pick
            flags.append({"层": li + 1, "列": name,
                          "草案": str(rapid), "agnes单格": str(cell_read),
                          "agnes条": str(agr), "处置": how})
        out = paths.RUNS_DIR / "table_reconstruct" / f"{stem}_还原_补产终版.xlsx"
        wb2 = Workbook()
        ws2 = wb2.active
        ws2.title = stem.replace("钻孔柱状图", "")
        ws2.append(names)
        for row in table:
            ws2.append(row)
        wb2.save(out)
        import src.tools.rebuild4_excel as r4
        qc = r4.relation_qc(names, table)
        summary[stem] = {"格": n_cell, "一致": n_agree,
                         "一致率": round(n_agree / max(n_cell, 1), 3),
                         "分歧": len(flags), "QC": qc, "待核": len(
                             [f for f in flags if f["处置"] == "待人审"])}
        fp = paths.RUNS_DIR / "table_reconstruct" / f"{stem}_待核清单.json"
        fp.write_text(json.dumps(flags, ensure_ascii=False, indent=1),
                      encoding="utf-8")
        print(f"{stem}: 格 {n_cell} 一致 {n_agree} ({summary[stem]['一致率']:.1%}) "
              f"分歧 {len(flags)} 待人审 {summary[stem]['待核']} → {out.name}")
        print(f"   QC {qc}")
    (paths.RUNS_DIR / "table_reconstruct" / "对账汇总.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=1), encoding="utf-8")


def cmd_review():
    """待人审格导出复核包:裁片 PNG + 点选式复核页(三候选按钮+实时回写JSON)。"""
    import html as _html
    for stem in STEMS4:
        flags = json.loads((paths.RUNS_DIR / "table_reconstruct" / f"{stem}_待核清单.json")
                           .read_text(encoding="utf-8"))
        flags = [f for f in flags if f["处置"] == "待人审" and f.get("列")]
        if not flags:
            print(f"{stem}: 无待人审格")
            continue
        n = int(stem[-4:])
        g = chart_geometry(n)
        outd = paths.RUNS_DIR / "table_reconstruct" / f"{stem}_待核复核包"
        outd.mkdir(exist_ok=True)
        code = stem[-4:]
        rows = []
        for f in flags:
            li = f["层"] - 1
            name = f["列"]
            key = f"{f['层']}:{name}"
            y_top, y_bot = g["rows_y"][li], g["rows_y"][li + 1]
            y_mid = (y_top + y_bot) / 2
            c = next(c for c in g["keep"] if c["name"] == name)
            x0 = _chain_x(g["seg_all"], g["bs"][c["li"]]["ids"], y_mid) or c["x0"]
            x1 = _chain_x(g["seg_all"], g["bs"][c["ri"]]["ids"], y_mid) or c["x1"]
            crop = g["gray"][int(y_top) + 2:int(y_bot) - 1,
                             int(min(x0, x1)) + 1:int(max(x0, x1)) - 1]
            png = f"{stem}_L{li+1}_{name}.png"
            if crop.size == 0 or crop.shape[0] < 4 or crop.shape[1] < 4:
                img_html = "(无裁片:格几何退化)"
            else:
                cv2.imwrite(str(outd / png), crop)
                img_html = f'<img src="{png}" style="height:72px">'
            cands = []
            for label, v in (("草案", f.get("草案")), ("单格", f.get("agnes单格")),
                             ("条带", f.get("agnes条"))):
                vv = "" if v in (None, "-", "None") else str(v)
                show = vv if vv else "(空)"
                cands.append(f'<button class="pick" data-key="{key}" '
                             f'data-val="{_html.escape(vv, quote=True)}" '
                             f'onclick="pick(this)">{label}: {_html.escape(show)}</button>')
            rows.append(
                f'<tr id="r_{_html.escape(key, quote=True)}">'
                f'<td>{f["层"]}</td><td>{_html.escape(name)}</td>'
                f'<td>{"".join(cands)}</td>'
                f'<td><input class="free" placeholder="或自填" '
                f'oninput="freev(this,\'{_html.escape(key, quote=True)}\')"></td>'
                f'<td class="st" id="st_{_html.escape(key, quote=True)}"></td>'
                f'<td>{img_html}</td></tr>')
        page = (
            "<!doctype html><meta charset='utf-8'><title>" + stem + " 待核格</title>"
            "<style>td,th{border:1px solid #999;padding:4px;font-size:13px}"
            "table{border-collapse:collapse}tr:has(.st:not(:empty)){background:#dfd}"
            "#bar{position:sticky;bottom:0;background:#ffe;padding:8px}</style>"
            "<h3>" + stem + f" 待人审 {len(flags)} 格"
            "（点候选即择定;也可自填;未点的行=确认草案读数）</h3>"
            "<table><tr><th>层</th><th>列</th><th>三候选(点选)</th>"
            "<th>自填</th><th>已选</th><th>裁片</th></tr>" + "\n".join(rows) + "</table>"
            "<div id='bar'>已择定 <b id='cnt'>0</b>/" + str(len(flags)) +
            " 格(其余视为确认草案) "
            "<button onclick='copyjson()'>复制回写JSON</button>"
            "<textarea id='out' rows='3' cols='60' readonly></textarea></div>"
            "<script>var CODE='" + code + "';var picks={};"
            "function pick(b){picks[b.dataset.key]=b.dataset.val;"
            "document.getElementById('st_'+b.dataset.key).textContent='✓ '+b.dataset.val;"
            "upd();}"
            "function freev(i,k){if(i.value.trim()){picks[k]=i.value.trim();"
            "document.getElementById('st_'+k).textContent='✎ '+i.value.trim();}upd();}"
            "function upd(){document.getElementById('cnt').textContent="
            "Object.keys(picks).length;"
            "document.getElementById('out').value="
            "JSON.stringify(obj(),null,1);}"
            "function obj(){var o={};o[CODE]=picks;"
            "return o;}"
            "function copyjson(){var t=document.getElementById('out');t.select();"
            "document.execCommand('copy');}</script>")
        (outd / "待核清单.html").write_text(page, encoding="utf-8")
        print(f"{stem}: 待人审 {len(flags)} 格(点选版) → {outd}")


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    if cmd == "pilot":
        cmd_pilot(int(sys.argv[2]), int(sys.argv[3]))
    elif cmd == "run":
        cmd_run()
    elif cmd == "reconcile":
        cmd_reconcile()
    elif cmd == "review":
        cmd_review()
    else:
        print(__doc__)


if __name__ == "__main__":
    main()
