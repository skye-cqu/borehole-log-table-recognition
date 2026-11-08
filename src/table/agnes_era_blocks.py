# -*- coding: utf-8 -*-
"""时代带整块裁剪 + Agnes 全列复读(用户 2026-10-28 拍板,替代逐格像素取证路线)。

背景:RapidOCR 逐格识读精度不足(乱码/串行/小数点丢失),用户指令:按地质时代
把对应整块裁下传 Agnes——多行带单独成块,单行带按高度贪心拼到接近 1:1;横纵比
按带定,清晰度维持原始像素不缩放(PNG 无损,超 6MB 退 JPEG q95,均不 resize)。

裁块几何复刻 finalize() 前段(行手术/分组逐句同源),块↔数据行映射入账,
compare 子命令按账对回整合 xlsx 逐格比对出账,供裁决与应用。

子命令:
  crop   [图号...]  裁块 + 块账(无参数=全量)
  read   [图号...]  逐块送 Agnes,存 答.json(幂等:已答跳过;--force 重答)
  compare [图号...] 与整合 xlsx 逐格比对 → 比对.json + 比对汇总.json
  decide [图号...]  差异裁决(链算术/词表/编辑距) → 裁决.json(应用条目交 finalize 块2.7)
"""
import json
import re
import sys
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import cv2
import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.core import paths, batch  # noqa: E402
from src.table.finalize_tables import (  # noqa: E402
    column_roles, drop_header_rows, fill_missing_qualifier, join_split_bands,
    rows_to_era_groups, unstuck_chain)
from src.table.era_chars import _load_inputs  # noqa: E402
from src.table.track_rows import row_y  # noqa: E402

OUT = paths.AGNES_REREAD_DIR_20261028
PAD_Y = 5            # 块上下在行界折线自身 y 范围外再让的像素
PAD_X = 12           # 左右含外框线
MANUF_PAD = 30       # 拆行内部界(无折线)上下让宽些,防切邻行字
MAX_IMG_BYTES = 6_000_000   # PNG 超此值退 JPEG q95(API 请求体保险)
MAX_H_FRAC = 1.4     # 块高上限=宽×此值(防 API 内部强缩)
ROLE_CN = {"era": "地质时代", "layer": "煤层/标志层号", "depth": "深度(终深)",
           "thick": "层厚", "length": "采长", "dip": "倾角", "true_thick": "真厚",
           "desc": "岩性描述"}


def chart_rows(stem):
    """复刻 finalize() 几何段(只读,不改任何产物)。

    返回 {data, ys, bmap, roles, groups, rows_r, hm, rd, bands, header}:
    bmap[i]=数据行 i 顶界在 rows_r 的下标(拆行内部界=None);groups=[(带号,[行号...])]。
    """
    from openpyxl import load_workbook
    hm, rd = _load_inputs(stem)
    x_mid_tbl = sum(rd["table_x"]) / 2
    rows_r = [r for r in rd["rows"] if row_y(r, x_mid_tbl) >= hm["band"][1]]
    ep = paths.ERA_CHAR_DIR / stem / "era_chars.json"
    bands = [dict(b) for b in json.loads(ep.read_text(encoding="utf-8"))["bands"]] \
        if ep.exists() else []
    bands, _ = join_split_bands(bands)
    bands, _ = fill_missing_qualifier(bands)
    wb = load_workbook(paths.REEMIT_DIR_20261023 / f"{stem}_还原.xlsx")
    ws = wb.active
    data = list(ws.iter_rows(values_only=True))
    n_data = len(data) - 1
    roles = column_roles(data[0] if data else [])
    x_era = sum(hm["keep"][0]["x_in_band"]) / 2
    ys = [row_y(r, x_era) for r in rows_r]
    if n_data != len(ys) - 1:
        raise ValueError(f"{stem} 行数不一致 xlsx={n_data} 行判定={len(ys) - 1}")
    data, ys, dropped_x = drop_header_rows(data, ys)
    data = [list(r) if r is not None else [] for r in data]
    bmap = [i for i in range(len(ys) + len(dropped_x)) if i not in {x - 2 for x in dropped_x}]
    data, ys, stuck_ops, _led = unstuck_chain(data, ys, roles)
    for op in sorted(stuck_ops, key=lambda o: (o[1], 0 if o[0] == "over" else 1), reverse=True):
        kind, xr, vals = op
        if kind == "split":
            new_rows = vals if isinstance(vals[0], (list, tuple)) else [vals]
            bmap[xr - 1:xr - 1] = [None] * len(new_rows)  # 拆行次行列表,各行顶界=内部界
        elif kind == "drop":
            del bmap[xr - 1]
    n_data = len(data) - 1
    if len(bmap) != n_data + 1:
        raise ValueError(f"{stem} bmap 失配 {len(bmap)} vs {n_data + 1}")
    y_mids = [(ys[i] + ys[i + 1]) / 2 for i in range(n_data)]
    groups = rows_to_era_groups(y_mids, bands)
    return {"data": data, "ys": ys, "bmap": bmap, "roles": roles, "groups": groups,
            "rows_r": rows_r, "hm": hm, "rd": rd, "bands": bands,
            "header": list(data[0] if data else [])}


def _bound_span(g, bi):
    """边界 bi 的 (y_min, y_max):有折线=折线自身范围,拆行内部界=x_era 处标量。"""
    if bi is not None:
        poly = g["rows_r"][bi].get("poly") or []
        if len(poly) >= 2:
            ys_ = [p[1] for p in poly]
            return min(ys_), max(ys_)
    y = g["ys"][bi if bi is not None else 0]
    return y, y


def build_blocks(g):
    """行 → 块列表:组界优先收块,块高目标=表宽(≈1:1),上限=宽×1.4;
    单带超限才在带内行界处再分。返回 [(首行,末行,带号或None)]。"""
    n = len(g["ys"]) - 1
    gid = [None] * n
    for k, rows in g["groups"]:
        for i in rows:
            gid[i] = k
    width = g["rd"]["table_x"][1] - g["rd"]["table_x"][0]
    target, maxh = width * 1.0, width * MAX_H_FRAC

    def span(a, b):
        y0, _ = _bound_span(g, g["bmap"][a])
        _, y1 = _bound_span(g, g["bmap"][b + 1])
        return y1 - y0

    blocks, a = [], 0
    while a < n:
        b, h = a, span(a, a)
        while b + 1 < n:
            nh = span(a, b + 1)
            boundary = gid[b + 1] != gid[b]
            if h >= target and boundary:
                break                       # 达标且组界→收块
            if nh > maxh and (boundary or h >= target):
                break                       # 超限:组界处收;带内须达标才可断
            b += 1
            h = nh
        blocks.append([a, b, gid[a]])
        a = b + 1
    # 尾块过薄(<0.35×宽)会成 20:1 长条,向前并块(不超高即并,跨组也并——比例优先)
    thin = width * 0.35
    while len(blocks) >= 2:
        a0, b0, k0 = blocks[-1]
        if span(a0, b0) >= thin:
            break
        pa, pb, pk = blocks[-2]
        if span(pa, b0) > maxh * 1.06:      # 允许略超:细长条比 6% 超高更伤识读
            break
        blocks[-2:] = [[pa, b0, pk]]
    return [tuple(x) for x in blocks]


