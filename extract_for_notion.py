import sys, os, glob, json
sys.stdout.reconfigure(encoding='utf-8')
from dbfread import DBF
from collections import defaultdict

base = r'D:\지구단위계획구역_extract_temp'
region_map = {
    '11000':'서울','26000':'부산','27000':'대구','28000':'인천','29000':'광주',
    '30000':'대전','31000':'울산','36000':'세종','41000':'경기','43000':'충북',
    '44000':'충남','46000':'전남','47000':'경북','48000':'경남','50000':'제주',
    '51000':'강원','52000':'전북'
}

# sgg_cd -> region mapping (first 2 digits)
sgg_to_region = {}
for code, name in region_map.items():
    sgg_to_region[code[:2]] = name

# Aggregate by sgg_cd
sgg_stats = defaultdict(lambda: {'count': 0, 'total_area': 0.0, 'named': 0, 'system': '', 'region': ''})
# Collect named districts (with alias)
named_districts = []

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
                ar_str = rec.get('dgm_ar', '').strip()
                sgg = rec.get('sgg_cd', '').strip()
                atrb = rec.get('atrb_se', '').strip()

                try:
                    area = float(ar_str)
                except:
                    area = 0.0

                region = region_map.get(code, '')
                s = sgg_stats[sgg]
                s['count'] += 1
                s['total_area'] += area
                s['system'] = system
                s['region'] = region

                if al:
                    named_districts.append({
                        'system': system,
                        'region': region,
                        'sgg_cd': sgg,
                        'dgm_nm': nm[:50],
                        'alias': al[:80],
                        'ntfdate': nt,
                        'area_m2': round(area, 1),
                        'atrb_se': atrb,
                    })
        except Exception as e:
            print(f'ERROR: {dbf_path} - {e}', file=sys.stderr)

# Output 1: sgg summary
print('=== SGG SUMMARY ===')
print(json.dumps({
    'count': len(sgg_stats),
    'sample': {k: v for i, (k, v) in enumerate(sorted(sgg_stats.items())) if i < 5}
}, ensure_ascii=False))

# Output 2: named districts count
print(f'\n=== NAMED DISTRICTS: {len(named_districts)} ===')
print(f'Sample:')
for d in named_districts[:5]:
    print(json.dumps(d, ensure_ascii=False))

# Save full data as JSON
with open(r'D:\지구단위계획구역_extract_temp\sgg_summary.json', 'w', encoding='utf-8') as f:
    summary_list = []
    for sgg, stats in sorted(sgg_stats.items()):
        summary_list.append({
            'sgg_cd': sgg,
            'system': stats['system'],
            'region': stats['region'],
            'count': stats['count'],
            'total_area_m2': round(stats['total_area'], 1),
        })
    json.dump(summary_list, f, ensure_ascii=False, indent=2)

with open(r'D:\지구단위계획구역_extract_temp\named_districts.json', 'w', encoding='utf-8') as f:
    json.dump(named_districts, f, ensure_ascii=False, indent=2)

print(f'\nSaved: sgg_summary.json ({len(sgg_stats)} entries)')
print(f'Saved: named_districts.json ({len(named_districts)} entries)')
