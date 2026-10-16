import asyncio, json, sys
from playwright.async_api import async_playwright
sys.path.insert(0, '/home/claude/val'); from browser import route
async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch(); pg = await (await b.new_context()).new_page(); await pg.route('**/*', route)
        await pg.goto('http://local/#highways'); await pg.wait_for_function('window.__ready===true', timeout=300000)
        for y0, y1, L, st in [(1940, 2023, 20, 20), (1979, 2023, 15, 15), (1979, 2023, 20, 5), (1940, 1979, 20, 5)]:
            await pg.evaluate(f"""() => {{ S.view='highways'; S.hwmode='history'; S.y0={y0}; S.y1={y1}; S.hlen={L}; S.hstep={st}; S.eps=2; S.seasons=new Set(['DJF','MAM','JJA','SON']); S.regime=''; syncViewOpts(); compute(); }}""")
            await pg.wait_for_timeout(500); await pg.wait_for_function('!computing && !pending && HIST', timeout=900000)
            h = await pg.evaluate("({w: HIST.map(d=>[d.y0,d.y1,+d.nh.toFixed(2),+d.sh.toFixed(2)]), nhT: HIST.nhTrend, shT: HIST.shTrend})")
            f = lambda t: f"{t['b']*10:+.2f}°/dec p={t['p']:.3f}" if t else 'n/a'
            print(f'{y0}-{y1} L={L} step={st}: NH {f(h["nhT"])} | SH {f(h["shT"])} | windows {h["w"]}')
        await b.close()
asyncio.run(main())
