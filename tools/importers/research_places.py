"""把網路搜尋整理的地點（_raw/research/*.json，格式見檔內 places／updates）併進 data/src/base_places.json

用法：python tools/importers/research_places.py _raw/research/kyoto.json [_raw/research/osaka.json ...]
- 沒座標的用 OpenStreetMap Nominatim 依地址／名稱查（1 秒 1 筆，快取在 _raw/research/geocode_cache.json）；查不到的略過並列出來
- 有來源的事實寫進評論（by＝網路整理），來源連結放 p.links，地點詳細頁會列出來
- updates：只補既有地點「有來源」的推車／哺乳室資訊，不覆蓋原本的備註
"""
import json, math, os, re, sys, time, urllib.parse, urllib.request

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..')
P = lambda *a: os.path.join(ROOT, *a)
trip = json.load(open(P('data/trip.json'), encoding='utf-8'))
AREAS = json.load(open(P('data/areas.json'), encoding='utf-8'))
base_p = P('data/src/base_places.json'); base = json.load(open(base_p, encoding='utf-8'))
cache_p = P('_raw', 'research', 'geocode_cache.json')
cache = json.load(open(cache_p, encoding='utf-8')) if os.path.exists(cache_p) else {}
S_, W_, N_, E_ = trip['city']['bbox']

def norm(s): return re.sub(r'[\s\W_]+', '', re.sub(r'[（(].*?[)）]', '', str(s or '')).lower())
def dist(a, b, c, d):
    r = math.pi / 180; return 6371 * math.hypot((d - b) * r * math.cos((a + c) / 2 * r), (c - a) * r)
def area_of(lat, lng):
    best = min(AREAS, key=lambda a: dist(lat, lng, a['lat'], a['lng']))
    if dist(lat, lng, best['lat'], best['lng']) <= max(best.get('r', 1.6), 2.5): return best['name']
    c = trip['city']['center']; return trip['city']['name'] + ('其他' if dist(lat, lng, c[0], c[1]) < 30 else '以外')
API = os.environ.get('SHEET_API', '')   # 選用：Apps Script /exec 網址（用 Google 地圖找地點，比 OSM 準）；不要寫進 repo
def gsearch(q):
    k = 'g:' + q
    if k in cache: return cache[k]
    try:
        r = json.load(urllib.request.urlopen(API + '?' + urllib.parse.urlencode(dict(op='search', q=q, bbox=','.join(map(str, trip['city']['bbox'])),
            city=trip['city']['name'], region='jp')), timeout=40))['results']
        r = [x for x in r if x.get('isPlace') or x.get('exact')]
        cache[k] = [r[0]['lat'], r[0]['lng']] if r else None
    except Exception: cache[k] = None
    return cache[k]
def geocode(q):
    if not q: return None
    if API: return gsearch(q)
    if q in cache: return cache[q]
    url = 'https://nominatim.openstreetmap.org/search?' + urllib.parse.urlencode(dict(q=q, format='json', limit=1, countrycodes='jp',
        viewbox=f'{W_},{N_},{E_},{S_}', bounded=1))
    try: r = json.load(urllib.request.urlopen(urllib.request.Request(url, headers={'User-Agent': 'trip-mini-app/1.0'}), timeout=20))
    except Exception: r = []
    cache[q] = [float(r[0]['lat']), float(r[0]['lon'])] if r else None
    time.sleep(1.1); return cache[q]

idx = {norm(p['name']): p for p in base}
for p in base:
    for k in [p.get('name_en'), p.get('name_ja')]:
        if norm(k): idx.setdefault(norm(k), p)
new = upd = 0; dup = []; nogeo = []
for f in sys.argv[1:]:
    R = json.load(open(f, encoding='utf-8')); tag = os.path.splitext(os.path.basename(f))[0]
    for q in R.get('places', []):
        if not q.get('sources'): continue                      # 沒來源的不收
        hit = idx.get(norm(q['name'])) or idx.get(norm(q.get('name_ja')))
        if hit: dup.append(q['name']); continue
        lat, lng = q.get('lat'), q.get('lng')
        if lat is None:
            g = geocode(q.get('address')) or geocode(q.get('name_ja')) or geocode(q['name'])
            lat, lng = (g or [None, None])
        if lat is None: nogeo.append(q['name']); continue      # 查不到座標就不收，免得點放錯城市
        is_approx = False
        new += 1
        facts = [x for x in (q.get('facts') or []) if x]
        com = ([dict(src='web', by='網路整理', text=q['december'])] if q.get('december') else []) + \
              ([dict(src='web', by='網路整理', text=' / '.join(facts)[:200])] if facts else [])
        p = dict(id=f"w_{tag[:3]}_{new}", name=q['name'], name_en='', name_ja=q.get('name_ja') or '', type=q.get('type') or '其他', subcat=q.get('subcat') or '',
                 closed=q.get('closed') or '', note=q.get('note') or '', price='', address=q.get('address') or '', lat=lat, lng=lng, approx=is_approx,
                 map=f"https://www.google.com/maps/search/?api=1&query={urllib.parse.quote(q.get('name_ja') or q['name'])}",
                 ig=[], threads=[], votes=0, voters=[], src=['web'], sharedBy=[], comments=com, rating=None, ratingCount=None, fromList=False,
                 area=area_of(lat, lng), indoor=bool(q.get('indoor')), lists=['網路整理'],
                 access=dict(stroller=q.get('stroller') or '', nursing=q.get('nursing'), note=''), links=q['sources'][:4])
        base.append(p); idx[norm(p['name'])] = p
    for u in R.get('updates', []):
        p = idx.get(norm(u.get('name')))
        if not p or not u.get('sources'): continue
        a = p.setdefault('access', {})
        if u.get('nursing') is not None: a['nursing'] = u['nursing']
        if u.get('stroller'): a['stroller'] = u['stroller']
        if u.get('facts'):
            t = ' / '.join(u['facts'])[:200]
            if all(c.get('text') != t for c in p.setdefault('comments', [])): p['comments'].append(dict(src='web', by='網路整理', text=t))
        for s in u['sources'][:3]:
            if s not in p.setdefault('links', []): p['links'].append(s)
        upd += 1
json.dump(base, open(base_p, 'w', encoding='utf-8'), ensure_ascii=False, indent=0)
json.dump(cache, open(cache_p, 'w', encoding='utf-8'), ensure_ascii=False)
sys.stdout.reconfigure(encoding='utf-8')
print(f'新增 {new}、查不到座標略過 {len(nogeo)}、補充既有地點 {upd}、已在清單略過 {len(dup)}；base_places 共 {len(base)} 個')
if dup: print('  已在清單：' + '、'.join(dup))
if nogeo: print('  查不到座標：' + '、'.join(nogeo))
