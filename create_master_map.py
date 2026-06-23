import sys, os, glob, json
sys.stdout.reconfigure(encoding='utf-8')
import geopandas as gpd
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
            # Normalize column names (UPIS has uppercase)
            gdf.columns = [c.lower() for c in gdf.columns]
            gdf['system'] = system
            gdf['region'] = region_map.get(code, code)
            gdf['region_code'] = code
            all_gdfs.append(gdf)
            print(f'Loaded: {system}_{code} ({len(gdf)})')
        except Exception as e:
            print(f'ERROR: {e}', file=sys.stderr)

merged = gpd.pd.concat(all_gdfs, ignore_index=True)
merged = merged.to_crs(epsg=4326)
print(f'Total: {len(merged)}')

# Normalize fields
def safe_str(v):
    if v is None or (isinstance(v, float) and str(v) == 'nan'):
        return ''
    return str(v).strip()

merged['alias_clean'] = merged.get('alias', gpd.pd.Series([''] * len(merged))).apply(safe_str)
merged['dgm_name'] = merged['dgm_nm'].apply(safe_str)
merged['name'] = merged.apply(lambda r: r['alias_clean'] if r['alias_clean'] else r['dgm_name'], axis=1)
merged['area'] = merged['dgm_ar'].apply(lambda x: round(float(x),1) if x and safe_str(x) else 0)
sgg_col = 'sgg_cd' if 'sgg_cd' in merged.columns else 'signgu_se'
merged['sgg'] = merged[sgg_col].apply(safe_str)
ntf_col = 'ntfdate' if 'ntfdate' in merged.columns else 'ntfc_sn'
merged['ntf'] = merged[ntf_col].apply(lambda x: safe_str(x)[:10]) if ntf_col in merged.columns else ''
merged['atrb'] = merged['atrb_se'].apply(safe_str)

# Display name
merged['display'] = merged.apply(lambda r:
    r['name'] if r['name'] else r['dgm_name'] if r['dgm_name'] else f"구역({r['region']})", axis=1)

# Calculate centroid
centroids = merged.geometry.centroid
merged['lat'] = centroids.y
merged['lng'] = centroids.x

# Assign unique ID
merged['did'] = range(len(merged))

# Simplify for GeoJSON export
merged['geometry'] = merged['geometry'].simplify(0.0003)

# Export as GeoJSON
export_cols = ['geometry', 'did', 'display', 'region', 'system', 'sgg', 'area', 'ntf', 'atrb', 'lat', 'lng']
geojson_data = merged[export_cols].to_json(ensure_ascii=False)

# Save centroid index (did -> lat, lng, display) for Notion linking
centroid_index = []
for _, r in merged.iterrows():
    centroid_index.append({
        'did': int(r['did']),
        'display': r['display'],
        'region': r['region'],
        'system': r['system'],
        'sgg': r['sgg'],
        'area': r['area'],
        'lat': round(r['lat'], 6),
        'lng': round(r['lng'], 6),
        'ntf': r['ntf'],
        'atrb': r['atrb'],
    })

with open(r'D:\지구단위계획구역_extract_temp\centroid_index.json', 'w', encoding='utf-8') as f:
    json.dump(centroid_index, f, ensure_ascii=False)
print(f'Centroid index: {len(centroid_index)} entries')

