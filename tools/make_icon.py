"""產生主畫面圖示（assets/icons/*.png）：白底＋圓形色塊＋一個 emoji，或直接用你自己的 SVG

用法：python tools/make_icon.py "🏯" [圓形顏色，預設 #e60033] [背景顏色，預設 #ffffff]
      python tools/make_icon.py --svg 你的圖.svg
需要：pip install playwright && playwright install chromium
（東京那趟用的是手畫的東京鐵塔 SVG，在 presets/tokyo/icon.svg，可以參考）
"""
import asyncio, os, sys
from playwright.async_api import async_playwright

D = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'assets', 'icons'); os.makedirs(D, exist_ok=True)
if sys.argv[1] == '--svg':
    svg = open(sys.argv[2], encoding='utf-8').read()
else:
    emoji, circle, bg = sys.argv[1], (sys.argv[2] if len(sys.argv) > 2 else '#e60033'), (sys.argv[3] if len(sys.argv) > 3 else '#ffffff')
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512"><rect width="512" height="512" fill="{bg}"/>
<circle cx="256" cy="256" r="180" fill="{circle}"/><text x="256" y="262" font-size="250" text-anchor="middle" dominant-baseline="middle"
font-family="Apple Color Emoji, Segoe UI Emoji, Noto Color Emoji, sans-serif">{emoji}</text></svg>'''
open(os.path.join(D, 'icon.svg'), 'w', encoding='utf-8').write(svg)
async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch()
        for name, size in [('apple-touch-icon.png', 180), ('icon-192.png', 192), ('icon-512.png', 512), ('favicon-32.png', 32)]:
            pg = await b.new_page(viewport={'width': size, 'height': size})
            await pg.set_content(f'<html><body style="margin:0">{svg.replace("<svg ", f"<svg width=\"{size}\" height=\"{size}\" ", 1)}</body></html>')
            await pg.screenshot(path=os.path.join(D, name)); await pg.close()
        await b.close()
asyncio.run(main())
print('✓ 已更新 assets/icons（已加到主畫面的人要移除後重加才會換）')
