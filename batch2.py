import sys, json
sys.stdout.reconfigure(encoding='utf-8')
with open(r'D:\지구단위계획구역_extract_temp\sgg_summary.json', encoding='utf-8') as f:
    data = json.load(f)
valid = [d for d in data if d['sgg_cd']]
valid.sort(key=lambda x: -x['count'])
batch2 = []
for d in valid[100:]:
    batch2.append({
        'properties': {
            '시군구코드': d['sgg_cd'],
            '시스템': d['system'],
            '시도': d['region'],
            '구역수': d['count'],
            '총면적(㎡)': d['total_area_m2'],
        }
    })
print(json.dumps(batch2, ensure_ascii=False))
