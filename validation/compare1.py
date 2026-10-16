import sys, json, numpy as np, pandas as pd, networkx as nx, time
sys.path.insert(0, '/home/claude/val/ref')
import refnet, ARnet_sub as artn, NETanalysis_sub as ana
df = pd.read_pickle('/home/claude/val/ref/cat.pkl')
J = lambda n: json.load(open(f'out/{n}.json'))
R = {}
def edgecmp(name, G, B):
    ref = {(u, v): d['weight'] for u, v, d in G.edges(data=True)}
    br = {(a, b): w for a, b, w, *_ in B['edges']}
    inter = set(ref) & set(br)
    wdiff = max((abs(ref[k] - br[k]) for k in inter), default=0)
    r = dict(ref_edges=len(ref), browser_edges=len(br), common=len(inter), only_ref=len(set(ref) - set(br)), only_browser=len(set(br) - set(ref)),
             jaccard=round(len(inter) / len(set(ref) | set(br)), 4), max_weight_diff=float(wdiff), ref_nodes=G.number_of_nodes(), browser_nodes=B['n'])
    print(name, r); R[name] = r; return ref, br

# 1. unconditioned networks: identical construction expected
for name, loc, res in [('base_c2', 'centroid', 2), ('base_h2', 'head', 2), ('base_c1', 'centroid', 1), ('base_c3', 'centroid', 3), ('eps8', 'centroid', 2)]:
    B = J(name); G, th, tv, cats = refnet.build(df, loc, res, B['epsC'])
    edgecmp(name, G, B)
    if name in ('base_c2', 'base_h2', 'eps8'):
        # node measures with the author's functions
        nodes = list(G.nodes()); bn = {c: (si, so, iv) for c, si, so, iv in B['nodes']}
        st = dict(zip(nodes, ana.degree_centrality(G))); dv = dict(zip(nodes, ana.divergence(G)))
        pr = dict(zip(nodes, ana.pagerank(G, 0.9, normalised=True)))
        bpr = {c: p * 100 for (c, *_), p in zip(B['nodes'], B['pr'])}
        R[name + '_nodes'] = dict(
            strength_maxabs=float(max(abs(st[c] - (bn[c][0] + bn[c][1])) for c in nodes)),
            divergence_maxabs=float(max(abs(dv[c] - (bn[c][1] - bn[c][0])) for c in nodes)),
            pagerank_max_rel=float(max(abs(pr[c] - bpr[c]) / pr[c] for c in nodes)),
            pagerank_sum_browser=float(sum(B['pr'])), divergence_sum=float(sum(dv.values())),
            strength_p99_per_decade=float(np.quantile(list(st.values()), .99) / (B['months'] / 120)))
        print(name, 'nodes', R[name + '_nodes'])
    if name == 'base_c2':
        # IVT classes: thresholds from pooled step differences, edge classes, node net IVT
        (o, d), (vo, vd) = th[0], tv[0]
        diffs = vd - vo
        thr = np.nanquantile(diffs, [.1, .25, .4, .6, .75, .9])
        R['ivt_thresholds'] = dict(reference=[round(x, 2) for x in thr], browser=B['IVTTHR'])
        ecl = ana.compute_edge_moisture_transport((o, d), (vo, vd), output='manual', thresholds=thr)
        bcl = {(a, b): c for a, b, w, dm, c in B['edges']}
        agree = np.mean([ecl[k] == bcl[k] for k in bcl])
        dmean = {}
        for a, b, w, dm, c in B['edges']: dmean[(a, b)] = dm
        s = pd.DataFrame({'o': o, 'd': d, 'df': diffs}).groupby(['o', 'd'])['df'].mean()
        dm_err = max(abs(s[k] - dmean[k]) for k in bcl)
        # node net IVT: mean IVT leaving (at destination) minus mean IVT arriving (at origin)
        out_mean = pd.Series(vd).groupby(o).mean(); in_mean = pd.Series(vo).groupby(d).mean()
        net = (out_mean - in_mean).dropna()
        bnet = {c: iv for c, si, so, iv in B['nodes'] if iv is not None and np.isfinite(iv)}
        nerr = max(abs(net[c] - bnet[c]) for c in bnet if c in net.index)
        R['ivt_classes'] = dict(edge_class_agreement=float(agree), edge_mean_diff_maxabs=float(dm_err), node_net_ivt_maxabs=float(nerr), nodes_compared=len(bnet))
        print(R['ivt_thresholds'], R['ivt_classes'])
        # EBC with the paper's recipe: inverted weights + networkx, normalised
        t0 = time.time(); Gi = ana.invert_weights(G); eb = nx.edge_betweenness_centrality(Gi, weight='weight')
        beb = {(a, b): x for (a, b, *_), x in zip(B['edges'], B['ebc'])}
        ks = list(eb); x = np.array([eb[k] for k in ks]); y = np.array([beb[k] for k in ks])
        top = lambda v, p: set(np.array(ks, dtype=object)[np.argsort(-v)[:int(len(v) * p)]].tolist()) if False else None
        order_r = np.argsort(-x); order_b = np.argsort(-y); k4 = int(len(x) * .04)
        set_r = {ks[i] for i in order_r[:k4]}; set_b = {ks[i] for i in order_b[:k4]}
        R['ebc'] = dict(max_abs=float(np.max(np.abs(x - y))), max=float(x.max()), corr=float(np.corrcoef(x, y)[0, 1]),
                        top4pct_overlap=len(set_r & set_b) / k4, seconds=round(time.time() - t0))
        print('ebc', R['ebc'])
json.dump(R, open('out/compare1.json', 'w'), indent=1)