def _mask_spans(g):
    """要遮蔽的竖条(用户 2026-10-28:柱状/简易水文两列无用,遮住防干扰识读):
    1) 相邻 keep 列不共享分隔线=其间是被丢弃的列(柱状等),遮 sep右..sep左;
    2) 末个 keep 列右界到右框=水文曲线区,遮到裁片右缘(顺带盖掉页边注记)。"""
    keep = g["hm"]["keep"]
    spans = []
    for j in range(len(keep) - 1):
        ls, rs = keep[j].get("right_sep"), keep[j + 1].get("left_sep")
        if ls is not None and rs is not None and ls != rs:
            spans.append((ls, rs))
    last = keep[-1].get("right_sep")
    if last is not None:
        spans.append((last, None))          # None=遮到右缘
    return spans


def _apply_masks(gray, g, spans, y0, y1, xr_edge):
    sep = g["hm"]["sep_pts"]
    tx1 = float(g["rd"]["table_x"][1])
    for i in range(y0, y1):
        for a, b in spans:
            xa = float(np.interp(i, sep[a]["ys"], sep[a]["xs"]))
            xb = tx1 + PAD_X if b is None else float(np.interp(i, sep[b]["ys"], sep[b]["xs"]))
            if xb > xa:
                gray[i, int(xa):int(xb) + 1] = 255


def crop_one(stem):
    """单图裁块,写 OUT/stem/块XX.png|jpg + 块账.json。返回 (stem, ok, info)。"""
    outd = OUT / stem
    outd.mkdir(parents=True, exist_ok=True)
    g = chart_rows(stem)
    gray = cv2.imread(str(paths.RAW_DIR / f"{stem}.JPG"), cv2.IMREAD_GRAYSCALE)
    xl, xr = g["rd"]["table_x"]
    x0, x1 = max(0, int(xl) - PAD_X), min(gray.shape[1], int(xr) + PAD_X)
    spans = _mask_spans(g)
    blocks, acc = [], []
    for k, (a, b, bk) in enumerate(build_blocks(g)):
        ty0, _ = _bound_span(g, g["bmap"][a])
        _, ty1 = _bound_span(g, g["bmap"][b + 1])
        pad_top = PAD_Y if g["bmap"][a] is not None else MANUF_PAD
        pad_bot = PAD_Y if g["bmap"][b + 1] is not None else MANUF_PAD
        y0 = max(0, int(ty0) - pad_top)
        y1 = min(gray.shape[0], int(ty1) + pad_bot + 1)
        _apply_masks(gray, g, spans, y0, y1, x1)
        crop = gray[y0:y1, x0:x1]
        ok, png = cv2.imencode(".png", crop)
        mime, blob, fname = "image/png", png.tobytes(), f"块{k:02d}.png"
        if len(blob) > MAX_IMG_BYTES:
            ok, enc = cv2.imencode(".jpg", crop, [cv2.IMWRITE_JPEG_QUALITY, 95])
            mime, blob, fname = "image/jpeg", enc.tobytes(), f"块{k:02d}.jpg"
        (outd / fname).write_bytes(blob)
        era = g["bands"][bk]["name"] if bk is not None and bk < len(g["bands"]) else None
        blocks.append({"k": k, "file": fname, "行": [a, b], "带": bk, "era": era,
                       "y": [y0, y1], "x": [x0, x1], "mime": mime,
                       "wh": [int(x1 - x0), int(y1 - y0)], "bytes": len(blob)})
        acc.append((a, b))
    rows_used = [i for ab in acc for i in range(ab[0], ab[1] + 1)]
    assert rows_used == list(range(len(g["ys"]) - 1)), f"{stem} 块未覆盖全部行"
    账 = {"stem": stem, "table_x": [int(xl), int(xr)],
          "header": [str(h) if h is not None else "" for h in g["header"]],
          "roles": g["roles"], "n_data": len(g["ys"]) - 1, "blocks": blocks}
    (outd / "块账.json").write_text(json.dumps(账, ensure_ascii=False, indent=1),
                                    encoding="utf-8")
    ratios = [f"{bb['wh'][0]}x{bb['wh'][1]}({bb['wh'][0] / bb['wh'][1]:.1f}:1)" for bb in blocks]
    return stem, True, f"{len(blocks)} 块 " + " ".join(ratios)


def _prompt(账, blk):
    roles = 账["roles"]
    keys = [r for r in ("era", "layer", "depth", "thick", "length", "dip",
                        "true_thick", "desc") if r in roles]
    names = " | ".join(f"{ROLE_CN[r]}({r})" for r in keys)
    fields = ", ".join('"%s": 文字或""' % k for k in keys)
    nrows = blk["行"][1] - blk["行"][0] + 1
    # 2026-10-29 三读修订:不再预填时代名(实证 Agnes 会回声提示词而非读图,era一致率仅56.6%)
    return f"""你是地质钻孔柱状图识读员。图中是同一张表格的连续 {nrows} 个数据行(自上而下)。
表头自左至右为:{names}。图中竖向白条是已屏蔽的非识读区,忽略。
任务:逐行逐格识读,输出严格 JSON(禁止 markdown 代码块):
{{"rows": [{{"r": 行序号从1, {fields}}}]}}
要求:
- 只抄图中真实存在的文字;空格填 "";数字/小数点/°符号原样保留。
- 深度列逐格原样抄写(含小数位),它是行对齐依据;不得跳行、重复行或合并行。
- 层号可能是阿拉伯数字、汉字数字(如 三下、四中)或组名(如 茅口组)。
- 岩性描述逐字完整抄写,不要概括不要遗漏。
- 表格线歪斜属扫描变形,按行对齐识读。"""


