# -*- coding: utf-8 -*-
"""像素核验包 → seed 行桥接(证据坐标转换)。

像素包(20261029)的行号是交付表行;本器把包行映射到 seed 行,产出 pack_bridge.json:
    {stem: {"行<seed_row>": {"agnes": [读1,读2,读3], "交付": 现交付值, "桥": "text"|"index"}}}
寻址两级:①"现交付值文本在 seed 描述列唯一出现"(最高精度);
②索引兜底——交付表与 seed 行号实测 99.8% 一致(1435/1438),文本匹配不到的行
按行号看。桥接只定"往哪看"的坐标,采纳仍由收敛门仲裁,坐标错最多浪费一次复读。

CLI: python src/handwriting/bridge_pack.py
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.core import paths
from src.handwriting.normalizers import norm_text


def build_bridge(pack_dir, seed_dir):
    """包目录+seed目录 → (bridge, 统计)。桥接只定"往哪看"的坐标,不定值。

    寻址两级:①现交付值文本在 seed 描述列唯一出现(最高精度);
    ②行号兜底(交付表↔seed 行号实测 99.8% 一致);多义/不可达不桥。
    """
    from openpyxl import load_workbook
    from src.table.finalize_tables import column_roles
    bridge = {}
    stats = {"tot": 0, "text": 0, "multi": 0, "index": 0, "skip": 0}
    for fp in sorted(Path(pack_dir).glob("*_核验索引.xlsx")):
        stem = fp.name.split("钻孔柱状图")[1][:4]
        wb = load_workbook(Path(seed_dir) / f"钻孔柱状图{stem}_整合.xlsx",
                           read_only=True)
        srows = list(wb.active.iter_rows(values_only=True))
        wb.close()
        dc = column_roles(srows[0])["desc"]
        texts = {}
        for i, r in enumerate(srows[1:], start=2):
            t = norm_text(r[dc])
            if t:
                texts.setdefault(t, []).append(i)
        idx = load_workbook(fp, read_only=True)
        rows = list(idx.active.iter_rows(values_only=True))[1:]
        idx.close()
        for r in rows:
            if str(r[2] or "").strip() != "岩性描述":
                continue
            cur = norm_text(r[7])
            if not cur:
                continue
            stats["tot"] += 1
            agnes = [str(r[i]) if r[i] is not None and str(r[i]).strip()
                     and str(r[i]) != "(未锚)" else None for i in (4, 5, 6)]
            entry = {"agnes": agnes, "交付": str(r[7] or "")}
            hits = texts.get(cur, [])
            if len(hits) == 1:                     # 文本唯一匹配(最高精度)
                stats["text"] += 1
                bridge.setdefault(f"钻孔柱状图{stem}", {})[f"行{hits[0]}"] = \
                    {**entry, "桥": "text"}
                continue
            if len(hits) > 1:
                stats["multi"] += 1
                continue
            # 行号兜底寻址:交付表与 seed 行号 99.8% 一致(2026-11-05 实测
            # 1435/1438),文本匹配失败的行按索引看,桥接只定坐标不定值
            dr = int(r[1])
            if 2 <= dr <= len(srows) and norm_text(srows[dr - 1][dc]):
                stats["index"] += 1
                bridge.setdefault(f"钻孔柱状图{stem}", {})[f"行{dr}"] = \
                    {**entry, "桥": "index"}
            else:
                stats["skip"] += 1
    return bridge, stats


def main():
    pack = paths.PROJECT_ROOT / "outputs/Agnes像素核验包_20261029"
    bridge, s = build_bridge(pack, paths.AUTORESEARCH_SEED_DIR)
    out = paths.AUTORESEARCH_DIR / "pack_bridge.json"
    out.write_text(json.dumps(bridge, ensure_ascii=False, indent=1),
                   encoding="utf-8")
    print(f"包行{s['tot']} 文本唯一{s['text']} 多义{s['multi']} "
          f"索引兜底{s['index']} 索引也不可达{s['skip']} → {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
