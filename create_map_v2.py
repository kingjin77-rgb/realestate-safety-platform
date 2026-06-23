import sys, os, glob
sys.stdout.reconfigure(encoding='utf-8')
import geopandas as gpd
import folium
from folium import GeoJson, GeoJsonPopup, GeoJsonTooltip
from folium.plugins import MarkerCluster
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
            all_gdfs.append(gdf)
            print(f'Loaded: {system}_{code} ({len(gdf)} rows)')
        except Exception as e:
            print(f'ERROR: {shp_path} - {e}', file=sys.stderr)

merged = gpd.pd.concat(all_gdfs, ignore_index=True)
merged = merged.to_crs(epsg=4326)
print(f'Total: {len(merged)} features, CRS: {merged.crs}')

# Clean columns
merged['area_m2'] = merged['dgm_ar'].apply(lambda x: round(float(x), 1) if x and str(x).strip() else 0)
merged['name'] = merged['alias'].fillna('').apply(lambda x: x.strip() if isinstance(x, str) else '')
merged['dgm_name'] = merged['dgm_nm'].fillna('').apply(lambda x: x.strip() if isinstance(x, str) else '')
merged['ntf'] = merged['ntfdate'].fillna('').apply(lambda x: x.strip() if isinstance(x, str) else '')
merged['display'] = merged.apply(
    lambda r: r['name'] if r['name'] else r['dgm_name'] if r['dgm_name'] else f"구역 ({r['region']})", axis=1
)
merged['sgg'] = merged['sgg_cd'].fillna('').apply(lambda x: x.strip() if isinstance(x, str) else '')

# Create map
m = folium.Map(location=[36.5, 127.8], zoom_start=7, tiles='CartoDB positron')

# Add satellite tile option
folium.TileLayer('https://mt1.google.com/vt/lyrs=s&x={x}&y={y}&z={z}',
    attr='Google', name='위성지도').add_to(m)
folium.TileLayer('OpenStreetMap', name='기본지도').add_to(m)

colors = {'KLIP': '#2196F3', 'UPIS': '#9C27B0'}

for sys_name in ['KLIP', 'UPIS']:
    subset = merged[merged['system'] == sys_name].copy()
    if len(subset) == 0:
        continue

    # Lighter simplify for better accuracy (0.0002 ≈ ~22m)
    subset['geometry'] = subset['geometry'].simplify(0.0002)

    cols = ['geometry', 'display', 'region', 'sgg', 'area_m2', 'ntf', 'system']
    geojson = GeoJson(
        subset[cols],
        name=f'{sys_name} 구역경계',
        style_function=lambda x, c=colors[sys_name]: {
            'fillColor': c,
            'color': c,
            'weight': 1.5,
            'fillOpacity': 0.35,
        },
        highlight_function=lambda x: {
            'weight': 3,
            'fillOpacity': 0.6,
        },
        tooltip=GeoJsonTooltip(
            fields=['display', 'region', 'area_m2', 'ntf'],
            aliases=['구역명', '시도', '면적(㎡)', '고시일'],
            sticky=True,
            style='font-size:13px;'
        ),
        popup=GeoJsonPopup(
            fields=['display', 'region', 'sgg', 'area_m2', 'ntf', 'system'],
            aliases=['구역명', '시도', '시군구코드', '면적(㎡)', '고시일', '시스템'],
        ),
    )
    geojson.add_to(m)

# Add marker cluster for named districts (centroid markers)
named = merged[merged['name'] != ''].copy()
named['centroid'] = named.geometry.centroid
print(f'Adding {len(named)} named district markers')

mc = MarkerCluster(name='구역명 마커', show=True)
for _, row in named.iterrows():
    c = row['centroid']
    folium.CircleMarker(
        location=[c.y, c.x],
        radius=4,
        color=colors.get(row['system'], '#333'),
        fill=True,
        fill_opacity=0.7,
        popup=f"<b>{row['display']}</b><br>{row['region']} ({row['sgg']})<br>면적: {row['area_m2']:,.0f}㎡<br>고시일: {row['ntf'] or '-'}",
        tooltip=row['display'],
    ).add_to(mc)
mc.add_to(m)

folium.LayerControl(collapsed=False).add_to(m)

output = r'D:\지구단위계획구역_전국지도_v2.html'
m.save(output)
print(f'\nSaved: {output}')
sz = os.path.getsize(output) / 1024 / 1024
print(f'Size: {sz:.1f} MB')