def read_one(stem, force=False):
    """单图逐块送 Agnes,存 OUT/stem/块XX.答.json。返回 (stem, ok, info)。"""
    from src.table.agnes_post import ask
    outd = OUT / stem
    账 = json.loads((outd / "块账.json").read_text(encoding="utf-8"))
    done = skip = fail = 0
    for blk in 账["blocks"]:
        ansf = outd / f"{Path(blk['file']).stem}.答.json"
        if ansf.exists() and not force:
            try:
                if not json.loads(ansf.read_text(encoding="utf-8")).get("error"):
                    skip += 1
                    continue          # 已答且无错才跳过;error 档重试
            except Exception:  # noqa: BLE001
                pass
        img_path = outd / blk["file"]
        blob = img_path.read_bytes()
        try:
            raw = ask(_prompt(账, blk), image_jpeg=blob, max_tokens=16000,
                      timeout=300, mime=blk["mime"])
        except Exception as e:  # noqa: BLE001
            fail += 1
            ansf.write_text(json.dumps({"k": blk["k"], "error": repr(e)[:200]},
                                       ensure_ascii=False), encoding="utf-8")
            continue
        m = re.search(r"\{.*\}", raw, re.S)
        rows = None
        if m:
            try:
                rows = json.loads(m.group(0)).get("rows")
            except Exception:  # noqa: BLE001
                rows = None
        ansf.write_text(json.dumps({"k": blk["k"], "rows": rows, "raw": raw},
                                   ensure_ascii=False, indent=1), encoding="utf-8")
        done += 1
    return stem, fail == 0, f"答{done} 跳{skip} 败{fail}"


_PUNC = re.compile(r"[\s,，。.;；:：、·()（）\-—―~〕〔\[\]{}\"'“”‘’!！?？%°]")


def _norm(role, v):
    """比对归一:数值列去空格/°/,;文本列去空白;desc 另折半/全角标点
    (两引擎标点习惯差异大,只让真字差进差异账)。返回 (kind, 规范值)。"""
    if v is None:
        return "empty", ""
    s = str(v).strip()
    if not s:
        return "empty", ""
    if role in ("depth", "thick", "length", "true_thick"):
        t = s.replace(" ", "").replace("°", "").rstrip(",。.")
        try:
            return "num", round(float(t), 3)
        except ValueError:
            return "text", s
    if role == "dip":
        return "text", s.replace(" ", "").replace("°", "")
    if role == "desc":
        return "text", _PUNC.sub("", s)
    return "text", re.sub(r"\s+", "", s)


def compare_one(stem):
    """块账+答 → 对回整合 xlsx 逐格比对,写 比对.json。返回 (stem, ok, info)。"""
    from openpyxl import load_workbook
    outd = OUT / stem
    账 = json.loads((outd / "块账.json").read_text(encoding="utf-8"))
    wb = load_workbook(paths.FINALIZE_FULL_DIR / f"{stem}_整合.xlsx", rich_text=True)
    ws = wb.active
    xdata = list(ws.iter_rows(values_only=True))
    roles = 账["roles"]
    keys = [r for r in ("layer", "depth", "thick", "length", "dip",
                        "true_thick", "desc") if r in roles]   # era 已定稿不比对
    diffs, n_seen, n_diff = [], 0, 0
    for blk in 账["blocks"]:
        ans = json.loads((outd / f"{Path(blk['file']).stem}.答.json")
                         .read_text(encoding="utf-8"))
        rows = ans.get("rows")
        if not rows:
            diffs.append({"块": blk["k"], "问题": "Agnes无解析行"})
            continue
        a, b = blk["行"]
        if len(rows) != b - a + 1:
            diffs.append({"块": blk["k"], "问题": f"行数不齐 Agnes={len(rows)} 应={b - a + 1}"})
        for j, arow in enumerate(rows):
            di = a + j
            if di > b:
                break
            xr_ = di + 1                    # xdata 列表下标(xlsx 行=di+2,1基)
            if xr_ >= len(xdata):
                break
            _spread(arow, roles)
            for kk in keys:
                mine = xdata[xr_][roles[kk]] if len(xdata[xr_]) > roles[kk] else None
                theirs = (arow or {}).get(kk, "")
                k1, v1 = _norm(kk, mine)
                k2, v2 = _norm(kk, theirs)
                n_seen += 1
                if k1 == "empty" and k2 == "empty":
                    continue
                if k1 == "num" and k2 == "num" and abs(v1 - v2) < 0.005:
                    continue
                if k1 == k2 and v1 == v2:
                    continue
                n_diff += 1
                diffs.append({"块": blk["k"], "xlsx行": xr_, "数据行": di, "列": ROLE_CN[kk],
                              "角色": kk, "我方": "" if mine is None else str(mine),
                              "agnes": str(theirs)})
    (outd / "比对.json").write_text(json.dumps(
        {"stem": stem, "格数": n_seen, "差异": n_diff, "diffs": diffs},
        ensure_ascii=False, indent=1), encoding="utf-8")
    return stem, True, f"格{n_seen} 差异{n_diff}"


_LAYER_OK = re.compile(r"[0-9]{1,3}|[一二三四五六七八九十]+[上下中]?|[\u4e00-\u9fff]{1,4}组|[IVXivx]{1,3}|[ⅠⅡⅢⅣⅤⅥⅦⅧⅨⅩ]{1,2}")
_DIP_OK = re.compile(r"[0-9]{1,2}(\.[0-9]+)?")
_GARB = re.compile(r"[○□◇◆▪■|/\\{}<>?〔〕〖〗]")
_CJK = re.compile(r"[\u4e00-\u9fff]")


def _edist(a, b):
    """Levenshtein(>3 截断为 99,desc 长文本够用)。"""
    if abs(len(a) - len(b)) > 3:
        return 99
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i] + [0] * len(b)
        for j, cb in enumerate(b, 1):
            cur[j] = min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb))
        prev = cur
    return prev[-1]


def _num_ok(v):
    try:
        return 0 <= float(v) < 3000
    except (TypeError, ValueError):
        return False


def _spread(arow, roles):
    """Agnes 把相邻数值挤进一个字段的矫正:数值字段(按 xlsx 列序)某字段多 token
    且其后数值字段全空时,按列序逐一分摊。倾角带°不动。就地修改返回。"""
    order = sorted([(roles[r], r) for r in ("depth", "thick", "length", "true_thick")
                    if r in roles])
    cols = [r for _, r in order]
    spare = []
    for _, r in order:
        v = str((arow or {}).get(r, "") or "").strip()
        toks = [t for t in re.split(r"[|\s]+", v.replace("°", "")) if t]
        if len(toks) >= 2:
            spare = toks[1:]
            arow[r] = toks[0]
        elif v == "" and spare:
            arow[r] = spare.pop(0)
            if not spare:
                break
    return arow


