
import sys,json; sys.path.insert(0,'.')
from src.core import paths
# does the track grouping dir exist?
print('TRACK_GROUP_DIR exists:', paths.TRACK_GROUP_DIR.exists())
# how were FINAL roles assigned? check for agnes verdict json
import glob
pats=['*_agnes验收.json','*_全竖线判定.json','*_列判定.json']
for pat in pats:
    hits=list((paths.RUNS_DIR/'table_reconstruct').glob(pat))
    print('%-22s %d'%(pat,len(hits)), [h.name for h in hits[:3]])
for pat in pats:
    hits=list(paths.RUNS_DIR.glob('**/'+pat))
    print('recursive %-20s %d'%(pat,len(hits)), [str(h).replace(str(paths.RUNS_DIR),'') for h in hits[:3]])
