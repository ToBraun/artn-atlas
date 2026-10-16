import sys, json, numpy as np, pandas as pd, networkx as nx
sys.path.insert(0, '/home/claude/val/ref'); import refnet, ARnet_sub as artn
df = pd.read_pickle('ref/cat.pkl'); J = lambda n: json.load(open(f'out/{n}.json')); R = {}
def cmp(name, G, B):
    ref = {(u, v): d['weight'] for u, v, d in G.edges(data=True)}; br = {(a, b): w for a, b, w, *_ in B['edges']}
    inter = set(ref) & set(br); wd = np.array([abs(ref[k] - br[k]) for k in inter])
    r = dict(ref_edges=len(ref), browser_edges=len(br), jaccard=round(len(inter) / len(set(ref) | set(br)), 4),
             weight_identical=float(np.mean(wd == 0)), max_weight_diff=float(wd.max() if len(wd) else 0))
    print(name, r); R[name] = r
def nets(cond, eps, data):
    l_cats, cd = artn.preprocess_catalog(data.copy(), None, 'centroid', 'hexagonal', 'global', 2, cond, None)
    A, ti, th, tv, tg = artn.generate_transport_matrix(l_cats, 'hexagonal', cd, None)
    return artn.generate_network(A, tg, True, True, eps, False, 'absolute'), l_cats
# time window: the paper's constrain() (strict bounds, drops first/last track) vs the app (step origin month in window)
G, *_ = refnet.build(df, 'centroid', 2, J('win_8019')['epsC'], T=[1980, 2019]); cmp('window_1980_2019', G, J('win_8019'))
# seasons: script splits catalogue rows by season (cond='season'), groups sorted DJF, JJA, MAM, SON
Gs, cats = nets('season', [4, 4, 4, 4], df); cmp('DJF_rate_eps4', Gs[0], J('djf_rate'))
Gs, cats = nets('season', [5, 5, 5, 5], df)
for i, s in enumerate(['djf', 'jja', 'mam', 'son']): cmp(s.upper() + '_eps5', Gs[i], J(s + '_match'))
# ENSO with the script's own labelling (ONI, skiprows=1, drop -99.9 rows, 3-mo rolling, z-score, +-0.5, >=5 months)
d = pd.read_csv('/mnt/user-data/uploads/ARTN_visualizer/data/ONI.txt', sep=r'\s+', header=None, dtype=str, skiprows=1, engine='python')
d = d[d.apply(lambda row: not row.str.contains('-99.90').any(), axis=1)].astype(float)
d.columns = ['Year', 'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
L = d.melt(id_vars='Year', var_name='Month', value_name='COidx'); L['Month'] = pd.to_datetime(L['Month'], format='%b').dt.month
L['Date'] = pd.to_datetime(L[['Year', 'Month']].assign(Day=1)); L = L.set_index('Date').sort_index()
L['avg'] = L['COidx'].rolling(window=3, min_periods=3).mean()
def csp(s, thr, mp, ph):
    s = (s - np.nanmean(s)) / np.std(s); c = (s > thr if ph == 1 else s < thr).astype(int)
    return (c.groupby((c != c.shift()).cumsum()).cumsum() >= mp) * ph
L['tc'] = (csp(L['avg'], .5, 5, 1) + csp(L['avg'], -.5, 5, -1)).replace({np.nan: 0}).astype(int)
reg = json.load(open('/home/claude/real/data/regimes.json')); en = [i for i in reg['indices'] if i['key'] == 'enso'][0]
app = {(1940 + m // 12, m % 12 + 1): en['labels'][m] for m in range(len(en['labels']))}
mapc = {1: '+', 0: '0', -1: '-'}
mism = [(k, app.get((k.year, k.month)), mapc[v]) for k, v in L['tc'].items() if 1940 <= k.year <= 2023 and app.get((k.year, k.month)) != mapc[v]]
R['enso_labels'] = dict(months_compared=int(sum(1 for k in L.index if 1940 <= k.year <= 2023)), mismatches=len(mism), first_mismatches=[str(x) for x in mism[:5]],
                        counts={p: int(sum(1 for k, v in L['tc'].items() if 1940 <= k.year <= 2023 and mapc[v] == p)) for p in '+0-'})
print(R['enso_labels'])
# ENSO networks: label every catalogue row by its month (the script floors to days and forward-fills monthly labels)
lab = {(k.year, k.month): v for k, v in L['tc'].items()}
dd = df.copy(); dd['teleconnection'] = [lab.get(x) for x in zip(dd.time.dt.year, dd.time.dt.month)]
dd = dd[dd['teleconnection'].notna()]
for app_name, idx in [('nina', 0), ('neut', 1), ('nino', 2)]:
    B = J(app_name); Gs, _ = nets('teleconnection', [B['epsC']] * 3, dd); cmp(f'ENSO_{app_name}_eps{B["epsC"]}', Gs[idx], B)
Gs, _ = nets('teleconnection', [3, 9, 3], dd)
R['enso_paper_thresholds_3_9_3'] = {n: Gs[i].number_of_edges() for n, i in [('nina', 0), ('neut', 1), ('nino', 2)]}
R['unconditioned_edges_eps16'] = 12750
print(R['enso_paper_thresholds_3_9_3'])
json.dump(R, open('out/compare2.json', 'w'), indent=1)
