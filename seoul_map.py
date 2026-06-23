import sys, os
sys.stdout.reconfigure(encoding='utf-8')
import geopandas as gpd
import folium
from folium import GeoJson, GeoJsonTooltip, GeoJsonPopup
import warnings
warnings.filterwarnings('ignore')

gdf = gpd.read_file(r'D:\지구단위계획구역_extract_temp\UPIS_11000\UPIS_C_UQ161.shp', encoding='cp949')
gdf = gdf.to_crs(epsg=4326)
print(f'Seoul: {len(gdf)} features')

gdf['display'] = gdf['DGM_NM'].fillna('구역').apply(lambda x: x.strip() if isinstance(x, str) else '구역')
gdf['area_m2'] = gdf['DGM_AR'].apply(lambda x: round(float(x), 1) if x else 0)

center = [37.5665, 126.978]
m = folium.Map(location=center, zoom_start=12, tiles='CartoDB positron')

folium.TileLayer(
    'https://mt1.google.com/vt/lyrs=s&x={x}&y={y}&z={z}',
    attr='Google', name='위성지도'
).add_to(m)
folium.TileLayer('OpenStreetMap', name='기본지도').add_to(m)

GeoJson(
    gdf[['geometry', 'display', 'area_m2', 'ATRB_SE']],
    name='서울 지구단위계획구역',
    style_function=lambda x: {
        'fillColor': '#FF5722',
        'color': '#D84315',
        'weight': 2,
        'fillOpacity': 0.4,
    },
    highlight_function=lambda x: {
        'weight': 4,
        'fillOpacity': 0.7,
        'color': '#FF0000',
    },
    tooltip=GeoJsonTooltip(
        fields=['display', 'area_m2'],
        aliases=['구역명', '면적(㎡)'],
        sticky=True,
        style='font-size:14px; font-weight:bold;'
    ),
    popup=GeoJsonPopup(
        fields=['display', 'area_m2', 'ATRB_SE'],
        aliases=['구역명', '면적(㎡)', '구역분류'],
    ),
).add_to(m)

folium.LayerControl(collapsed=False).add_to(m)

out = r'D:\지구단위계획구역_서울샘플.html'
m.save(out)
print(f'Saved: {out} ({os.path.getsize(out)/1024:.0f} KB)')
