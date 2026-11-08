# -*- coding: utf-8 -*-
"""值级规则引擎:对整理表 xlsx 做逐格取值修正(数据集无关核心)。

规则 = Rule(name, roles, fn, note):
  name   规则名(账目/清单按此归组)
  roles  适配的列角色名集合;None=所有列
  fn(v, ctx) -> 新值 | None    None=不修改。v=格值(原样),ctx =
              {"stem", "role", "row", "col", "rowvals"}
约束:只改值,不增删行列;fn 必须纯函数(同输入同输出);
     禁止"抄参考表"式规则——取值只能由图上证据/多读一致/数字自洽驱动。
角色解析由调用方注入(resolve_roles(header)->{角色:列号}),引擎不知道任何具体表头。
"""
from dataclasses import dataclass
from typing import Callable, Optional


@dataclass(frozen=True)
class Rule:
    name: str
    roles: Optional[frozenset]
    fn: Callable
    note: str = ""


def value_of(v):
    """格值→比对口径字符串(CellRichText/数字/None 统一成 str)。"""
    return "" if v is None else str(v)


def apply_to_workbook(wb_path, rules, resolve_roles, stem=""):
    """对单个 xlsx 应用规则并保存,返回账目列表。

    账目条目 = {"图","行","列","角色","规则","旧","新"}。不增删行列。
    """
    from openpyxl import load_workbook
    from openpyxl.cell.cell import MergedCell
    wb = load_workbook(wb_path, rich_text=True)
    ws = wb.active
    grid = list(ws.iter_rows())
    if not grid:
        return []
    roles = resolve_roles([c.value for c in grid[0]])   # {角色: 列号}
    idx_role = {c: r for r, c in roles.items()}
    allvals = [[c.value for c in row] for row in grid]  # 应用起点快照(跨行门用)
    ledger = []
    for r_i, row in enumerate(grid[1:], start=2):
        rowvals = [c.value for c in row]
        for c_i, cell in enumerate(row):
            role = idx_role.get(c_i)
            if role is None or isinstance(cell, MergedCell):
                continue              # rowspan 非锚格:图纸面就是空格,禁写(保真)
            old = cell.value
            new = old
            for rule in rules:
                if rule.roles is not None and role not in rule.roles:
                    continue
                ctx = {"stem": stem, "role": role, "row": r_i,
                       "col": c_i, "rowvals": rowvals,
                       "rows": allvals, "r_idx": r_i - 1,
                       "role_col": roles}
                out = rule.fn(new, ctx)
                if out is None or value_of(out) == value_of(new):
                    continue
                new = out
                ledger.append({"图": stem, "行": r_i, "列": c_i + 1,
                               "角色": role, "规则": rule.name,
                               "旧": value_of(old)[:80], "新": value_of(new)[:80]})
            if new is not old and value_of(new) != value_of(old):
                cell.value = new
    wb.save(wb_path)
    return ledger
