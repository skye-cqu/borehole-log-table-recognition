
import json,hashlib,pathlib
p=pathlib.Path('runs/table_reconstruct/钻孔柱状图1015_表头映射.json')
d=json.loads(p.read_text(encoding='utf-8'))
base={}
for line in pathlib.Path('runs/tmp/baseline_表头映射_20261019.txt').read_text(encoding='utf-8-sig').splitlines():
    if not line.strip(): continue
    n,h=line.split(); base[n.strip()]=h.upper()
target=base['钻孔柱状图1015_表头映射.json']
print('target',target)
print('current keys',list(d.keys()))
# try adding notes as empty list at the position used by determine()
for notes_val in ([], None):
    e={}
    for k in ['image','band','sep_x_band','n_sep','columns','drop_columns','keep','warnings','notes','ok','header_src','label_verify','sep_pts']:
        e[k]=notes_val if k=='notes' else d[k]
    s=json.dumps(e,ensure_ascii=False,indent=1)
    h=hashlib.sha256(s.encode('utf-8')).hexdigest().upper()
    print('try notes=',notes_val,'->',h[:20],'MATCH' if h==target else '')
