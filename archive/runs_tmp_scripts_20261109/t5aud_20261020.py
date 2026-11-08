
import sys,json,csv; sys.path.insert(0,'.')
from src.core import paths
p=paths.TMP_DIR/'时代列门禁_20261010.json'
d=json.loads(p.read_text(encoding='utf-8'))
print('top keys',list(d.keys())[:20] if isinstance(d,dict) else type(d))
