# -*- coding: utf-8 -*-
"""按区域层序重建地层块并对比交付版（报告模式，只读）。

输入：
  - paths.DELIVERY_XLSX（桌面交付文件）
  - paths.AI_PIPELINE_DIR（外部 LLM 重建管线 field_graph 产物，当前未纳入本项目）
"""
import json
import os
import sys
from bisect import bisect
from collections import OrderedDict
from pathlib import Path

import openpyxl

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))
from src.core import paths

F = str(paths.DELIVERY_XLSX)
BASE = str(paths.AI_PIPELINE_DIR)

# 区域标准层序（有序）
ORDER = ['第四系','飞仙关组','飞仙关组一段','飞仙关组二段','飞仙关组一至二段','飞仙关组二至一段',
         '大隆组','长兴组','龙潭组上段','龙潭组中段','龙潭组下段','茅口组']
# 粗归类目标
CANON = ['第四系','飞仙关组','大隆组','长兴组','龙潭组上段','龙潭组中段','龙潭组下段','茅口组']


def bnum(b):
    return int(b.split('_')[1])


def parse_depth(v):
    if isinstance(v, (int, float)):
        return float(v)
    if isinstance(v, str):
        s = v.strip().replace(' ', '')
        if s == '':
            return None
        try:
            return float(s)
        except Exception:
            return None
    return None


def coarse_clean(pv):
    """把原始 positioning_value 清洗为 8 个标准层之一（或 None）"""
    if not pv:
        return None
    s = pv
    # OCR 变体纠错
    repl = [('仙关组','飞仙关组'),('茅日','茅口'),('矛口','茅口'),('猫口','茅口'),('茆口','茅口'),('茅□','茅口'),
            ('龙谭','龙潭'),('龙湖潭','龙潭'),('龙潭以早','龙潭'),('龙潭16','龙潭'),
            ('龙潭中组','龙潭组中段'),('龙潭组上设','龙潭组上段'),('潭组上段','龙潭组上段'),
            ('潭组下段','龙潭组下段'),('龙潭组下组','龙潭组下段'),('龙潭组段','龙潭组中段'),
            ('龙潭中段','龙潭组中段'),('龙潭组王段','龙潭组一段'),('飞仙飞仙','飞仙'),
            ('大隆隆','大隆'),('长兴V','长兴'),('第目系','第四系'),('弟四系','第四系'),
            ('关组段','龙潭组中段'),('至段','长兴组'),('段大隆','大隆'),('人隆',''),
            ('仙关组至','飞仙关组'),('龙潭组二至一段一段','龙潭组二至一段'),
            ('飞仙关组二至一段一段','飞仙关组二至一段'),('大隆组人隆组','大隆组'),
            ('龙潭组上','龙潭组上段'),('龙潭组下','龙潭组下段'),('龙潭组中','龙潭组中段')]
    for a, b in repl:
        s = s.replace(a, b)
    # 粗归类
    if '第四系' in s or '第四糸' in s:
        return '第四系'
    if '飞仙' in s:
        return '飞仙关组'
    if '大隆' in s:
        return '大隆组'
    if '长兴' in s:
        return '长兴组'
    if '龙潭组上' in s or '龙潭上' in s:
        return '龙潭组上段'
    if '龙潭组中' in s or '龙潭中' in s or '龙潭组段' in s:
        return '龙潭组中段'
    if '龙潭组下' in s or '龙潭下' in s:
        return '龙潭组下段'
    if '龙潭' in s:
        return '龙潭组'   # 粗：待细分
    if '茅口' in s:
        return '茅口组'
    if s.strip() in ('段', '至段', '龙潭16', '龙潭以早组'):
        return None  # 过于模糊，作空处理
    return None


def fill_run(prev_lab, next_lab, count):
    """在 prev_lab 与 next_lab 之间，按区域层序填充 count 个带"""
    if count <= 0:
        return []
    if prev_lab is None:
        # 顶部空带（首个标注之前）
        if next_lab in ('飞仙关组', '大隆组', '长兴组'):
            return ['第四系'] * count
        if next_lab in ('龙潭组上段', '龙潭组中段', '龙潭组下段', '龙潭组', '茅口组'):
            return ['龙潭组下段'] * count  # 孔从龙潭组开始
        return [next_lab] * count
    if next_lab is None:
        return [prev_lab] * count  # 底部延伸
    if prev_lab not in ORDER or next_lab not in ORDER:
        return [prev_lab] * count
    pi = ORDER.index(prev_lab)
    ni = ORDER.index(next_lab)
    between = ORDER[pi + 1:ni]
    if not between:
        return [prev_lab] * count
    base = count // len(between)
    rem = count % len(between)
    res = []
    for i, f in enumerate(between):
        res += [f] * (base + (1 if i < rem else 0))
    return res


