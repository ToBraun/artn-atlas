"""Run the deployed page (site/index.html, as GitHub serves it) headless and pull numbers out of it."""
import asyncio, json, pathlib, sys
from playwright.async_api import async_playwright
NM = '/home/claude/proto/node_modules/'
MAP = {'cdnjs.cloudflare.com/ajax/libs/d3/7.9.0/d3.min.js': NM + 'd3/dist/d3.min.js',
       'topojson-client@3.1.0/dist/topojson-client.min.js': NM + 'topojson-client/dist/topojson-client.min.js',
       'h3-js@4.5.0/dist/h3-js.umd.js': NM + 'h3-js/dist/h3-js.umd.js',
       '@mapequation/infomap@2.15.1/index.umd.js': NM + '@mapequation/infomap/index.umd.js'}
SITE = pathlib.Path('/home/claude/real/site')
async def route(r):
    u = r.request.url
    if u.startswith('http://local/data/'): return await r.fulfill(path=str(SITE / 'data' / u.split('/data/')[1].split('?')[0]), content_type='application/octet-stream')
    if u.startswith('http://local/'): return await r.fulfill(path=str(SITE / 'index.html'), content_type='text/html; charset=utf-8')
    for pre, d in [('/fc/', NM + '@fontsource/barlow-condensed/files/'), ('/fm/', NM + '@fontsource/ibm-plex-mono/files/'), ('/f/', NM + '@fontsource/barlow/files/')]:
        if pre in u and u.endswith('.woff2'): return await r.fulfill(path=d + u.split(pre)[1], content_type='font/woff2')
    if 'fonts.googleapis.com' in u: return await r.fulfill(path='/home/claude/proto/fonts.css', content_type='text/css')
    for k, v in MAP.items():
        if k in u: return await r.fulfill(path=v, content_type='application/javascript')
    await r.abort()

# page-side helper: build a network for a state patch and export everything keyed by H3 cell string
HELPER = r"""
async (patch) => {
  Object.assign(S, patch.S || {}); if (patch.seasons) S.seasons = new Set(patch.seasons);
  await cellsFor(S.loc, S.res);
  const c = patch.cond ? { ...condA(), ...patch.cond, seasons: new Set(patch.cond.seasons || [...S.seasons]), phases: new Set(patch.cond.phases || [...curPhases()]) } : condA();
  const Gx = buildNetwork(c), cells = Gx.g.cells, cid = i => cells[Gx.gid[i]];
  const out = { epsC: Gx.epsC, matched: Gx.matched, target: Gx.target || null, months: Gx.months, ndec: Gx.ndec, nAR: Gx.nAR, n: Gx.n, E: Gx.E, IVTTHR,
    edges: Array.from({ length: Gx.E }, (_, e) => [cid(Gx.src[e]), cid(Gx.dst[e]), Gx.w[e], Gx.dmean[e], Gx.ecls[e]]),
    nodes: Array.from({ length: Gx.n }, (_, i) => [cid(i), Gx.sin[i], Gx.sout[i], Gx.nivt[i]]) };
  if (patch.pagerank) out.pr = Array.from(pagerank(Gx, patch.pagerank));
  if (patch.ebc) { const eb = await ebc(Gx); out.ebc = Array.from(eb); out.ebcK = Gx.ebcK; }
  if (patch.infomap) { const prev = S.trials; S.trials = patch.infomap.trials || 1; S.seed = patch.infomap.seed || 38;
    const IM = await infomapBasins(Gx), mod = IM.mod; S.trials = prev; out.modules = Array.from({ length: Gx.n }, (_, i) => [cid(i), mod[Gx.gid[i]]]);
    S.minsize = 15; const BB = relabelBasins(Gx, IM); out.flow = Array.from(IM.flow); out.ratio = BB.ratio.slice(1).map(r => isFinite(r) ? r : null);
    out.lab = Array.from({ length: Gx.n }, (_, i) => [cid(i), BB.lab[Gx.gid[i]]]); }
  return out;
}"""
async def run(jobs, out_dir):
    async with async_playwright() as p:
        b = await p.chromium.launch(); pg = await (await b.new_context(viewport={'width': 1400, 'height': 860})).new_page()
        await pg.route('**/*', route); pg.on('pageerror', lambda e: print('pageerror', e))
        await pg.goto('http://local/#network'); await pg.wait_for_function('window.__ready===true', timeout=300000)
        await pg.wait_for_function('!computing', timeout=300000)
        for name, patch in jobs:
            res = await pg.evaluate(HELPER, patch)
            pathlib.Path(out_dir, name + '.json').write_text(json.dumps(res)); print('done', name, res['n'], res['E'], res['epsC'])
        await b.close()
if __name__ == '__main__':
    jobs = json.loads(pathlib.Path(sys.argv[1]).read_text()); asyncio.run(run(jobs, sys.argv[2]))
