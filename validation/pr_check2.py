import sys, json, numpy as np, pandas as pd, networkx as nx
sys.path.insert(0, '/home/claude/val/ref'); import refnet
df = pd.read_pickle('ref/cat.pkl')
G, *_ = refnet.build(df, 'centroid', 2, 8)
a = nx.pagerank(G, alpha=0.9, weight='weight'); b = nx.pagerank(G, alpha=0.9, weight='weight', tol=1e-13, max_iter=10000)
k = list(a); x = np.array([a[c] for c in k]); y = np.array([b[c] for c in k]); rel = np.abs(x - y) / y
q = np.quantile(y, [.5, .9, .99])
print('median rel err', np.median(rel), 'max', rel.max())
for lo, lab in [(q[0], 'above median'), (q[1], 'top 10%'), (q[2], 'top 1%')]:
    m = y >= lo; print(lab, 'max rel err', rel[m].max().round(4), 'mean', rel[m].mean().round(4))
print('rank corr', pd.Series(x).corr(pd.Series(y), method='spearman'))
# iterations networkx needed
