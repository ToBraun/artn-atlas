import sys, json, numpy as np, pandas as pd, networkx as nx
sys.path.insert(0, '/home/claude/val/ref'); import refnet
df = pd.read_pickle('ref/cat.pkl')
for name, loc, eps in [('base_c2', 'centroid', 16), ('eps8', 'centroid', 8)]:
    B = json.load(open(f'out/{name}.json')); G, *_ = refnet.build(df, loc, 2, eps)
    b = {c: p for (c, *_), p in zip(B['nodes'], B['pr'])}
    for tol in (1e-6, 1e-10, 1e-13):
        pr = nx.pagerank(G, alpha=0.9, weight='weight', tol=tol, max_iter=10000)
        rel = max(abs(pr[c] - b[c]) / pr[c] for c in pr)
        print(name, 'nx tol', tol, 'max rel diff to browser', round(rel, 6))