def _anchor_seq(rows, a, b, xd, depth_of):
    """单调序列对齐(2026-10-29 三读版,替代贪心最近位):深度列严格递增,
    Agnes 行序与 xlsx 行序是同序双序列,DP 最大化 |xd(di)-depth(j)|≤0.005
    的配对数且配对保持两序单调——行归属漂移(整块错行)由此归位。
    返回 {Agnes行j: xlsx数据行di}。"""
    m, n = len(rows), b - a + 1
    dvs = [depth_of(r) for r in rows]
    xds = []
    for t in range(n):
        v = xd(a + t)
        xds.append(v)
    ok = [[(dvs[j] is not None and xds[t] is not None
            and abs(xds[t] - dvs[j]) <= 0.005) for t in range(n)]
          for j in range(m)]
    dp = [[0] * (n + 1) for _ in range(m + 1)]
    for j in range(1, m + 1):
        for t in range(1, n + 1):
            best = max(dp[j - 1][t], dp[j][t - 1])
            if ok[j - 1][t - 1]:
                best = max(best, dp[j - 1][t - 1] + 1)
            dp[j][t] = best
    claim, j, t = {}, m, n
    while j > 0 and t > 0:
        if ok[j - 1][t - 1] and dp[j][t] == dp[j - 1][t - 1] + 1:
            claim[j - 1] = a + t - 1
            j -= 1
            t -= 1
        elif dp[j - 1][t] == dp[j][t]:
            j -= 1
        else:
            t -= 1
    return claim


def _ag_depth_tok(arow):
    """Agnes 行的深度首 token(±0.005 锚定用);解析失败返回 None。"""
    toks = [t for t in re.split(r"[|\s]+", str((arow or {}).get("depth", ""))
                                .replace("°", "")) if t]
    try:
        return round(float(toks[0]), 2)
    except (TypeError, ValueError, IndexError):
        return None


def _anchor_runs(runs, a, b, xd, roles):
    """每次读数独立单调 DP 锚定 + 双空行按位补配;返回 [(rows, claim{j: di})]。
    decide 与 compare3 共用,保证对照表与裁决同口径;就地 _spread 各读行。"""
    anchored = []
    for rows in runs:
        claim = _anchor_seq(rows, a, b, xd, _ag_depth_tok)
        used = set(claim.values())
        free = [di for di in range(a, b + 1) if di not in used]
        for j, arow in enumerate(rows):
            if j in claim:
                continue
            di = a + j
            if di in free and xd(di) is None and _ag_depth_tok(arow) is None:
                claim[j] = di
                free.remove(di)
        for arow in rows:
            _spread(arow, roles)
        anchored.append((rows, claim))
    return anchored


def _sliver_rows(stem):
    """缝行集合(2026-11-03):数据行所在带沿表宽5取样的最小带高<12px
    → 顶底界线交叉(缝行/倒挂带),非真实层行(1016带124 石灰岩案实证)。"""
    import numpy as np
    SLIVER_MIN = 12   # 窗修复回退(2026-11-04)后就地定值,判据与当时实测一致
    from src.table.track_rows import row_y
    try:
        g = chart_rows(stem)
    except Exception:  # noqa: BLE001
        return set()
    bmap, rows_r = g["bmap"], g["rows_r"]
    tl, tr = g["rd"]["table_x"]
    n = len(bmap) - 1
    out = set()
    xs = np.linspace(tl + 60, tr - 60, 5)
    for di in range(n):
        p = di
        while p >= 0 and bmap[p] is None:
            p -= 1
        q = di + 1
        while q <= n and bmap[q] is None:
            q += 1
        if p < 0 or q > n:
            continue
        hmin = min(row_y(rows_r[bmap[q]], x) - row_y(rows_r[bmap[p]], x) for x in xs)
        if hmin < SLIVER_MIN:
            out.add(di)
    return out


