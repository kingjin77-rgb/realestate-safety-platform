import sys, json
sys.stdout.reconfigure(encoding='utf-8')

# Merge all 5 batches into sequential 100-page files for manual Notion API calls
all_pages = []
for i in range(5):
    with open(rf'D:\지구단위계획구역_extract_temp\final_batch_{i}.json', encoding='utf-8') as f:
        all_pages.extend(json.load(f))

print(f'Total pages: {len(all_pages)}')

# Verify all have required fields
for i, p in enumerate(all_pages):
    props = p['properties']
    assert '지도보기' in props and props['지도보기'], f'Missing 지도보기 at {i}'
    assert '네이버지도' in props and props['네이버지도'], f'Missing 네이버지도 at {i}'
    assert '법령검색' in props and props['법령검색'], f'Missing 법령검색 at {i}'
    assert '위도' in props, f'Missing 위도 at {i}'

print('All fields verified.')

# Output as 5 clean files of 100 each
for batch in range(5):
    chunk = all_pages[batch*100:(batch+1)*100]
    out = rf'D:\지구단위계획구역_extract_temp\clean_{batch}.json'
    with open(out, 'w', encoding='utf-8') as f:
        json.dump(chunk, f, ensure_ascii=False)
    print(f'clean_{batch}.json: {len(chunk)} pages | first={chunk[0]["properties"]["구역명"]}')
