import asyncio, json, pathlib, sys
from playwright.async_api import async_playwright
sys.path.insert(0, '/home/claude/val'); from browser import route
CONF = [
 ('F2a', 'network', {'eps': 2, 'thrule': 'rate'}, None),
 ('F2b', 'hubs', {'eps': 0.96, 'metric': 'strength', 'tophubs': 0}, None),
 ('F2c', 'hubs', {'eps': 0.96, 'metric': 'divergence', 'tophubs': 0, 'loc': 'head'}, None),
 ('F2d', 'hubs', {'eps': 0.96, 'metric': 'pagerank', 'alpha': 0.9, 'tophubs': 0, 'loc': 'head'}, None),
 ('F3a', 'hubs', {'eps': 2, 'metric': 'ivtnode', 'tophubs': 0}, None),
 ('F4a', 'highways', {'eps': 2, 'hwmode': 'roads'}, None),
 ('F4b', 'highways', {'eps': 2, 'hwmode': 'ivt'}, None),
 ('F4d', 'highways', {'eps': 2, 'hwmode': 'compare', 'cmptype': 'seasons', 'thrule': 'match'}, None),
 ('F4e', 'highways', {'eps': 2, 'hwmode': 'ivt', 'thrule': 'match'}, ['DJF']),
 ('F4f', 'highways', {'eps': 2, 'hwmode': 'ivt', 'thrule': 'match'}, ['JJA']),
 ('F4e_MAM', 'highways', {'eps': 2, 'hwmode': 'ivt', 'thrule': 'match'}, ['MAM']),
 ('F4f_SON', 'highways', {'eps': 2, 'hwmode': 'ivt', 'thrule': 'match'}, ['SON']),
 ('F4g', 'highways', {'eps': 2, 'hwmode': 'compare', 'cmptype': 'phases', 'regime': 'enso', 'thrule': 'match'}, None),
 ('F4h', 'highways', {'eps': 2, 'hwmode': 'ivt', 'regime': 'enso', 'phase': 1, 'thrule': 'match'}, None),
 ('F4i', 'highways', {'eps': 2, 'hwmode': 'ivt', 'regime': 'enso', 'phase': -1, 'thrule': 'match'}, None),
 ('F5a', 'basins', {'eps': 0.96, 'thrule': 'rate', 'trials': 5, 'seed': 38, 'minsize': 15}, None),
 ('F5b', 'basins', {'eps': 0.96, 'thrule': 'rate', 'trials': 5, 'seed': 38, 'minsize': 15, 'upstream': True}, 'select:47,-78'),
]
BASE = dict(loc='centroid', res=2, y0=1940, y1=2023, regime='', phase=0, show='values', hwmode='roads', motor=4, prim=15, minor=True, thrule='match', selNode=-1, selBasin=-1, ebcmode='auto')
async def main(names):
    async with async_playwright() as p:
        b = await p.chromium.launch(); pg = await (await b.new_context(viewport={'width': 1500, 'height': 820}, device_scale_factor=1.5)).new_page()
        await pg.route('**/*', route); pg.on('pageerror', lambda e: print('pageerror', e))
        await pg.goto('http://local/#network'); await pg.wait_for_function('window.__ready===true', timeout=300000)
        await pg.add_style_tag(content='.mapbtns,#status{display:none!important}')
        for name, view, st, extra in CONF:
            if names and name not in names: continue
            seasons = extra if isinstance(extra, list) else ['DJF', 'MAM', 'JJA', 'SON']
            await pg.evaluate("""([view, st, seasons]) => { Object.assign(S, st); S.view = view; S.seasons = new Set(seasons); syncViewOpts(); compute(); }""", [view, {**BASE, **st}, seasons])
            await pg.wait_for_timeout(400); await pg.wait_for_function('!computing && !pending', timeout=900000)
            if isinstance(extra, str) and extra.startswith('select:'):
                la, lo = map(float, extra[7:].split(','))
                await pg.evaluate("""([la, lo]) => { const c = G.g.idx.get(h3.latLngToCell(la, lo, S.res)); S.selNode = c; S.selBasin = BAS.lab[c] || -1; draw(); return S.selBasin; }""", [la, lo])
            info = await pg.evaluate("({epsC: G.epsC, E: G.E, B: GB ? GB.epsC : null, basins: BAS ? BAS.n : null, sel: S.selBasin, legend: document.getElementById('legend').innerText.replace(/\\n/g,' | ')})")
            await pg.locator('main').screenshot(path=f'/home/claude/val/tool/{name}.png'); print(name, info)
        await b.close()
pathlib.Path('/home/claude/val/tool').mkdir(exist_ok=True)
asyncio.run(main(sys.argv[1:]))