# Build HTML map with JavaScript for URL parameter zoom
html_template = '''<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>지구단위계획구역 전국 지도</title>
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"/>
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<style>
  body{margin:0;padding:0;}
  #map{position:absolute;top:0;bottom:0;width:100%;}
  #info{position:absolute;top:10px;left:60px;z-index:1000;background:white;
    padding:10px 15px;border-radius:8px;box-shadow:0 2px 8px rgba(0,0,0,0.3);
    font:14px/1.5 'Malgun Gothic',sans-serif;max-width:400px;}
  #info h3{margin:0 0 5px;color:#1565C0;}
  #search{position:absolute;top:10px;right:10px;z-index:1000;}
  #search input{padding:8px 12px;font-size:14px;border:2px solid #1565C0;
    border-radius:20px;width:250px;outline:none;}
  #results{background:white;border-radius:8px;max-height:300px;overflow-y:auto;
    box-shadow:0 2px 8px rgba(0,0,0,0.2);margin-top:4px;display:none;}
  #results div{padding:8px 12px;cursor:pointer;border-bottom:1px solid #eee;font-size:13px;}
  #results div:hover{background:#E3F2FD;}
  .legend{position:absolute;bottom:30px;left:10px;z-index:1000;background:white;
    padding:10px;border-radius:8px;box-shadow:0 2px 6px rgba(0,0,0,0.2);font-size:13px;}
  .legend div{margin:3px 0;}
  .legend span{display:inline-block;width:14px;height:14px;margin-right:6px;
    vertical-align:middle;border-radius:2px;}
</style>
</head>
<body>
<div id="map"></div>
<div id="info"><h3>지구단위계획구역 전국 지도</h3>
<div>32,070개 구역 | 클릭/검색으로 탐색</div></div>
<div id="search">
  <input type="text" id="searchInput" placeholder="구역명 검색 (예: 송산그린시티)">
  <div id="results"></div>
</div>
<div class="legend">
  <div><span style="background:#2196F3"></span>KLIP (국토이용정보)</div>
  <div><span style="background:#9C27B0"></span>UPIS (도시계획정보)</div>
</div>

<script>
var map = L.map('map').setView([36.5, 127.8], 7);

L.tileLayer('https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png', {
  attribution: 'CartoDB', maxZoom: 19
}).addTo(map);

var satLayer = L.tileLayer('https://mt1.google.com/vt/lyrs=s&x={x}&y={y}&z={z}', {
  attribution: 'Google', maxZoom: 20
});
var osmLayer = L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
  attribution: 'OSM', maxZoom: 19
});

L.control.layers({
  '기본': L.tileLayer('https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png',{maxZoom:19}).addTo(map),
  '위성': satLayer,
  'OSM': osmLayer
}).addTo(map);

var geojsonData = GEOJSON_DATA_PLACEHOLDER;

var highlighted = null;
var allFeatures = [];

function getColor(sys) { return sys === 'KLIP' ? '#2196F3' : '#9C27B0'; }

function style(feature) {
  return {fillColor: getColor(feature.properties.system),
    color: getColor(feature.properties.system), weight: 1.5, fillOpacity: 0.3};
}

function highlightStyle(feature) {
  return {fillColor: '#FF5722', color: '#D84315', weight: 3, fillOpacity: 0.6};
}

function onEachFeature(feature, layer) {
  allFeatures.push({layer: layer, props: feature.properties});
  var p = feature.properties;
  layer.bindTooltip('<b>' + p.display + '</b><br>' + p.region + ' | ' +
    Number(p.area).toLocaleString() + '㎡', {sticky: true});
  layer.bindPopup('<b>' + p.display + '</b><br>시도: ' + p.region +
    '<br>시군구: ' + p.sgg + '<br>면적: ' + Number(p.area).toLocaleString() + '㎡' +
    '<br>고시: ' + (p.ntf || '-') + '<br>시스템: ' + p.system +
    '<br>분류: ' + p.atrb);
  layer.on('click', function() { zoomToFeature(layer, p); });
}

var gjLayer = L.geoJSON(geojsonData, {style: style, onEachFeature: onEachFeature}).addTo(map);

function zoomToFeature(layer, props) {
  if (highlighted) highlighted.setStyle(style(highlighted.feature));
  layer.setStyle(highlightStyle(layer.feature));
  highlighted = layer;
  map.fitBounds(layer.getBounds(), {padding: [50,50], maxZoom: 16});
  document.getElementById('info').innerHTML =
    '<h3>' + props.display + '</h3>' +
    '<div>시도: ' + props.region + ' | 시군구: ' + props.sgg + '</div>' +
    '<div>면적: ' + Number(props.area).toLocaleString() + ' ㎡</div>' +
    '<div>고시일: ' + (props.ntf || '-') + '</div>' +
    '<div>시스템: ' + props.system + ' | 분류: ' + props.atrb + '</div>';
}

// Search
var searchInput = document.getElementById('searchInput');
var resultsDiv = document.getElementById('results');

searchInput.addEventListener('input', function() {
  var q = this.value.trim().toLowerCase();
  resultsDiv.innerHTML = '';
  if (q.length < 2) { resultsDiv.style.display = 'none'; return; }
  var matches = allFeatures.filter(function(f) {
    return f.props.display.toLowerCase().indexOf(q) >= 0;
  }).slice(0, 20);
  if (matches.length === 0) { resultsDiv.style.display = 'none'; return; }
  resultsDiv.style.display = 'block';
  matches.forEach(function(f) {
    var div = document.createElement('div');
    div.textContent = f.props.display + ' (' + f.props.region + ', ' +
      Number(f.props.area).toLocaleString() + '㎡)';
    div.onclick = function() {
      zoomToFeature(f.layer, f.props);
      resultsDiv.style.display = 'none';
      searchInput.value = f.props.display;
    };
    resultsDiv.appendChild(div);
  });
});

// URL parameter: ?did=123 or ?lat=37.5&lng=127.0
var params = new URLSearchParams(window.location.search);
var hash = window.location.hash;

if (params.get('did')) {
  var targetDid = parseInt(params.get('did'));
  var found = allFeatures.find(function(f) { return f.props.did === targetDid; });
  if (found) setTimeout(function() { zoomToFeature(found.layer, found.props); }, 500);
} else if (params.get('lat') && params.get('lng')) {
  var lat = parseFloat(params.get('lat'));
  var lng = parseFloat(params.get('lng'));
  var zoom = parseInt(params.get('zoom') || '15');
  setTimeout(function() { map.setView([lat, lng], zoom); }, 300);
} else if (hash) {
  // Support #did=123
  var hashParams = new URLSearchParams(hash.substring(1));
  if (hashParams.get('did')) {
    var targetDid2 = parseInt(hashParams.get('did'));
    var found2 = allFeatures.find(function(f) { return f.props.did === targetDid2; });
    if (found2) setTimeout(function() { zoomToFeature(found2.layer, found2.props); }, 500);
  }
}
</script>
</body>
</html>'''

# Inject GeoJSON data
html_content = html_template.replace('GEOJSON_DATA_PLACEHOLDER', geojson_data)

output = r'D:\지구단위계획구역_마스터지도.html'
with open(output, 'w', encoding='utf-8') as f:
    f.write(html_content)

sz = os.path.getsize(output) / 1024 / 1024
print(f'Master map saved: {output} ({sz:.1f} MB)')

# Also save named district -> did mapping for Notion
named_map = []
for item in centroid_index:
    if item['display'] and item['display'] not in ('구역', ''):
        named_map.append(item)
named_map.sort(key=lambda x: -x['area'])

with open(r'D:\지구단위계획구역_extract_temp\named_with_did.json', 'w', encoding='utf-8') as f:
    json.dump(named_map, f, ensure_ascii=False)
print(f'Named districts with DID: {len(named_map)}')
