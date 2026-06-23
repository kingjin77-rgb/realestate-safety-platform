import sys, json
sys.stdout.reconfigure(encoding='utf-8')

for i in range(1, 5):
    path = rf'D:\지구단위계획구역_extract_temp\batch_v2_{i}.json'
    with open(path, encoding='utf-8') as f:
        data = json.load(f)

    outpath = rf'D:\지구단위계획구역_extract_temp\batch_v2_{i}_ready.json'
    with open(outpath, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False)

    print(f'Batch {i}: {len(data)} pages ready at {outpath}')
    # Print first entry for verification
    p = data[0]['properties']
    print(f'  First: {p["구역명"]} | {p["시도"]} | {p["면적(㎡)"]:,.0f} m2')
