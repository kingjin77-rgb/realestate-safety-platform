import sys, os, glob, json
sys.stdout.reconfigure(encoding='utf-8')
from dbfread import DBF

base = r'D:\지구단위계획구역_extract_temp'
region_map = {
    '11000':'서울','26000':'부산','27000':'대구','28000':'인천','29000':'광주',
    '30000':'대전','31000':'울산','36000':'세종','41000':'경기','43000':'충북',
    '44000':'충남','46000':'전남','47000':'경북','48000':'경남','50000':'제주',
    '51000':'강원','52000':'전북'
}

named = 0
unnamed = 0
with_alias = 0
with_ntf = 0
sample_named = []

for folder in sorted(glob.glob(os.path.join(base, '*'))):
    if not os.path.isdir(folder): continue
    dirname = os.path.basename(folder)
    parts = dirname.split('_')
    if len(parts) != 2: continue
    system, code = parts

    for dbf_path in glob.glob(os.path.join(folder, '*UQ161.dbf')):
        try:
            db = DBF(dbf_path, encoding='cp949')
            for rec in db:
                nm = rec.get('dgm_nm', '').strip()
                al = rec.get('alias', '').strip()
                nt = rec.get('ntfdate', '').strip()
                ar = rec.get('dgm_ar', '').strip()
                sgg = rec.get('sgg_cd', '').strip()
                if nm:
                    named += 1
                    if len(sample_named) < 20:
                        sample_named.append({
                            'system': system, 'region': region_map.get(code, code),
                            'sgg_cd': sgg, 'dgm_nm': nm, 'alias': al,
                            'ntfdate': nt, 'dgm_ar': ar[:12]
                        })
                else:
                    unnamed += 1
                if al: with_alias += 1
                if nt: with_ntf += 1
        except Exception as e:
            print(f'ERROR: {dbf_path} - {e}', file=sys.stderr)

print(f'Named (dgm_nm): {named}')
print(f'Unnamed: {unnamed}')
print(f'With alias: {with_alias}')
print(f'With ntfdate: {with_ntf}')
print()
for s in sample_named:
    print(json.dumps(s, ensure_ascii=False))
