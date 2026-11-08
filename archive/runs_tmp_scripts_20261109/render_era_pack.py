"""项② 视觉门禁包: 时代列西延逐行 1:1 裁片拼图(30 张)。

每图一张拼图: era 行的 [西延后西端-40px, c0+90px] × [y±80px] 裁片竖排,
红线 = 西延后折线(新), 蓝线 = 基线(v9)数值区折线 —— 对照西延段的走向。
判读口径: 助手渲染供用户核验, 不作"正确"结论依据。
输出 runs/tmp/era视觉包_20261001/{stem}_时代行拼图.png + 汇总 stdout。
"""
import sys, json, warnings, glob, os
warnings.filterwarnings("ignore")
sys.path.insert(0, ".")
import numpy as np
import cv2
from src.core import paths
from src.table import track_rows as tr

OUT = paths.RUNS_DIR / "tmp" / "era视觉包_20261001"
BAK = paths.PROJECT_ROOT / "rollback" / "era_ext_行判定_备份_20261001"


def montage(stem):
    new = json.loads((paths.RUNS_DIR / "table_reconstruct" / f"{stem}_行判定.json")
                     .read_text(encoding="utf-8"))
    old = json.loads((BAK / f"{stem}_行判定.json").read_text(encoding="utf-8"))
    eras = [r for r in new["rows"] if r.get("era")]
    fp = paths.RUNS_DIR / "table_reconstruct" / f"{stem}_列结构定稿.json"
    fr = tr.table_frame(stem)
    nf = sum(1 for r in eras if r.get("era") == "full")
    npart = sum(1 for r in eras if r.get("era") == "partial")
    head = f"{stem}  rows={len(new['rows'])} full={nf} partial={npart}"
    if not eras or fr is None or not fp.exists():
        return head, None
    c0 = float(json.loads(fp.read_text(encoding="utf-8"))["columns"][0]["x_at_mid"])
    gray = cv2.imread(str(paths.RAW_DIR / f"{stem}.JPG"), cv2.IMREAD_GRAYSCALE)
    viz = cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)
    for r in old["rows"]:
        tr._draw_poly(viz, r["poly"], (255, 80, 0), 2)      # 基线全量蓝线
    viz2 = viz.copy()
    for r in eras:
        tr._draw_poly(viz2, r["poly"], (0, 0, 255), 3)      # 新 era 行红线
    crops = []
    for r in eras:
        y = int(r["y_at_mid"])
        c = viz2[max(y - 80, 0):y + 80, max(int(r["x"][0]) - 40, 0):int(c0) + 90]
        if c.size:
            tag = f"y={r['y_at_mid']} {r['era']} d_frame={r['era_d_frame']}"
            cv2.putText(c, tag, (8, 24), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 120, 0), 2)
            crops.append(c)
            crops.append(np.full((6, c.shape[1], 3), 60, np.uint8))
    if not crops:
        return head, None
    w = max(c.shape[1] for c in crops)
    crops = [np.pad(c, ((0, 0), (0, w - c.shape[1]), (0, 0)), constant_values=255)
             for c in crops]
    m = np.vstack(crops[:-1])
    cv2.putText(m, head, (10, m.shape[0] - 12), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 0, 0), 2)
    fp_out = OUT / f"{stem}_时代行拼图.png"
    cv2.imwrite(str(fp_out), m)
    return head, fp_out


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    for f in sorted(glob.glob(str(BAK / "钻孔柱状图*_行判定.json"))):
        stem = os.path.basename(f)[:-9]
        head, p = montage(stem)
        print(head, "->", p.name if p else "(无拼图)")
    print("\n判读: 红线=西延后 era 行, 蓝线=基线全部行; 西延段应沿时代列内的真实横线墨迹。")
