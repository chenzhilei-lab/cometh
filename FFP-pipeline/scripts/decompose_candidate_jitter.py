#!/usr/bin/env python3
"""3-way decomposition: separately perturb dedup ordering, floating-point,
and KDTree iteration order. Each perturbation runs 20 trials; we count the
mean number of candidates that differ from the baseline."""
import numpy as np, warnings, json, os
from collections import defaultdict
warnings.filterwarnings('ignore')
from astropy.io import fits
from astropy.wcs import WCS
from astropy.stats import sigma_clipped_stats
from photutils.detection import DAOStarFinder
from scipy.spatial import cKDTree

DATA='D:/JWST_FFP/serpens'; ZPT=26.5; TILE=3000
MAGLIM={'F140M':26.0,'F210M':27.0,'F360M':25.5,'F480M':25.0}
COLOR={'F140M_F210M':(-0.3,2.0),'F210M_F360M':(0.3,2.5),'F360M_F480M':(-0.2,1.5)}

# detect once -> raw catalogues (no dedup, just positions, ra, dec, mag)
raw={}
for filt in ['F140M','F210M','F360M','F480M']:
    xs,ys,fl=[],[],[]
    for fn in sorted(os.listdir(DATA)):
        if 'i2d' not in fn: continue
        f=fits.getheader(f'{DATA}/{fn}',0).get('FILTER','')
        if f!=filt: continue
        with fits.open(f'{DATA}/{fn}') as h: sci=h['SCI'].data.astype(float); w=WCS(h['SCI'].header)
        ny,nx=sci.shape
        for y0 in range(0,ny,TILE):
            for x0 in range(0,nx,TILE):
                t=sci[y0:min(y0+TILE,ny),x0:min(x0+TILE,nx)]
                if np.all(~np.isfinite(t)): continue
                _,med,std=sigma_clipped_stats(t,sigma=3.0)
                if std<=0: continue
                s=DAOStarFinder(fwhm=3.0,threshold=5*std)(t-med)
                if s is None: continue
                xc='xcentroid' if 'xcentroid' in s.colnames else 'x_centroid'
                yc='ycentroid' if 'ycentroid' in s.colnames else 'y_centroid'
                ra,dec=w.all_pix2world(np.array(s[xc])+x0,np.array(s[yc])+y0,0)
                xs+=list(ra); ys+=list(dec); fl+=list(np.array(s['flux']))
    raw[filt]=(np.array(xs),np.array(ys),-2.5*np.log10(np.maximum(np.array(fl),1e-10))+ZPT)
    print(f'{filt}: {len(xs)} raw detections')

def select(mags_fixed, dedup_order_fixed, float_jitter):
    rng=np.random.default_rng(abs(hash(str(float_jitter)+str(dedup_order_fixed)))%2**31)
    cats={}
    for filt in ['F140M','F210M','F360M','F480M']:
        x,y,m=raw[filt]; m=m+float_jitter*rng.normal(0,0.01,len(m))
        ok=m<MAGLIM[filt]; x,y,m=x[ok],y[ok],m[ok]; co=np.radians(np.column_stack([x,y])); tr=cKDTree(co)
        keep=set();seen=set()
        if dedup_order_fixed: order=np.arange(len(m)) # insertion order, not mag-sorted
        else: order=np.argsort(m) # greedy brightest-first
        for i in order:
            if i in seen: continue
            for j in tr.query_ball_point(co[i],0.3/206265): seen.add(j); keep.add(i)
        cats[filt]=(x[list(keep)],y[list(keep)],m[list(keep)])
    x,y,m=cats['F210M']; trees={f:cKDTree(np.radians(np.column_stack(cats[f][:2]))) for f in cats}
    cands=set()
    for i in range(len(x)):
        q=np.radians([[x[i],y[i]]]); mm={'F210M':m[i]}; ok=True
        for f in ['F140M','F360M','F480M']:
            d,idx=trees[f].query(q); dval=float(d[0]) if hasattr(d,'__len__') else float(d)
            if dval>0.5/206265: ok=False;break
            mm[f]=cats[f][2][int(np.atleast_1d(idx[0])[0])]
        if not ok: continue
        for cn,(lo,hi) in COLOR.items():
            f1,f2=cn.split('_')
            if not (lo<mm[f1]-mm[f2]<hi): ok=False;break
        if ok: cands.add(i)
    return cands

baseline=select(False,False,0); Ntrials=20
# (a) dedup order only
a=[len(select(False,True,0)) for _ in range(Ntrials)]
# (b) float jitter only
b=[len(select(False,False,0.01)) for _ in range(Ntrials)]
# (c) dedup order + float jitter (full perturbation)
c=[len(select(False,True,0.01)) for _ in range(Ntrials)]
results={'baseline':len(baseline),'dedup_only_mean':float(np.mean(a)),'dedup_only_std':float(np.std(a)),
         'float_only_mean':float(np.mean(b)),'float_only_std':float(np.std(b)),
         'both_mean':float(np.mean(c)),'both_std':float(np.std(c)),
         'Ntrials':Ntrials}
print(f'baseline: {len(baseline)}');print(f'dedup: {np.mean(a):.1f}+-{np.std(a):.1f}')
print(f'float: {np.mean(b):.1f}+-{np.std(b):.1f}');print(f'both: {np.mean(c):.1f}+-{np.std(c):.1f}')
json.dump(results,open('candidate_jitter_decomposition.json','w'),indent=2)
print('Saved -> candidate_jitter_decomposition.json')
