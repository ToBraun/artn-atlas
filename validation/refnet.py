"""Reference ARTN built with the author's own ARnet_sub / NETanalysis_sub code.
Only origins_and_destinations is replaced by a vectorised version with identical semantics
(consecutive rows of each trackid in catalogue order, rows with NaN coord_idx removed first);
the original loops over 134k tracks with a full-table mask each and would take hours."""
import numpy as np, pandas as pd, networkx as nx, sys
sys.path.insert(0, '/home/claude/val/ref')
import ARnet_sub as artn, NETanalysis_sub as ana

def _od_vectorised(ARcat, LC_cond=None):
    assert LC_cond is None
    d = ARcat[ARcat['coord_idx'].notna()]
    tid = d['trackid'].values
    same = tid[1:] == tid[:-1]          # consecutive rows of the same track (catalogue order, as in the loop)
    # the original groups by unique trackid; rows of one track must be contiguous for this to be identical
    assert pd.Series(tid).ne(pd.Series(tid).shift()).sum() == len(np.unique(tid)), 'tracks not contiguous'
    c = d['coord_idx'].values; v = d['mean_ivt'].values
    return c[:-1][same], v[:-1][same], c[1:][same], v[1:][same]
artn.origins_and_destinations = _od_vectorised

def load_catalog(path='/mnt/user-data/uploads/ARTN_visualizer/data/pikart_slim.npz'):
    z = np.load(path)
    df = pd.DataFrame({'time': z['time'].astype('datetime64[h]').astype('datetime64[ns]'), 'trackid': z['trackid'], 'mean_ivt': z['mean_ivt']})
    for k in z.files:
        if k.startswith('hex_idx_'):
            df[k] = np.array([format(int(x), 'x') for x in z[k]])
    return df.sort_values(['trackid', 'time'], kind='stable').reset_index(drop=True)

def build(df, loc='centroid', res=2, eps=16, T=None, cond=None):
    l_cats, cd = artn.preprocess_catalog(df.copy(), T, loc, 'hexagonal', 'global', res, cond, None)
    A, t_idx, t_hex, t_ivt, t_grid = artn.generate_transport_matrix(l_cats, 'hexagonal', cd, None)
    G = artn.generate_network(A, t_grid, True, True, eps, False, 'absolute')
    return G, t_hex, t_ivt, l_cats
