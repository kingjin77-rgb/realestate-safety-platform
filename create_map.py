import sys, os, glob, json
sys.stdout.reconfigure(encoding='utf-8')
import geopandas as gpd
import folium
from folium import GeoJson, GeoJsonPopup, GeoJsonTooltip
import warnings
warnings.filterwarnings('ignore')

base = r'D:\지구단위계획구역_extract_temp'
region_map = {
    '11000':'서울','26000':'부산','27000':'대구','28000':'인천','29000':'광주',
    '30000':'대전','31000':'울산','36000':'세종','41000':'경기','43000':'충북',
    '44000':'충남','46000':'전남','47000':'경북','48000':'경남','50000':'제주',
    '51000':'강원','52000':'전북'
}

all_gdfs = []

for folder in sorted(glob.glob(os.path.join(base, '*'))):
    if not os.path.isdir(folder): continue
    dirname = os.path.basename(folder)
    parts = dirname.split('_')
    if len(parts) != 2: continue
    system, code = parts

    for shp_path in glob.glob(os.path.join(folder, '*UQ161.shp')):
        try:
            gdf = gpd.read_file(shp_path, encoding='cp949')
            gdf['system'] = system
            gdf['region'] = region_map.get(code, code)
            gdf['region_code'] = code
            all_gdfs.append(gdf)
            print(f'Loaded: {os.path.basename(shp_path)} ({len(gdf)} rows)')
        except Exception as e:
            print(f'ERROR: {shp_path} - {e}', file=sys.stderr)

print(f'\nTotal GeoDataFrames: {len(all_gdfs)}')
merged = gpd.pd.concat(all_gdfs, ignore_index=True)
print(f'Total features: {len(merged)}')
print(f'CRS: {merged.crs}')

# Convert to WGS84 (EPSG:4326)
merged = merged.to_crs(epsg=4326)
print(f'Converted to: {merged.crs}')

# Clean up columns for display
merged['area_m2'] = merged['dgm_ar'].apply(lambda x: round(float(x), 1) if x and str(x).strip() else 0)
merged['name'] = merged['alias'].fillna('').apply(lambda x: x.strip() if isinstance(x, str) else '')
merged['dgm_name'] = merged['dgm_nm'].fillna('').apply(lambda x: x.strip() if isinstance(x, str) else '')
merged['ntf'] = merged['ntfdate'].fillna('').apply(lambda x: x.strip() if isinstance(x, str) else '')

# Filter to named districts for cleaner map (or show all)
print(f'Named (alias): {len(merged[merged["name"] != ""])}')

# Create map centered on South Korea
m = folium.Map(location=[36.5, 127.8], zoom_start=7, tiles='CartoDB positron')

# Color by system
colors = {'KLIP': '#3388ff', 'UPIS': '#9933ff'}

for sys_name in ['KLIP', 'UPIS']:
    subset = merged[merged['system'] == sys_name].copy()
    if len(subset) == 0:
        continue

    # Simplify geometry for performance
    subset['geometry'] = subset['geometry'].simplify(0.001)

    # Create display label
    subset['display'] = subset.apply(
        lambda r: r['name'] if r['name'] else r['dgm_name'] if r['dgm_name'] else f"구역 ({r['region']})", axis=1
    )

    geojson = GeoJson(
        subset[['geometry', 'display', 'region', 'sgg_cd', 'area_m2', 'ntf', 'system']],
        name=sys_name,
        style_function=lambda x, c=colors[sys_name]: {
            'fillColor': c,
            'color': c,
            'weight': 1,
            'fillOpacity': 0.3,
        },
        tooltip=GeoJsonTooltip(
            fields=['display', 'region', 'area_m2', 'ntf'],
            aliases=['구역명', '시도', '면적(㎡)', '고시일'],
            sticky=True,
        ),
        popup=GeoJsonPopup(
            fields=['display', 'region', 'sgg_cd', 'area_m2', 'ntf', 'system'],
            aliases=['구역명', '시도', '시군구코드', '면적(㎡)', '고시일', '시스템'],
        ),
    )
    geojson.add_to(m)

folium.LayerControl().add_to(m)

output_path = r'D:\지구단위계획구역_전국지도.html'
m.save(output_path)
print(f'\nMap saved: {output_path}')
print(f'Features on map: {len(merged)}')
