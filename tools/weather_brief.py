"""行前天氣快報：抓整趟旅程每天的天氣預報（Open-Meteo，免金鑰），整理成 Markdown

用法：
  python tools/weather_brief.py              # 印出快報
  python tools/weather_brief.py --issue      # 在 GitHub 開一則 issue（需要環境變數 GITHUB_TOKEN、GITHUB_REPOSITORY）
GitHub Actions（.github/workflows/weather-brief.yml）會在出發前自動跑，開 issue 後 GitHub 會寄信通知。
16 天內才有預報；更早的日期會標「還沒有預報」。
"""
import datetime, json, math, os, sys, urllib.request, urllib.parse

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
trip = json.load(open(os.path.join(ROOT, 'data', 'trip.json'), encoding='utf-8'))
places = json.load(open(os.path.join(ROOT, 'data', 'places.json'), encoding='utf-8'))
WD = '一二三四五六日'
SITE = os.environ.get('SITE_URL', '')

def wmo(c):
    if c is None: return '❔', '未知'
    for lim, ic, tx in [(0, '☀️', '晴'), (2, '🌤️', '晴時多雲'), (3, '☁️', '陰'), (48, '🌫️', '霧'), (57, '🌦️', '毛毛雨'), (67, '🌧️', '雨'),
                        (77, '🌨️', '雪'), (82, '🌧️', '陣雨'), (86, '🌨️', '陣雪')]:
        if c <= lim: return ic, tx
    return '⛈️', '雷雨'

def loc_of(d):
    ls = trip.get('lodgings') or [trip['lodging']]
    l = next((l for l in ls if l['checkin'] <= d < l['checkout']), ls[-1])
    c = trip['city']
    return l.get('wx') or {'name': c['name'], 'lat': c['center'][0], 'lng': c['center'][1]}

def dist(a, b, c, d):
    r = math.pi / 180
    return 6371 * math.hypot((d - b) * r * math.cos((a + c) / 2 * r), (c - a) * r)

def fetch(l, d0, d1):
    q = urllib.parse.urlencode(dict(latitude=l['lat'], longitude=l['lng'], timezone='Asia/Tokyo', start_date=d0, end_date=d1,
        daily='weather_code,temperature_2m_max,temperature_2m_min,precipitation_probability_max,precipitation_sum',
        hourly='precipitation_probability'))
    return json.load(urllib.request.urlopen('https://api.open-meteo.com/v1/forecast?' + q, timeout=30))

today = datetime.date.fromisoformat(os.environ['TODAY']) if os.environ.get('TODAY') else datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9))).date()   # TODAY 可覆寫，測試用
horizon = str(today + datetime.timedelta(days=15))
groups = {}
for d in trip['dates']:
    l = loc_of(d); groups.setdefault(l['name'], (l, []))[1].append(d)
W = {}
for name, (l, ds) in groups.items():
    fc = [d for d in ds if d <= horizon]
    if not fc: continue
    try: r = fetch(l, fc[0], fc[-1]); dl = r['daily']
    except Exception as e: print(f'⚠️ {name} 預報抓不到：{e}', file=sys.stderr); continue
    for i, d in enumerate(dl['time']):
        if d not in fc: continue
        hrs = [int(t[11:13]) for t, v in zip(r['hourly']['time'], r['hourly']['precipitation_probability'])
               if t.startswith(d) and 8 <= int(t[11:13]) <= 20 and (v or 0) >= 50]
        W[d] = dict(loc=name, lat=l['lat'], lng=l['lng'], code=dl['weather_code'][i], tmax=dl['temperature_2m_max'][i], tmin=dl['temperature_2m_min'][i],
                    pop=dl['precipitation_probability_max'][i], rain=dl['precipitation_sum'][i], hrs=(hrs[0], hrs[-1] + 1) if hrs else None)

def md(d):
    x = datetime.date.fromisoformat(d); return f"{x.month}/{x.day}（{WD[x.weekday()]}）"

start = datetime.date.fromisoformat(trip['dates'][0]); dleft = (start - today).days
lines = [f"# 🌦️ {trip['title']}｜行前天氣快報", '',
         f"{today.month}/{today.day} 更新 · {'距離出發還有 ' + str(dleft) + ' 天' if dleft > 0 else '旅程進行中'} · 資料來源：Open-Meteo 預報（會隨時間變動）", '']
wet, cold = [], []
for n, d in enumerate(trip['dates'], 1):
    w = W.get(d)
    if not w or w['tmax'] is None:
        lines.append(f"- **D{n} {md(d)}** {loc_of(d)['name']}：還沒有預報"); continue
    ic, tx = wmo(w['code'])
    is_wet = (w['pop'] or 0) >= 50 or (w['rain'] or 0) >= 1
    tip = []
    if w['hrs']: tip.append(f"☔ {w['hrs'][0]}–{w['hrs'][1]} 點可能下雨")
    elif is_wet: tip.append('☔ 可能下雨')
    if w['tmin'] <= 3: tip.append(f"🥶 最低 {round(w['tmin'])}°C")
    if is_wet: wet.append((n, d, w))
    if w['tmin'] <= 3: cold.append(n)
    lines.append(f"- **D{n} {md(d)}** {w['loc']} {ic} {tx} {round(w['tmin'])}–{round(w['tmax'])}°C · 降雨機率 {w['pop'] if w['pop'] is not None else '–'}% · {w['rain'] or 0} mm"
                 + (f"　{'、'.join(tip)}" if tip else ''))
lines += ['', '## 要注意']
if wet:
    lines.append('- ☔ **可能下雨**：' + '、'.join(f"D{n}" for n, _, _ in wet) + '，推車雨罩、雨衣、替換衣物帶著')
    for n, d, w in wet:
        near = sorted((p for p in places if p.get('indoor') and p.get('lat') and dist(w['lat'], w['lng'], p['lat'], p['lng']) < 15),
                      key=lambda p: dist(w['lat'], w['lng'], p['lat'], p['lng']))[:4]
        if near: lines.append(f"  - D{n} 雨天備案（室內）：" + '、'.join(p['name'] for p in near))
else:
    lines.append('- ☀️ 目前預報沒有明顯的雨天')
if cold: lines.append('- 🥶 **低溫**：' + '、'.join(f"D{n}" for n in cold) + ' 最低 3°C 以下，推車防風罩、手套、帽子、暖暖包')
lines += ['- 預報每天都會變，出發後以網站上的天氣卡為準（每 3 小時自動更新）']
if SITE: lines += ['', f"👉 打開網站：{SITE}"]
body = '\n'.join(lines)

if '--issue' in sys.argv:
    tok, repo = os.environ['GITHUB_TOKEN'], os.environ['GITHUB_REPOSITORY']
    req = urllib.request.Request(f'https://api.github.com/repos/{repo}/issues', method='POST',
        data=json.dumps({'title': f"🌦️ 行前天氣快報 {today.month}/{today.day}（{'D-' + str(dleft) if dleft > 0 else '旅程中'}）", 'body': body}).encode(),
        headers={'Authorization': f'Bearer {tok}', 'Accept': 'application/vnd.github+json'})
    print('issue:', json.load(urllib.request.urlopen(req, timeout=30))['html_url'])
else:
    sys.stdout.reconfigure(encoding='utf-8'); print(body)
