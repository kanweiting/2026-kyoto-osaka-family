"""把 Google「我的地圖」（My Maps，網址 google.com/maps/d/...mid=xxx）併進 data/src/base_places.json

用法：python tools/importers/mymaps_kml.py <My Maps 網址或 mid> "<顯示的清單名稱>" [--default 類別] [--skip 名稱關鍵字,...]
  例：python tools/importers/mymaps_kml.py "https://www.google.com/maps/d/edit?mid=1j49..." "2024 大阪京都行"
- 地圖要設成「知道連結的人都能檢視」；會下載 KML（圖層＝資料夾名稱會記在備註）
- 只收 trip.json city.bbox 範圍內的點；跟既有地點同名或 300 m 內同名開頭的會合併（加上清單標籤和備註）
- 名稱裡的（推）、＄ 等標註會移到評論，名稱只留店名
之後跑 python tools/sync_sheet.py 產生 data/places.json。
"""
import html, json, math, os, re, sys, urllib.request
import xml.etree.ElementTree as ET

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..')
P = lambda *a: os.path.join(ROOT, *a)
args = [a for a in sys.argv[1:]]
opt = lambda k, d=None: (args[args.index(k) + 1] if k in args else d)
src, LABEL = args[0], args[1]
DEFAULT = opt('--default', '其他')
SKIP = [s for s in (opt('--skip', '') or '').split(',') if s]
mid = (re.search(r'mid=([\w-]+)', src) or re.match(r'([\w-]{20,})$', src)).group(1)
trip = json.load(open(P('data/trip.json'), encoding='utf-8'))
S_, W_, N_, E_ = trip['city']['bbox']
AREAS = json.load(open(P('data/areas.json'), encoding='utf-8'))
base_p = P('data/src/base_places.json')
base = json.load(open(base_p, encoding='utf-8')) if os.path.exists(base_p) else []

kml = urllib.request.urlopen(f'https://www.google.com/maps/d/kml?mid={mid}&forcekml=1', timeout=60).read()
NS = {'k': 'http://www.opengis.net/kml/2.2'}
root = ET.fromstring(kml)

def norm(s): return re.sub(r'[\s\W_]+', '', re.sub(r'[（(].*?[)）]', '', str(s or '')).lower())
def dist(a, b, c, d):
    r = math.pi / 180; return 6371 * math.hypot((d - b) * r * math.cos((a + c) / 2 * r), (c - a) * r)
def area_of(lat, lng):
    best = min(AREAS, key=lambda a: dist(lat, lng, a['lat'], a['lng'])) if AREAS else None
    if best and dist(lat, lng, best['lat'], best['lng']) <= max(best.get('r', 1.6), 2.5): return best['name']
    c = trip['city']['center']; return trip['city']['name'] + ('其他' if dist(lat, lng, c[0], c[1]) < 30 else '以外')
def clean(raw):
    n = raw.split('\n')[0].strip()
    tags = []
    if n.startswith(('＄', '$')): n = n[1:].strip(); tags.append('要門票')
    m = re.search(r'\s*[（(](.*)$', n)
    if m and len(n[:m.start()].strip()) >= 2: tags.append(m.group(1).rstrip('）)').strip()); n = n[:m.start()].strip()
    n = re.sub(r'tbc$', '', n).strip()
    return n, [t for t in tags if t]
def text_of(d):
    d = re.sub(r'<br\s*/?>', '\n', d or '', flags=re.I); d = html.unescape(re.sub(r'<[^>]+>', '', d))
    d = re.sub(r'\n{2,}', '\n', d).strip()
    d = re.sub(r'\s*\n\s*', ' / ', d)
    return d[:180] + ('…' if len(d) > 180 else '')
