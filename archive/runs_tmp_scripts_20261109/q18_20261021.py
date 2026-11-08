
# -*- coding: utf-8 -*-
"""A/B 两线身份: 看 柱状列(848..?) 与 岩性描述 的相对关系, 原图放大。"""
import sys,json; sys.path.insert(0,'.')
import numpy as np, cv2
from src.core import paths
stem='钻孔柱状图1023'
D=paths.RUNS_DIR/'table_reconstruct'
OUT=paths.RUNS_DIR/'tmp'/'col_crop_20261021'
gray=cv2.imread(str(paths.RAW_DIR/f'{stem}.JPG'),cv2.IMREAD_GRAYSCALE)
H,W=gray.shape
def crop(y0,y1,x0,x1,name,sc):
    sub=cv2.cvtColor(gray[y0:y1,x0:x1],cv2.COLOR_GRAY2BGR)
    big=cv2.resize(sub,None,fx=sc,fy=sc,interpolation=cv2.INTER_NEAREST)
    cv2.imwrite(str(OUT/name),big); print(name,big.shape)
# 9400..9600 x 800..1200: 真厚|柱状|岩性描述 三格
crop(9400,9620,800,1200,'d1_row_full.png',3)
# 只放大两线: x 1010..1140, y 9400..9620
crop(9400,9620,1010,1140,'d2_two_lines.png',8)
# 表头处: y 540..760, x 820..1200
crop(540,760,820,1200,'d3_header.png',3)