def decide_one(stem):
    """块答 + 整合 xlsx → 裁决.json。只裁行数对齐的块;三档处置:
    应用(有据,入裁决文件交 finalize 块2.7)/旗(无据,留验收)/维持(信我方)。
    数值=深度链算术仲裁;层号/倾角=约束词表;desc=残句/乱码特征+编辑距。"""
    from openpyxl import load_workbook
    outd = OUT / stem
    账 = json.loads((outd / "块账.json").read_text(encoding="utf-8"))
    roles = 账["roles"]
    wb = load_workbook(paths.FINALIZE_FULL_DIR / f"{stem}_整合.xlsx")
    ws = wb.active
    xdata = list(ws.iter_rows(values_only=True))
    keys = [r for r in ("layer", "depth", "thick", "length", "dip",
                        "true_thick", "desc") if r in roles]
    verdicts, blocks_bad, n_锚不齐 = [], [], 0
    merged_rows = {"layer": set(), "dip": set()}
    for mr in ws.merged_cells.ranges:
        for role in ("layer", "dip"):
            ci = roles.get(role)
            if ci is not None and mr.min_col == ci + 1:
                merged_rows[role].update(range(mr.min_row - 2, mr.max_row - 1))

    def xd(di):
        v = _g(xdata, roles, di, roles["depth"]) if "depth" in roles else None
        try:
            return round(float(v), 2)
        except (TypeError, ValueError):
            return None

    _ag_depth = _ag_depth_tok

    def xv(di, k):
        row = xdata[di + 1] if di + 1 < len(xdata) else ()   # di=数据行0基,xlsx行=di+2(1基)
        return row[roles[k]] if len(row) > roles[k] else None

    for blk in 账["blocks"]:
        stem_b = Path(blk["file"]).stem
        runs = []
        f2 = outd / f"{stem_b}.答.json"
        if f2.exists():
            r = json.loads(f2.read_text(encoding="utf-8")).get("rows")
            if r:
                runs.append(r)
        rep = paths.AGNES_REPEAT_DIR_20261029 / stem
        for tag in ("第1次", "第2次"):
            f1 = None
            for cand_name in (f"{stem_b}.{tag}.json", f"{stem_b}.答.{tag}.json"):
                p1 = rep / cand_name
                if p1.exists():
                    f1 = p1
                    break
            if f1 is not None:
                r = json.loads(f1.read_text(encoding="utf-8")).get("rows")
                if r:
                    runs.append(r)
        a, b = blk["行"]
        if not runs:
            blocks_bad.append({"块": blk["k"], "应": b - a + 1, "答": 0})
            continue
        # 每次读数独立单调锚定(与 compare3 对照表共用 _anchor_runs,同口径)。
        anchored = _anchor_runs(runs, a, b, xd, roles)
        for rows, claim in anchored:
            n_锚不齐 += len(rows) - len(claim)
        per_di = {}
        for rows, claim in anchored:
            for j, di in claim.items():
                per_di.setdefault(di, []).append(rows[j])
        for di, arows in sorted(per_di.items()):
            for k in keys:
                k1, v1 = _norm(k, xv(di, k))
                cands = {}
                for arow in arows:
                    _, vv = _norm(k, arow.get(k, ""))
                    cands.setdefault(vv, []).append(arow)
                if k == "desc":
                    # desc 全票制下的处置(2026-10-29 用户裁定二次收紧):
                    # 投票只证明读得稳,不证明读得对(同输入无法排除系统性错误)——
                    # 故多数票不再采值;仅 我方空/残句 补录仍应用,其余分歧旗挂像素核验。
                    mine_v = len(cands.get(v1, [])) + (0 if k1 == "empty" else 1)
                    diff = {vv: c for vv, c in cands.items()
                            if vv != v1 and vv != "empty"}
                    if not diff:
                        continue
                    best_v = max(diff, key=lambda t: len(diff[t]))
                    best_n = len(diff[best_v])
                    if k1 == "empty" or len(v1) <= 2:
                        arow = diff[best_v][0]
                        entry = {"图": stem, "行": di + 2, "角色": k, "列": ROLE_CN[k],
                                 "原": "" if xv(di, k) is None else str(xv(di, k)),
                                 "agnes": str(arow.get(k, ""))}
                        k2, v2 = _norm(k, entry["agnes"])
                        _adjudicate(entry, di, k, roles, xdata, k1, v1, k2, v2,
                                    merged_rows.get(k, set()), arow)
                        entry["依据"] += f"(读{best_n}票:我方{mine_v}票)"
                        verdicts.append(entry)
                    else:
                        verdicts.append({"图": stem, "行": di + 2, "角色": k,
                                         "列": ROLE_CN[k],
                                         "原": "" if xv(di, k) is None else str(xv(di, k)),
                                         "agnes": str(diff[best_v][0].get(k, "")),
                                         "处置": "旗", "应用": 0,
                                         "依据": f"描述分歧:同输入投票不采,留像素核验"
                                                 f"(读{best_n}票:我方{mine_v}票)"})
                    continue
                diff = [vv for vv in cands if vv != v1 and not (k1 == "empty" and vv == "empty")]
                if not diff:
                    continue
                if len(diff) > 1:
                    verdicts.append({"图": stem, "行": di + 2, "角色": k, "列": ROLE_CN[k],
                                     "原": "" if xv(di, k) is None else str(xv(di, k)),
                                     "agnes": " ┃ ".join(str(cands[vv][0].get(k, ""))[:40]
                                                         for vv in diff),
                                     "处置": "旗", "应用": 0,
                                     "依据": f"多读互歧({len(diff)}种):留人核"})
                    continue
                vv = diff[0]
                arow = cands[vv][0]
                n_sup = len(cands[vv])
                entry = {"图": stem, "行": di + 2, "角色": k, "列": ROLE_CN[k],
                         "原": "" if xv(di, k) is None else str(xv(di, k)),
                         "agnes": str(arow.get(k, ""))}
                k2, v2 = _norm(k, entry["agnes"])
                _adjudicate(entry, di, k, roles, xdata, k1, v1, k2, v2,
                            merged_rows.get(k, set()), arow)
                if entry["处置"] == "应用" and n_sup < len(arows):
                    entry["依据"] += f"(仅{n_sup}/{len(arows)}读此值,余同我方)"
                verdicts.append(entry)
    # 缝行守卫(2026-11-03):交叉线缝行=非真实层行,向缝行补录会与真层行重复
    # (1016行126 石灰岩双行实证,17/221 应用打在缝行)——缝行应用一律改旗留人核。
    sliver = _sliver_rows(stem)
    for entry in verdicts:
        if entry.get("处置") == "应用" and int(entry["行"]) - 2 in sliver:
            entry["处置"], entry["应用"] = "旗", 0
            entry["依据"] = "缝行(交叉线带)疑非真实层行,应用改旗留人核;原据:" + entry.get("依据", "")
    (outd / "裁决.json").write_text(json.dumps(
        {"stem": stem, "块行数不齐": blocks_bad, "锚不齐行": n_锚不齐, "条目": verdicts},
        ensure_ascii=False, indent=1), encoding="utf-8")
    n_app = sum(1 for e in verdicts if e["处置"] == "应用")
    n_flag = sum(1 for e in verdicts if e["处置"] == "旗")
    return stem, True, f"条目{len(verdicts)} 应用{n_app} 旗{n_flag} 行数不齐{len(blocks_bad)} 锚不齐{n_锚不齐}"


def _g(xdata, roles, rr, col):
    """xlsx 数据行 rr(0基) 的 col 列,越界安全。rr+2=xlsx 行(1基),列表下标=rr+1。"""
    row = xdata[rr + 1] if rr + 1 < len(xdata) else ()
    return row[col] if 0 <= col < len(row) else None


