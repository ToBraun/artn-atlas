import sys, json, numpy as np, pandas as pd, networkx as nx
from sklearn.metrics import adjusted_mutual_info_score as ami, adjusted_rand_score as ari
sys.path.insert(0, '/home/claude/val/ref'); import refnet, NETanalysis_sub as ana, ARnet_sub as artn
df = pd.read_pickle('ref/cat.pkl'); G, *_ = refnet.build(df, 'centroid', 2, 8)
G = artn.complete_nodes(G, 2)                                   # as in Fig5_ARbasins.py
G = nx.relabel_nodes(G, dict(zip(list(G.nodes()), range(G.number_of_nodes()))))
cid = nx.get_node_attributes(G, 'coordID')
R = {}
def sizes(lab, nmin=15):
    s = pd.Series(lab).value_counts(); return int((s >= nmin).sum()), int(s.max())
refs = {}
for seed in [38, 7, 1, 2, 3]:
    comm = ana.detect_non_hierarchical_communities(G, use_node_weights_as_flow=True, seed=seed)
    refs[seed] = {cid[n]: m for n, m in comm.items()}
B = {k: {c: m for c, m in json.load(open(f'out/{k}.json'))['modules']} for k in ['inf_eps8_s38', 'inf_eps8_s7', 'inf_eps8_t5']}
cells = sorted(set(B['inf_eps8_s38']) & set(refs[38]))
def score(a, b):
    x = [a[c] for c in cells]; y = [b[c] for c in cells]; return round(ami(x, y), 3)
R['n_cells'] = len(cells)
R['python_seeds_vs_each_other'] = {f'{a}-{b}': score(refs[a], refs[b]) for a, b in [(38, 7), (38, 1), (1, 2), (2, 3)]}
R['browser_vs_python'] = {f'{k}-py{s}': score(B[k], refs[s]) for k in B for s in [38, 7, 1]}
R['basins_ge15'] = {**{f'py{s}': sizes([refs[s][c] for c in cells]) for s in refs}, **{k: sizes([B[k][c] for c in cells]) for k in B}}
print(json.dumps(R, indent=1)); json.dump(R, open('out/compare3.json', 'w'), indent=1)
