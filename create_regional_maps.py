import sys, os, glob
sys.stdout.reconfigure(encoding='utf-8')
import geopandas as gpd
import folium
from folium import GeoJson, GeoJsonTooltip, GeoJsonPopup
import warnings
warnings.filterwarnings('ignore')

base = r'D:\지구단위계획구역_extract_temp'
out_dir = r'D:\지구단위계획구역_지도'
os.makedirs(out_dir, exist_ok=True)

region_map = {
    '11000':'서울','26000':'부산','27000':'대구','28000':'인천','29000':'광주',
    '30000':'대전','31000':'울산','36000':'세종','41000':'경기','43000':'충북',
    '44000':'충남','46000':'전남','47000':'경북','48000':'경남','50000':'제주',
    '51000':'강원','52000':'전북'
}

for folder in sorted(glob.glob(os.path.join(base, '*'))):
    if not os.path.isdir(folder): continue
    dirname = os.path.basename(folder)
    parts = dirname.split('_')
    if len(parts) != 2: continue
    system, code = parts
    region = region_map.get(code, code)

    for shp_path in glob.glob(os.path.join(folder, '*UQ161.shp')):
        try:
            gdf = gpd.read_file(shp_path, encoding='cp949')
            gdf.columns = [c.lower() for c in gdf.columns]
            gdf = gdf.to_crs(epsg=4326)

            def safe(v):
                if v is None or (isinstance(v, float) and str(v) == 'nan'):
                    return ''
                return str(v).strip()

            gdf['display'] = gdf.apply(lambda r:
                safe(r.get('alias')) or safe(r.get('dgm_nm')) or '구역', axis=1)
            gdf['area_m2'] = gdf['dgm_ar'].apply(lambda x: round(float(x),1) if x and safe(x) else 0)
            gdf['ntf'] = gdf.apply(lambda r: safe(r.get('ntfdate', r.get('ntfc_sn', ''))), axis=1)
            gdf['sgg'] = gdf.apply(lambda r: safe(r.get('sgg_cd', r.get('signgu_se', ''))), axis=1)
            gdf['atrb'] = gdf['atrb_se'].apply(safe)

            center_y = gdf.geometry.centroid.y.mean()
            center_x = gdf.geometry.centroid.x.mean()

            m = folium.Map(location=[center_y, center_x], zoom_start=11, tiles='CartoDB positron')
            folium.TileLayer('https://mt1.google.com/vt/lyrs=s&x={x}&y={y}&z={z}',
                attr='Google', name='위성지도').add_to(m)
            folium.TileLayer('OpenStreetMap', name='기본지도').add_to(m)

            color = '#2196F3' if system == 'KLIP' else '#9C27B0'

            GeoJson(
                gdf[['geometry', 'display', 'area_m2', 'ntf', 'sgg', 'atrb']],
                name=f'{region} 지구단위계획구역 ({system})',
                style_function=lambda x, c=color: {
                    'fillColor': c, 'color': c, 'weight': 2, 'fillOpacity': 0.4,
                },
                highlight_function=lambda x: {
                    'weight': 4, 'fillOpacity': 0.7, 'color': '#FF0000',
                },
                tooltip=GeoJsonTooltip(
                    fields=['display', 'area_m2', 'ntf'],
                    aliases=['구역명', '면적(㎡)', '고시일'],
                    sticky=True,
                    style='font-size:14px; font-weight:bold;'
                ),
                popup=GeoJsonPopup(
                    fields=['display', 'sgg', 'area_m2', 'ntf', 'atrb'],
                    aliases=['구역명', '시군구코드', '면적(㎡)', '고시일', '구역분류'],
                ),
            ).add_to(m)

            folium.LayerControl(collapsed=False).add_to(m)

            fname = f'{region}_{system}.html'
            fpath = os.path.join(out_dir, fname)
            m.save(fpath)
            sz = os.path.getsize(fpath) / 1024
            print(f'{fname:20s} | {len(gdf):5d}건 | {sz:8.0f} KB')

        except Exception as e:
            print(f'ERROR: {folder} - {e}', file=sys.stderr)

print(f'\nAll maps saved to: {out_dir}')