def _adjudicate(entry, di, k, roles, xdata, k1, v1, k2, v2, merged=(), arow=None):
    """就地填 entry 的 处置/新值/依据(纯函数,便于回测)。merged=该列合并区数据行集合。"""
    entry["处置"], entry["应用"] = "旗", 0

    def chain_score(val):
        """di 行 k 列换成 val 后的可判式闭合数(邻居取 xlsx 现值):
        depth 两式 d[i-1]+t[i]=val、val+t[i+1]=d[i+1];thick 一式 d[i-1]+val=d[i]
        (thick 的邻行式不含 val,对判别无贡献不算)。"""
        dep, thk = roles.get("depth"), roles.get("thick")
        if dep is None or thk is None or k not in ("depth", "thick"):
            return 0
        n = len(xdata) - 3
        hits = 0
        try:
            fv = float(val)
            if k == "depth":
                if di >= 1 and _num_ok(_g(xdata, roles, di - 1, dep)) \
                        and _num_ok(_g(xdata, roles, di, thk)) \
                        and abs(float(_g(xdata, roles, di - 1, dep))
                                + float(_g(xdata, roles, di, thk)) - fv) <= 0.02:
                    hits += 1
                if di + 1 <= n and _num_ok(_g(xdata, roles, di + 1, dep)) \
                        and _num_ok(_g(xdata, roles, di + 1, thk)) \
                        and abs(fv + float(_g(xdata, roles, di + 1, thk))
                                - float(_g(xdata, roles, di + 1, dep))) <= 0.02:
                    hits += 1
            else:
                if di >= 1 and _num_ok(_g(xdata, roles, di - 1, dep)) \
                        and _num_ok(_g(xdata, roles, di, dep)) \
                        and abs(float(_g(xdata, roles, di - 1, dep)) - fv
                                - float(_g(xdata, roles, di, dep))) <= 0.02:
                    hits += 1
        except (TypeError, ValueError):
            return 0
        return hits

    if k in ("depth", "thick", "length", "true_thick"):
        toks = [t for t in re.split(r"[|\s]+", str(entry["agnes"]).replace("°", "")) if t]
        if len(toks) >= 2:
            entry["依据"] = f"Agnes多值(粘连证据): {'|'.join(toks)}"
            return
        if k2 != "num":
            if k1 == "num":
                entry["处置"], entry["依据"] = "维持", "Agnes非数值,信我方"
            else:
                entry["依据"] = "双方皆非数值"
            return
        # 列滑旁证:Agnes 数与本行其他数值列(或其去点形)相同=读串列,信我方
        _dig = lambda s: re.sub(r"[^0-9]", "", str(s))  # noqa: E731
        if arow is not None and k1 == "empty":
            for _r2 in ("depth", "thick", "length", "true_thick"):
                if _r2 == k:
                    continue
                _v = (arow or {}).get(_r2, "")
                _n2, _w2 = _norm(_r2, _v)
                if _n2 == "num" and (abs(_w2 - v2) < 0.005 or
                                     (_dig(_v) == _dig(entry["agnes"]) and _dig(_v))):
                    entry["处置"], entry["依据"] = "维持", "Agnes列滑(值见他列),信我方"
                    return
        if k1 != "num":
            if k == "depth" and chain_score(v2) >= 1:
                entry["处置"], entry["新值"] = "应用", entry["agnes"]
                entry["依据"] = "我方空/非数值,Agnes数值且链闭合"
            else:
                entry["依据"] = "我方空,Agnes数值但链不闭合"
            return
        so, sa = chain_score(v1), chain_score(v2)
        if sa > so:
            entry["处置"], entry["新值"] = "应用", entry["agnes"]
            entry["依据"] = f"深度链仲裁:换Agnes闭合{sa}式>我方{so}式"
        elif so > 0:
            entry["处置"], entry["依据"] = "维持", f"链仲裁我方{so}式>Agnes{sa}式"
        else:
            # 双方都无法用链判:深度/层厚另有逆序与层厚≠深度差门禁旗管,此处不复旗
            entry["处置"], entry["依据"] = "维持", "链无判别力(邻行链断),留数值门禁管"
        return
    if k == "dip":
        a_clean = bool(_DIP_OK.fullmatch(v2))
        o_clean = bool(_DIP_OK.fullmatch(v1))
        if a_clean and k1 == "empty":
            if di in merged:
                entry["处置"], entry["依据"] = "维持", "合并区续行,值在区首"
            else:
                entry["处置"], entry["新值"] = "应用", str(entry["agnes"]).strip()
                entry["依据"] = "我方漏读倾角(原图像素在),Agnes纯数值补"
        elif a_clean and not o_clean:
            entry["处置"], entry["新值"] = "应用", str(entry["agnes"]).strip()
            entry["依据"] = "倾角词表:Agnes纯数值,我方含杂"
        elif o_clean and a_clean:
            entry["依据"] = "双方皆纯数值,留人核"
        elif o_clean:
            entry["处置"], entry["依据"] = "维持", "Agnes含杂,信我方"
        else:
            entry["依据"] = "双方含杂"
        return
    if k == "layer":
        a_num = bool(re.fullmatch(r"[0-9]{1,3}", v2))
        o_num = bool(re.fullmatch(r"[0-9]{1,3}", v1))
        a_ok = bool(_LAYER_OK.fullmatch(v2))
        o_ok = bool(_LAYER_OK.fullmatch(v1))
        if a_ok and k1 == "empty" and di in merged:
            entry["处置"], entry["依据"] = "维持", "合并区续行,值在区首"
        elif a_ok and k1 == "empty":
            entry["处置"], entry["新值"] = "应用", str(entry["agnes"]).strip()
            entry["依据"] = "我方漏读层号(原图像素在),Agnes词表合法补"
        elif a_ok and not o_ok:
            entry["处置"], entry["新值"] = "应用", str(entry["agnes"]).strip()
            entry["依据"] = "层号词表:Agnes合法(数字/中文数字/组名),我方乱码"
        elif k1 != "empty" and k2 != "empty" and not (a_num and o_num):
            # 文本类层号(组名/中文数字/罗马)分歧:同输入读数互歧,投票不可采
            # (2026-10-29 用户裁定:输入相同无法排除系统性错误,多数≠正确),留像素核验
            entry["依据"] = "层号文本分歧:同输入投票不采,留像素核验"
        elif o_ok:
            entry["处置"], entry["依据"] = "维持", "纯数字互歧,留人核" if (a_num and o_num) else "我方已合法,不换"
        else:
            entry["依据"] = "双方皆不合词表"
        return
    # desc:我方空/残句=补录(用户 2026-10-29 批准保留);其余文本分歧一律不采投票
    # (2026-10-29 用户裁定:同输入读数无法排除系统性错误,多数≠正确),旗挂像素核验
    a_raw = str(entry["agnes"]).strip()
    if k2 == "empty":
        entry["处置"], entry["依据"] = "维持", "Agnes无读,信我方"
        return
    if k1 == "empty" or len(v1) <= 2:
        if a_raw:
            entry["处置"], entry["新值"] = "应用", a_raw
            entry["依据"] = "我方空/残句,采Agnes成句(像素核验包可核)"
        else:
            entry["依据"] = "我方空,Agnes亦空"
        return
    entry["依据"] = "描述分歧:同输入投票不采,留像素核验"


def _pack_cells(stem):
    """待像素核验格:同输入投票不采的分歧旗 + 空格/残句补录应用。"""
    outd = OUT / stem
    cells = []
    vp = outd / "裁决.json"
    if vp.exists():
        for e in json.loads(vp.read_text(encoding="utf-8")).get("条目", []):
            d = e.get("依据", "")
            if "留像素核验" in d or "采Agnes成句" in d:
                cells.append(e)
    return cells


