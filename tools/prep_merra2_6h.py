import pandas as pd, numpy as np, h3, sys
"""PIKART MERRA-2 hex pickle -> slim npz for prep_web_data.py: 1980-2018, thinned to 6-hourly, centroid res 1-3.
Usage: python prep_merra2_6h.py pikart_merra2_hex.pkl merra2_6h.npz"""
m=pd.read_pickle(sys.argv[1])[["time","trackid","mean_ivt","centroid_lat","centroid_lon","hex_idx_centroid_res1","hex_idx_centroid_res2"]]
m['time']=pd.to_datetime(m.time)
# check stored hex vs recomputed
s=m.sample(20000,random_state=0)
for r in (1,2):
    ok=(s[f'hex_idx_centroid_res{r}']==[h3.latlng_to_cell(a,b,r) for a,b in zip(s.centroid_lat,s.centroid_lon)]).mean(); print('res',r,'match',ok)
def slim(d):
    pts,inv=np.unique(np.c_[d.centroid_lat,d.centroid_lon],axis=0,return_inverse=True); inv=inv.ravel()
    out=dict(time=d.time.values.astype('datetime64[h]').astype(np.int64),trackid=d.trackid.to_numpy(np.int64),mean_ivt=d.mean_ivt.to_numpy(np.float32))
    for r in (1,2,3): out[f'hex_idx_centroid_res{r}']=np.array([int(h3.latlng_to_cell(a,b,r),16) for a,b in pts],dtype=np.uint64)[inv]
    return out
m=m[m.time.dt.year<=2018]
m6=m[m.time.dt.hour%6==0]
print('3h rows',len(m),'6h rows',len(m6),'tracks',m.trackid.nunique(),m6.trackid.nunique())
np.savez_compressed(sys.argv[2],**slim(m6))
