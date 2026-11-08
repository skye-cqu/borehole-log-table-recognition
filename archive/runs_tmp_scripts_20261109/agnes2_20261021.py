
import sys,json; sys.path.insert(0,'.')
from src.core import paths
D=paths.RUNS_DIR/'table_reconstruct'
stem='钻孔柱状图1023'
d=json.loads((D/f'{stem}_全竖线判定.json').read_text(encoding='utf-8'))
print('n_tracks',d['n_tracks'],'n_visible',d['n_visible'])
print('track_nos sep:',d['track_nos']['sep'])
print('track_nos other:',d['track_nos']['other'])
print('merged_by_track:',d['merged_by_track'])
print('columns_gidx:',d['columns_gidx'])
print()
print('=> LLM 只看了',d['n_visible'],'条(可见的), 而 total tracks =',d['n_tracks'])
print('=> 也就是说 gidx 是"全部track"的序号, 但只有 n_visible 条被送进 LLM')
