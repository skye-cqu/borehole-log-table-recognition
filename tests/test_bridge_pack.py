# -*- coding: utf-8 -*-
"""bridge_pack 两级寻址的合成用例(2026-11-05 几何寻址是 run9 的解锁点)。

全合成:seed 表头 ["岩性描述"],包索引按真实列位(1=行号,2=角色,4-6=读1-3,
7=现交付值)。验证:文本唯一>行号兜底、多义不桥、角色过滤、不可达跳过。
"""
from openpyxl import Workbook

from src.handwriting.bridge_pack import build_bridge


def _mk(tmp_path, seed_texts, pack_rows):
    sd = tmp_path / "seed"; sd.mkdir(exist_ok=True)
    wb = Workbook(); ws = wb.active
    ws.append(["岩性描述"])
    for t in seed_texts:
        ws.append([t])
    wb.save(sd / "钻孔柱状图9001_整合.xlsx")
    pd = tmp_path / "pack"; pd.mkdir(exist_ok=True)
    wb = Workbook(); ws = wb.active
    ws.append(["文件", "xlsx行", "角色", "程序原值", "读1", "读2", "读3",
               "现交付值", "核验类型", "核验结论"])
    for r in pack_rows:
        ws.append(list(r))
    wb.save(pd / "钻孔柱状图9001_核验索引.xlsx")
    return sd, pd


def test_text_unique_and_index_fallback(tmp_path):
    sd, pd = _mk(tmp_path,
                 ["泥岩灰", "砂岩白", "石灰岩青", "煤黑"],
                 [["r2.png", 2, "岩性描述", "原值", "读A", None, None,
                   "泥岩灰", "投票一致", "保持"],
                  ["r3.png", 3, "岩性描述", "原值", "读B", None, None,
                   "砂岩白", "投票一致", "保持"],
                  ["r9.png", 4, "岩性描述", "原值", "读C", None, None,
                   "不存在文本", "投票分歧", "留像素"]])
    bridge, s = build_bridge(pd, sd)
    b = bridge["钻孔柱状图9001"]
    assert b["行2"]["桥"] == "text"                    # 文本唯一优先
    assert b["行2"]["agnes"] == ["读A", None, None]     # (未锚)/空读→None
    assert b["行4"]["桥"] == "index"                   # 文本不匹配→行号兜底
    assert s["text"] == 2 and s["index"] == 1


def test_multi_never_bridged_even_by_index(tmp_path):
    """文本多义直接跳过(不落到行号兜底):多义=文本证据本身有歧义。"""
    sd, pd = _mk(tmp_path, ["泥岩灰", "泥岩灰", "砂岩白"],
                 [["行4.png", 4, "岩性描述", "", "读A", None, None, "泥岩灰",
                   "", ""]])
    bridge, s = build_bridge(pd, sd)
    assert bridge == {} and s["multi"] == 1


def test_role_filter_and_unreachable(tmp_path):
    sd, pd = _mk(tmp_path, ["泥岩灰"],
                 [["r1.png", 2, "倾角", "", "x", None, None, "泥岩灰", "", ""],
                  ["r2.png", 99, "岩性描述", "", "x", None, None, "任意", "", ""],
                  ["r3.png", 2, "岩性描述", "", "x", None, None, "", "", ""]])
    bridge, s = build_bridge(pd, sd)
    assert bridge == {}
    assert s["tot"] == 1 and s["skip"] == 1            # 角色过滤与空交付值先于计数;
                                                       # 仅越界行计入 skip


def test_index_fallback_requires_seed_desc_nonempty(tmp_path):
    """行号兜底还要求 seed 该行描述非空(否则坐标不可用)。"""
    sd, pd = _mk(tmp_path, ["泥岩灰", None],
                 [["r1.png", 3, "岩性描述", "", "x", None, None, "不存在", "", ""]])
    bridge, s = build_bridge(pd, sd)
    assert bridge == {} and s["skip"] == 1