def build_band_formation(hole):
    p = os.path.join(BASE, f'{hole}.field_graph_d3_semantic.json')
    if not os.path.exists(p):
        return None
    d = json.load(open(p, encoding='utf-8'))
    gtg = d.get('geologic_text_graph') or {}
    nodes = {n['span_id']: n for n in gtg.get('nodes', [])}
    nB = len(d.get('atomic_bands', []))
    if nB == 0:
        return None
    age = [s for s in d.get('field_spans', []) if s.get('field_id') == 'geologic_age_physical']
    band_label = [None] * nB
    for s in age:
        node = nodes.get(s['span_id'])
        pv = node.get('positioning_value') if node else None
        bs = s.get('band_ids') or []
        if not bs:
            continue
        lo = min(bnum(b) for b in bs) - 1
        hi = max(bnum(b) for b in bs) - 1
        lo = max(0, lo)
        hi = min(nB - 1, hi)
        lab = coarse_clean(pv)
        for k in range(lo, hi + 1):
            band_label[k] = lab
    # 填空中带：在相邻标注之间按区域层序插值
    # 找到标注带索引
    labeled_idx = [i for i, l in enumerate(band_label) if l is not None]
    if not labeled_idx:
        return band_label  # 全空，无法重建
    # 顶部
    first = labeled_idx[0]
    if first > 0:
        top = fill_run(None, band_label[first], first)
        for i in range(first):
            band_label[i] = top[i]
    # 中间
    for a, b in zip(labeled_idx, labeled_idx[1:]):
        if b - a > 1:
            run = fill_run(band_label[a], band_label[b], b - a - 1)
            for i in range(a + 1, b):
                band_label[i] = run[i - a - 1]
    # 底部
    last = labeled_idx[-1]
    if last < nB - 1:
        for i in range(last + 1, nB):
            band_label[i] = band_label[last]
    return band_label


def band_depths(hole):
    """把每个 band 中心 y 线性标定到交付深度轴，返回每带深度"""
    p = os.path.join(BASE, f'{hole}.field_graph_d3_semantic.json')
    d = json.load(open(p, encoding='utf-8'))
    bands = d['atomic_bands']
    ys = [((b.get('reference_top_y') or 0) + (b.get('reference_bottom_y') or 0)) / 2 for b in bands]
    return ys  # 还需与交付深度配准，见 map_rows


def map_rows(hole, band_label, ys, depths):
    """对每个交付数据行，按深度找最近 band，赋地层"""
    nB = len(band_label)
    y0 = min(ys)
    y1 = max(ys)
    d0 = depths[0]
    d1 = depths[-1]
    if y1 == y0:
        return [band_label[0]] * len(depths)

    def band_depth(yc):
        return d0 + (yc - y0) / (y1 - y0) * (d1 - d0)

    per_row = []
    for dep in depths:
        if dep is None:
            per_row.append(None)
            continue
        # 找最近 band
        best = 0
        bd = 1e18
        for i in range(nB):
            dd = abs(band_depth(ys[i]) - dep)
            if dd < bd:
                bd = dd
                best = i
        per_row.append(band_label[best])
    return per_row


def delivery_blocks(ws):
    blocks = []
    cur = None
    r0 = None
    for r in range(2, ws.max_row + 1):
        v = ws.cell(r, 1).value
        if v not in (None, ''):
            if cur is not None:
                blocks.append((cur, r0, r - 1))
            cur = v
            r0 = r
    if cur is not None:
        blocks.append((cur, r0, ws.max_row))
    return blocks


def proposed_blocks(per_row):
    blocks = []
    cur = None
    r0 = None
    for i, lab in enumerate(per_row):
        r = i + 2
        if lab != cur:
            if cur is not None:
                blocks.append((cur, r0, r - 1))
            cur = lab
            r0 = r
    if cur is not None:
        blocks.append((cur, r0, r - 1))
    return blocks


def main():
    wb = openpyxl.load_workbook(F)
    print('=' * 100)
    for hole in wb.sheetnames:
        ws = wb[hole]
        bl = build_band_formation(hole)
        if bl is None:
            print(f'{hole:5}: [无法重建: 无 field_graph / 全空]')
            continue
        # 深度序列
        depths = []
        for r in range(2, ws.max_row + 1):
            depths.append(parse_depth(ws.cell(r, 3).value))
        # 用首尾已知深度配准；中间 None 用线性插值
        known = [(i, d) for i, d in enumerate(depths) if d is not None]
        if len(known) >= 2:
            idxs = [k[0] for k in known]
            vals = [k[1] for k in known]
            for i in range(len(depths)):
                if depths[i] is None:
                    pos = bisect(idxs, i)
                    if pos == 0:
                        depths[i] = vals[0]
                    elif pos == len(idxs):
                        depths[i] = vals[-1]
                    else:
                        a = known[pos - 1]
                        b = known[pos]
                        t = (i - a[0]) / (b[0] - a[0])
                        depths[i] = a[1] + t * (b[1] - a[1])
        ys = band_depths(hole)
        per_row = map_rows(hole, bl, ys, depths)
        cur_blk = delivery_blocks(ws)
        prop = proposed_blocks(per_row)
        cur_s = ' | '.join(f'{a}({b}-{c})' for a, b, c in cur_blk)
        prop_s = ' | '.join(f'{a}({b}-{c})' for a, b, c in prop)
        changed = cur_s != prop_s
        print(f'{hole:5} {"*** CHANGED ***" if changed else "ok":14} | 现: {cur_s}')
        if changed:
            print(f'{"":5} {"":14} | 拟: {prop_s}')
    print('=' * 100)


if __name__ == '__main__':
    main()