def pixel_pack_one(stem):
    """像素核验包(2026-10-29 用户裁定:同输入多数≠正确,分歧由人眼对原图裁决):
    待核格各裁原图单格裁片(原始像素,柱状/水文同口径遮蔽可后加),配核验索引表
    (程序原值+读1/2/3+现交付值+结论空列)。写 AGNES_PIXEL_PACK_DIR_20261029。"""
    import cv2
    from openpyxl import Workbook, load_workbook
    from openpyxl.styles import Alignment
    outd = OUT / stem
    cells = _pack_cells(stem)
    if not cells:
        return stem, True, "无待核格"
    账 = json.loads((outd / "块账.json").read_text(encoding="utf-8"))
    roles = 账["roles"]
    g = chart_rows(stem)
    rawp = next((paths.RAW_DIR / f"{stem}{s}" for s in (".JPG", ".jpg", ".jpeg")
                 if (paths.RAW_DIR / f"{stem}{s}").exists()), None)
    if rawp is None:
        return stem, False, "无原图"
    gray = cv2.imread(str(rawp), cv2.IMREAD_GRAYSCALE)
    wb = load_workbook(paths.FINALIZE_FULL_DIR / f"{stem}_整合.xlsx")
    xdata = list(wb.active.iter_rows(values_only=True))
    sep = g["hm"]["sep_pts"]
    keep = g["hm"]["keep"]
    bmap = g["bmap"]

    def bnd(pos, step):
        p = pos
        while 0 <= p < len(bmap) and bmap[p] is None:
            p += step
        return bmap[p] if 0 <= p < len(bmap) else None

    cmp_rows = {}
    cmp_p = paths.AGNES_COMPARE3_DIR_20261029 / f"{stem}_三读对照.xlsx"
    if cmp_p.exists():
        for r in load_workbook(cmp_p)["对照"].iter_rows(min_row=2, values_only=True):
            cmp_rows[(r[0], r[2])] = r
    pdir = paths.AGNES_PIXEL_PACK_DIR_20261029 / stem
    pdir.mkdir(parents=True, exist_ok=True)
    wbo = Workbook()
    sho = wbo.active
    sho.title = "核验索引"
    sho.append(["文件", "xlsx行", "角色", "程序原值", "读1", "读2", "读3",
                "现交付值", "核验类型", "核验结论(填:保持/新值)"])
    n_png = 0
    for e in cells:
        r_x = int(e["行"])
        di = r_x - 2
        k = e["角色"]
        c = roles.get(k)
        if c is None or not (0 <= di < len(bmap) - 1):
            continue
        bi0, bi1 = bnd(di, -1), bnd(di + 1, 1)
        if bi0 is None or bi1 is None:
            continue
        y0, _ = _bound_span(g, bi0)
        _, y1 = _bound_span(g, bi1)
        y0, y1 = int(round(y0)), int(round(y1))
        kk = keep[c] if c < len(keep) else {}
        xm = (y0 + y1) // 2
        ls, rs = kk.get("left_sep"), kk.get("right_sep")
        x0 = (int(np.interp(xm, sep[ls]["ys"], sep[ls]["xs"])) if ls is not None
              else int(g["rd"]["table_x"][0]))
        x1 = (int(np.interp(xm, sep[rs]["ys"], sep[rs]["xs"])) if rs is not None
              else int(g["rd"]["table_x"][1]))
        crop = gray[max(0, y0 - PAD_Y):min(gray.shape[0], y1 + PAD_Y),
                    max(0, x0 - PAD_X):min(gray.shape[1], x1 + PAD_X)]
        if crop.size == 0:
            continue
        fn = f"行{r_x:03d}_{ROLE_CN.get(k, k)}.png"
        cv2.imwrite(str(pdir / fn), crop)
        n_png += 1
        rowv = xdata[di + 1] if di + 1 < len(xdata) else ()
        cur = rowv[c] if len(rowv) > c else None
        cr = cmp_rows.get((r_x, k))
        typ = "补录(现值=Agnes读)" if "采Agnes成句" in e.get("依据", "") else "投票分歧(现值=程序原值)"
        sho.append([fn, r_x, ROLE_CN.get(k, k),
                    "" if e.get("原") is None else str(e["原"]),
                    str(cr[4]) if cr else "", str(cr[5]) if cr else "",
                    str(cr[6]) if cr else "",
                    "" if cur is None else str(cur), typ,
                    e.get("依据", "")[:44], ""])
    for col, w in zip("ABCDEFGHIJK", (26, 7, 9, 40, 40, 40, 40, 40, 20, 40, 16)):
        sho.column_dimensions[col].width = w
    for row in sho.iter_rows(min_row=2):
        for cc in row:
            cc.alignment = Alignment(vertical="top", wrap_text=True)
    outp = paths.AGNES_PIXEL_PACK_DIR_20261029
    outp.mkdir(parents=True, exist_ok=True)
    wbo.save(outp / f"{stem}_核验索引.xlsx")
    return stem, True, f"裁片{n_png} 待核{len(cells)}"


def _pack_job(p):
    return pixel_pack_one(p[0])


def _decide_job(p):
    return decide_one(p[0])


