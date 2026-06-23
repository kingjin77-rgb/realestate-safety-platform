import sys, json
sys.stdout.reconfigure(encoding='utf-8')

with open(r'D:\지구단위계획구역_extract_temp\named_districts.json', encoding='utf-8') as f:
    data = json.load(f)

# Sort by area descending, take top 500
data.sort(key=lambda x: -x['area_m2'])
top = data[:500]

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
                '구역명': d['alias'][:80] if d['alias'] else d['dgm_nm'][:50],
                '시스템': d['system'],
                '시도': d['region'],
                '시군구코드': d['sgg_cd'],
                '유형': d['dgm_nm'][:50],
                '면적(㎡)': d['area_m2'],
                '고시일': ntf,
                '구역분류': d['atrb_se'],
            }
        })

    outpath = rf'D:\지구단위계획구역_extract_temp\batch_detail_{batch_idx}.json'
    with open(outpath, 'w', encoding='utf-8') as f:
        json.dump(pages, f, ensure_ascii=False)
    print(f'Batch {batch_idx}: {len(pages)} pages -> {outpath}')
