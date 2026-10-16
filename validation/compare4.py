import sys, json, numpy as np, pandas as pd, networkx as nx
from infomap import Infomap
sys.path.insert(0, '/home/claude/val/ref'); import refnet, NETanalysis_sub as ana
df = pd.read_pickle('ref/cat.pkl'); G, *_ = refnet.build(df, 'centroid', 2, 8)
B = json.load(open('out/inf_eps8_s38.json'))
nodes = list(G.nodes()); idx = {c: i for i, c in enumerate(nodes)}; H = nx.relabel_nodes(G, idx)
im = Infomap(no_self_links=True, directed=True, two_level=True, silent=True, use_node_weights_as_flow=True, seed=38)
tot = sum(d['weight'] for *_, d in H.edges(data=True))
for u, v, d in H.edges(data=True): im.add_link(u, v, d['weight'] / tot)
im.run(); fl = {(nodes[int(a)], nodes[int(b)]): f for a, b, f in im.get_links(data='flow')}
bf = {(a, b): f for (a, b, *_), f in zip(B['edges'], B['flow'])}
k = list(fl); x = np.array([fl[e] for e in k]); y = np.array([bf[e] for e in k])
print('link flow: max rel diff', np.max(np.abs(x - y) / x), 'corr', np.corrcoef(x, y)[0, 1])
lab = {c: (l if l else -999) for c, l in B['lab']}
d_flow = pd.DataFrame([(a, b, f) for (a, b), f in fl.items()], columns=['Node1', 'Node2', 'Flow'])
r = ana.compute_community_flow_ratio(d_flow, lab)
br = B['ratio']; diffs = [abs(r[c] - br[c - 1]) / r[c] for c in r if br[c - 1] is not None and np.isfinite(r[c])]
print('basins', len(r), 'flow ratio max rel diff', max(diffs), 'example', [(c, round(r[c], 3), round(br[c - 1], 3)) for c in list(r)[:5]])