def compare3_one(stem):
    """三读+我方逐格对照表(2026-10-29 用户要求):每数据行×角色一行,
    读1/读2/读3 按 DP 锚定到行(与 decide 共用 _anchor_runs,同口径);
    三读一致/我方是否=多数/裁决采纳值逐格可见。写 AGNES_COMPARE3_DIR_20261029。"""
    from openpyxl import Workbook, load_workbook
    from openpyxl.styles import Alignment
    outd = OUT / stem
    账 = json.loads((outd / "块账.json").read_text(encoding="utf-8"))
    roles = 账["roles"]
    wb = load_workbook(paths.FINALIZE_FULL_DIR / f"{stem}_整合.xlsx")
    xdata = list(wb.active.iter_rows(values_only=True))
    n_data = len(xdata) - 1
    keys = [r for r in ("layer", "depth", "thick", "length", "dip",
                        "true_thick", "desc") if r in roles]

    def xd(di):
        row = xdata[di + 1] if di + 1 < len(xdata) else ()
        v = row[roles["depth"]] if "depth" in roles and len(row) > roles["depth"] else None
        try:
            return round(float(v), 2)
        except (TypeError, ValueError):
            return None

    rep = paths.AGNES_REPEAT_DIR_20261029 / stem
    vmap = {}
    vp = outd / "裁决.json"
    if vp.exists():
        for e in json.loads(vp.read_text(encoding="utf-8")).get("条目", []):
            vmap[(int(e["行"]), e["角色"])] = e
    reads = {"读1": {}, "读2": {}, "读3": {}}
    for blk in 账["blocks"]:
        sb = Path(blk["file"]).stem
        runs = []
        for tag, f in (("读1", rep / f"{sb}.答.第1次.json"),
                       ("读2", rep / f"{sb}.答.第2次.json"),
                       ("读3", outd / f"{sb}.答.json")):
            if f.exists():
                r = json.loads(f.read_text(encoding="utf-8")).get("rows")
                if r:
                    runs.append((tag, r))
        if not runs:
            continue
        a, b = blk["行"]
        tagged = _anchor_runs([r for _, r in runs], a, b, xd, roles)
        for (tag, _), (rows, claim) in zip(runs, tagged):
            for j, di in claim.items():
                reads[tag][di] = rows[j]
    wbo = Workbook()
    sho = wbo.active
    sho.title = "对照"
    sho.append(["xlsx行", "深度", "角色", "我方(原始程序)", "读1", "读2", "读3",
                "三读一致", "我方=读多数", "处置", "采纳值", "依据摘要"])
    stat = {}
    for di in range(n_data):
        rowv = xdata[di + 1] if di + 1 < len(xdata) else ()
        for k in keys:
            ours = rowv[roles[k]] if len(rowv) > roles[k] else None
            # 我方列=原始程序读数:有裁决条目的格用裁决原值(decide 时基线值),
            # 其余格交付值即原值(Agnes 未动它)。投票也按原值计,与 decide 同口径。
            v = vmap.get((di + 2, k))
            ours_s = str(v["原"]) if v is not None else (
                "" if ours is None else str(ours))
            vals = [reads[t].get(di, {}).get(k) for t in ("读1", "读2", "读3")]
            shown = ["(未锚)" if r is None else str(r) for r in vals]
            folds = [_norm(k, s)[1] for s in shown if s != "(未锚)"]
            n_read = len(folds)
            k1, v1 = _norm(k, ours_s)
            votes = {}
            for f in folds:
                votes[f] = votes.get(f, 0) + 1
            top_v, top_n = max(votes.items(), key=lambda t: t[1]) if votes else ("", 0)
            has_major = n_read > 0 and top_n * 2 > n_read
            same3 = "是" if (n_read == 3 and len(votes) == 1) else ("否" if n_read else "")
            mine_maj = ("是" if has_major and top_v == v1
                        else ("否" if has_major else ""))
            sho.append([di + 2,
                        "" if xd(di) is None else xd(di), k,
                        ours_s,
                        shown[0], shown[1], shown[2], same3, mine_maj,
                        "" if v is None else v["处置"],
                        "" if v is None else str(v.get("新值") or ""),
                        "" if v is None else str(v.get("依据") or "")[:44]])
            st = stat.setdefault(k, {"比格": 0, "全同": 0, "我方多数": 0})
            if n_read:
                st["比格"] += 1
                st["全同"] += 1 if same3 == "是" else 0
                st["我方多数"] += 1 if mine_maj == "是" else 0
    sho2 = wbo.create_sheet("汇总")
    sho2.append(["角色", "可比格", "三读全同", "全同率", "我方=读多数", "我方多数率"])
    for k in keys:
        st = stat.get(k, {"比格": 0, "全同": 0, "我方多数": 0})
        sho2.append([k, st["比格"], st["全同"],
                     round(st["全同"] / st["比格"], 3) if st["比格"] else "",
                     st["我方多数"],
                     round(st["我方多数"] / st["比格"], 3) if st["比格"] else ""])
    for col, w in zip("ABCDEFGHIJKL", (7, 8, 9, 44, 44, 44, 44, 9, 11, 7, 22, 40)):
        sho.column_dimensions[col].width = w
    for row in sho.iter_rows(min_row=2):
        for c in row:
            c.alignment = Alignment(vertical="top", wrap_text=True)
    outp = paths.AGNES_COMPARE3_DIR_20261029
    outp.mkdir(parents=True, exist_ok=True)
    wbo.save(outp / f"{stem}_三读对照.xlsx")
    n_cmp = sum(st["比格"] for st in stat.values())
    n_same = sum(st["全同"] for st in stat.values())
    n_mine = sum(st["我方多数"] for st in stat.values())
    return stem, True, (f"行{n_data} 可比{n_cmp} 三读全同{n_same}"
                        f"({n_same / n_cmp:.0%}) 我方=多数{n_mine}"
                        f"({n_mine / n_cmp:.0%})" if n_cmp else f"行{n_data} 无可比格")


def _compare3_job(p):
    return compare3_one(p[0])


def _stems(argv):
    want = {s if s.startswith("钻孔柱状图") else f"钻孔柱状图{s}" for s in argv}
    if want:
        return sorted(want)
    return sorted(p.stem for p in paths.RAW_DIR.glob("*.JPG"))


def _crop_job(p):
    return crop_one(p[0])


def _compare_job(p):
    return compare_one(p[0])


def main():
    if not sys.argv[1:] or sys.argv[1] not in ("crop", "read", "compare", "decide",
                                               "compare3", "pixel_pack"):
        print(__doc__)
        return 2
    cmd = sys.argv[1]
    rest = [a for a in sys.argv[2:] if a != "--force"]
    force = "--force" in sys.argv[2:]
    stems = _stems(rest)
    if cmd == "crop":
        results = batch.run_batch([(s,) for s in stems], _crop_job, max_workers=4)
        bad = [r for _, ok, r in results if not ok]
        print("\n".join(f"{s} {r}" for s, ok, r in results))
        return 1 if bad else 0
    if cmd == "read":
        with ThreadPoolExecutor(max_workers=12) as ex:
            futs = {ex.submit(read_one, s, force): s for s in stems}
            fails = 0
            for fu in as_completed(futs):
                s = futs[fu]
                try:
                    _, ok, info = fu.result()
                except Exception as e:  # noqa: BLE001
                    ok, info = False, repr(e)[:150]
                fails += 0 if ok else 1
                print(s, info, flush=True)
        return 1 if fails else 0
    if cmd == "decide":
        results = batch.run_batch([(s,) for s in stems], _decide_job, max_workers=4)
        print("\n".join(f"{s} {r}" for s, ok, r in results))
        return 0
    if cmd == "compare3":
        results = batch.run_batch([(s,) for s in stems], _compare3_job, max_workers=4)
        print("\n".join(f"{s} {r}" for s, ok, r in results))
        return 0
    if cmd == "pixel_pack":
        results = batch.run_batch([(s,) for s in stems], _pack_job, max_workers=4)
        print("\n".join(f"{s} {r}" for s, ok, r in results))
        return 0
    results = batch.run_batch([(s,) for s in stems], _compare_job, max_workers=4)
    print("\n".join(f"{s} {r}" for s, ok, r in results))
    return 0


if __name__ == "__main__":
    sys.exit(main())
