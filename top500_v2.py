import sys, json
sys.stdout.reconfigure(encoding='utf-8')

with open(r'D:\지구단위계획구역_extract_temp\named_districts.json', encoding='utf-8') as f:
    data = json.load(f)

# Filter out generic/subdivision names
GENERIC = {'단독주택용지', '공동주택용지', '종교용지', '주거용지', '상업용지',
           '기타용지', '공공시설용지', '녹지', '도로', '주차장', '공원',
           '학교용지', '체육시설용지', '공공청사용지'}

filtered = []
seen = set()
for d in data:
    alias = d['alias'].strip()
    if not alias or alias in GENERIC:
        continue
    # Dedup key: alias + sgg_cd + rounded area
    key = (alias, d['sgg_cd'], round(d['area_m2'], 0))
    if key in seen:
        continue
    seen.add(key)
    filtered.append(d)

filtered.sort(key=lambda x: -x['area_m2'])
print(f'After filter+dedup: {len(filtered)} (from {len(data)})')

# Take top 500
top = filtered[:500]
print(f'Top 500 range: {top[0]["area_m2"]:.0f} ~ {top[-1]["area_m2"]:.0f} m2')

# Show sample
for d in top[:5]:
    print(f'  {d["alias"][:40]:40s} | {d["region"]:4s} | {d["area_m2"]:>12,.0f} m2')

# Split into batches of 100
for batch_idx in range(5):
    batch = top[batch_idx*100:(batch_idx+1)*100]
    pages = []
    for d in batch:
        ntf = d['ntfdate']
        if ntf and len(ntf) == 8:
            ntf = f"{ntf[:4]}-{ntf[4:6]}-{ntf[6:8]}"
        pages.append({
            'properties': {
                '구역명': d['alias'][:80],
                '시스템': d['system'],
                '시도': d['region'],
                '시군구코드': d['sgg_cd'],
                '유형': d['dgm_nm'][:50],
                '면적(㎡)': d['area_m2'],
                '고시일': ntf,
                '구역분류': d['atrb_se'],
            }
        })
    outpath = rf'D:\지구단위계획구역_extract_temp\batch_v2_{batch_idx}.json'
    with open(outpath, 'w', encoding='utf-8') as f:
        json.dump(pages, f, ensure_ascii=False)
    print(f'Batch {batch_idx}: {len(pages)} pages')