TYPES = [('餐廳', r'燒肉|焼肉|串炸|串カツ|壽司|寿司|鮨|御好燒|お好み|大阪燒|章魚燒|たこ焼|拉麵|ラーメン|noodle|牛舌|和牛|飯糰|onigiri|食堂|うどん|そば|麵|麺'),
         ('咖啡/甜點', r'cafe|café|カフェ|咖啡|coffee|喫茶|甜|提拉米蘇|鯛燒|たい焼|ice dog|千鳥屋|菓|bakery|パン'),
         ('Bar/居酒屋', r'bar|バー|居酒屋|酒場|beer'),
         ('購物', r'百貨|商店街|橫丁|横丁|美食街|市場|美國村|parco|lucua|kitte|est\b|hep|大丸|sports|supreme|carhartt|biotop|furniture|market|snkrdunk|vintage|street|outlet|伴手禮'),
         ('景點', r'寺|神社|神宮|天滿宮|公園|城|塔|展望|庭園|橋|道|疏水|苑|溫泉|湯|館|山|川|村')]
ICON = {'1577': '餐廳', '1886': '景點', '1697': '景點'}

idx = {}
for p in base:
    for k in (norm(p['name']), norm(p.get('name_en'))):
        if len(k) >= 2: idx.setdefault(k, p)
new = merged = 0; skipped = []
for f in root.iter('{%s}Folder' % NS['k']):
    layer = (f.findtext('k:name', namespaces=NS) or '').strip()
    for pm in f.findall('k:Placemark', NS):
        raw = pm.findtext('k:name', namespaces=NS) or ''
        co = (pm.findtext('.//k:coordinates', namespaces=NS) or '').strip().split()
        if not co: continue
        lng, lat = map(float, co[0].split(',')[:2])
        name, tags = clean(raw)
        if any(s in raw for s in SKIP): skipped.append(f'{name}（略過）'); continue
        if not (S_ <= lat <= N_ and W_ <= lng <= E_): skipped.append(f'{name}（範圍外）'); continue
        note = text_of(pm.findtext('k:description', namespaces=NS))
        near = lambda x, km: x.get('lat') and dist(x['lat'], x['lng'], lat, lng) < km
        # 同名（或括號裡的別名，例如「鹿苑寺(金閣寺)」）且 1.5 km 內；或 300 m 內、名稱開頭相同
        p = next((x for k in [name] + tags if (x := idx.get(norm(k))) and near(x, 1.5)), None) or             next((x for x in base if near(x, 0.3) and len(norm(name)) >= 3 and len(norm(x['name'])) >= 3
                  and (norm(x['name']).startswith(norm(name)[:3]) or norm(name).startswith(norm(x['name'])[:3]))), None)
        if p: merged += 1
        else:
            new += 1
            icon = re.search(r'icon-(\d+)|n-(\d+)|(\d{4})-', pm.findtext('k:styleUrl', namespaces=NS) or '')
            icon = next((g for g in (icon.groups() if icon else []) if g), '')
            t = next((t for t, rx in TYPES if re.search(rx, name, re.I)), ICON.get(icon, DEFAULT))
            p = dict(id=f"m_{mid[:5]}_{new}", name=name, name_en='', type=t, subcat='', closed='', note='', price='', address='', lat=lat, lng=lng, approx=False,
                     map=f"https://www.google.com/maps/search/?api=1&query={lat},{lng}", ig=[], threads=[], votes=0, voters=[], src=[], sharedBy=[], comments=[],
                     rating=None, ratingCount=None, fromList=False, area=area_of(lat, lng))
            base.append(p); idx[norm(name)] = p
        if 'mymaps' not in p['src']: p['src'].append('mymaps')
        if LABEL not in p.setdefault('lists', []): p['lists'].append(LABEL)
        txt = ' · '.join(x for x in [layer and f'圖層：{layer}', tags and '標註：' + '、'.join(tags), note] if x)
        if txt and all(c.get('text') != txt for c in p.setdefault('comments', [])) and len(p['comments']) < 5:
            p['comments'].append(dict(src='gmaps', by=LABEL, text=txt))
json.dump(base, open(base_p, 'w', encoding='utf-8'), ensure_ascii=False, indent=0)
sys.stdout.reconfigure(encoding='utf-8')
print(f'{LABEL}：新增 {new}、與既有地點合併 {merged}、略過 {len(skipped)}；base_places 共 {len(base)} 個')
if skipped: print('  略過：' + '、'.join(skipped))
