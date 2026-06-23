import sys, json
from urllib.parse import quote
sys.stdout.reconfigure(encoding='utf-8')

with open(r'D:\지구단위계획구역_extract_temp\named_with_did.json', encoding='utf-8') as f:
    all_data = json.load(f)

GENERIC = {'단독주택용지', '공동주택용지', '종교용지', '주거용지', '상업용지',
           '기타용지', '공공시설용지', '녹지', '도로', '주차장', '공원',
           '학교용지', '체육시설용지', '공공청사용지', '체육시설용지(골프코스)',
           '체육시설용지(클럽하우스)', '체육시설용지(연습그린)', '체육시설용지(휴게소)',
           '기반시설용지(진입도로)', '기반시설용지(저류지)', '기반시설용지(주차장)',
           '기반시설용지(커트도로)', '원지형보전녹지', '관광숙박', '업무시설용지',
           '제조시설용지', '체육시설용지(창고관리동)'}

filtered = []
seen = set()
for d in all_data:
    name = d['display']
    if not name or name in GENERIC or name in ('구역', ''):
        continue
    key = (name, d['sgg'], round(d['area']))
    if key in seen:
        continue
    seen.add(key)
    filtered.append(d)

filtered.sort(key=lambda x: -x['area'])
top = filtered[:500]

for batch_idx in range(5):
    batch = top[batch_idx*100:(batch_idx+1)*100]
    pages = []
    for d in batch:
        ntf = d.get('ntf', '')
        if ntf and len(ntf) == 8:
            ntf = f"{ntf[:4]}-{ntf[4:6]}-{ntf[6:8]}"

        name = d['display'][:80]
        lat = d['lat']
        lng = d['lng']
        region = d['region']

        gmap = f"https://www.google.com/maps/@{lat},{lng},16z/data=!3m1!1e1"
        naver = f"https://map.naver.com/v5/search/{quote(name + ' ' + region)}"
        eum = f"https://www.eum.go.kr/web/ar/lu/luLandDevelopSearch.jsp"
        law = f"https://www.law.go.kr/DRF/lawSearch.do?target=admr&type=HTML&query={quote(name + ' 지구단위계획')}"

        pages.append({
            'properties': {
                '구역명': name,
                '시스템': d['system'],
                '시도': region,
                '시군구코드': d['sgg'],
                '유형': d.get('atrb', ''),
                '면적(㎡)': d['area'],
                '고시일': ntf,
                '구역분류': d.get('atrb', ''),
                '위도': round(lat, 6),
                '경도': round(lng, 6),
                '지도보기': gmap,
                '토지이음': eum,
                '법령검색': law,
                '네이버지도': naver,
            }
        })

    outpath = rf'D:\지구단위계획구역_extract_temp\final_batch_{batch_idx}.json'
    with open(outpath, 'w', encoding='utf-8') as f:
        json.dump(pages, f, ensure_ascii=False)

    p = pages[0]['properties']
    print(f'Batch {batch_idx}: {len(pages)}건 | {p["구역명"]}')

print('Done. 5 batches ready.')
