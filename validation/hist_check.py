import asyncio, json, sys
from playwright.async_api import async_playwright
sys.path.insert(0, '/home/claude/val'); from browser import route
from scipy import stats
async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch(); pg = await (await b.new_context()).new_page(); await pg.route('**/*', route)
        await pg.goto('http://local/#highways'); await pg.wait_for_function('window.__ready===true', timeout=300000)
        out = {}
        for L, st in [(20, 10), (20, 20), (10, 10)]:
            await pg.evaluate(f"""() => {{ S.view='highways'; S.hwmode='history'; S.hlen={L}; S.hstep={st}; S.eps=2; S.thrule='match'; S.seasons=new Set(['DJF','MAM','JJA','SON']); S.regime=''; syncViewOpts(); compute(); }}""")
            await pg.wait_for_timeout(500); await pg.wait_for_function('!computing && !pending && HIST', timeout=900000)
            h = await pg.evaluate("({mid: HIST.map(d=>d.mid), nh: HIST.map(d=>d.nh), sh: HIST.map(d=>d.sh), y0: HIST.map(d=>d.y0), nhT: HIST.nhTrend, shT: HIST.shTrend})")
            for k in ('nh', 'sh'):
                r = stats.linregress(h['mid'], h[k]); t = h[k + 'T']
                print(f'L={L} step={st} {k}: app slope {t["b"]*10:.3f}/dec p={t["p"]:.4g} | scipy slope {r.slope*10:.3f}/dec p={r.pvalue:.4g}')
            out[f'{L}_{st}'] = h
        json.dump(out, open('out/hist.json', 'w')); await b.close()
asyncio.run(main())
