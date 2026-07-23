#!/usr/bin/env python3
"""Code-level reproducibility tracing: show that the run-to-run candidate variation
(31 vs 14) originates in the greedy deduplication + nearest-neighbour cross-match,
which are sensitive to sub-0.01 mag numerical differences (float precision, data
staging, library versions). We detect once, then run the naive 0.5\" selection N
times with tiny magnitude perturbations (sigma=0.01 mag, far below photometric
error) and record how the candidate set fluctuates. Stable candidates recur in
every trial; unstable ones flip in and out and sit in the crowded clumps."""
import numpy as np, warnings, json, os
from collections import defaultdict, Counter
warnings.filterwarnings('ignore')
from astropy.io import fits
from astropy.wcs import WCS
from astropy.stats import sigma_clipped_stats
from photutils.detection import DAOStarFinder
from scipy.spatial import cKDTree
import pandas as pd

DATA=r'D:\JWST_FFP\serpens'; ZPT=26.5; TILE=3000
MAGLIM={'F140M':26.0,'F210M':27.0,'F360M':25.5,'F480M':25.0}
COLOR={'F140M_F210M':(-0.3,2.0),'F210M_F360M':(0.3,2.5),'F360M_F480M':(-0.2,1.5)}

fbf=defaultdict(list)
for fn in sorted(os.listdir(DATA)):
    if fn.endswith('.fits') and 'i2d' in fn:
        f=fits.getheader(os.path.join(DATA,fn),0).get('FILTER','')
        if f in MAGLIM: fbf[f].append(os.path.join(DATA,fn))

# detect once: positions + naive mag per band
raw={}
for filt in ['F140M','F210M','F360M','F480M']:
    xs,ys,fl=[],[],[]
    for fp in fbf[filt]:
        with fits.open(fp,memmap=True) as h:
            sci=np.asarray(h['SCI'].data,float); w=WCS(h['SCI'].header)
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
                xs+=list(ra);ys+=list(dec);fl+=list(np.array(s['flux']))
    raw[filt]=(np.array(xs),np.array(ys),-2.5*np.log10(np.maximum(np.array(fl),1e-10))+ZPT)
    print(f"{filt}: {len(xs)} raw")

def select(perturb, rng):
    cats={}
    for filt in ['F140M','F210M','F360M','F480M']:
        ra,dec,mag=raw[filt]
        if perturb: mag=mag+rng.normal(0,0.01,len(mag))   # sub-0.01 mag numerical jitter
        m=mag<MAGLIM[filt]; ra,dec,mag=ra[m],dec[m],mag[m]
        co=np.radians(np.column_stack([ra,dec])); tr=cKDTree(co); keep=set();seen=set()
        for i in np.argsort(mag):                          # greedy dedup: brightest first
            if i in seen: continue
            for j in tr.query_ball_point(co[i],0.3/206265): seen.add(j)
            keep.add(i)
        k=sorted(keep); cats[filt]=(ra[k],dec[k],mag[k])
    rra,rdec,rmag=cats['F210M']; trees={f:cKDTree(np.radians(np.column_stack(cats[f][:2]))) for f in cats}
    cands=[]
    for i in range(len(rra)):
        q=np.radians([[rra[i],rdec[i]]]); mm={'F210M':rmag[i]}; ok=True
        for f in ['F140M','F360M','F480M']:
            d,idx=trees[f].query(q)
            if float(d[0])>0.5/206265: ok=False;break
            mm[f]=cats[f][2][int(np.atleast_1d(idx[0])[0])]
        if not ok: continue
        for cn,(lo,hi) in COLOR.items():
            f1,f2=cn.split('_')
            if not (COLOR[cn][0]<mm[f1]-mm[f2]<COLOR[cn][1]): ok=False;break
        if ok: cands.append((round(rra[i],5),round(rdec[i],5)))
    return set(cands)

rng=np.random.default_rng(0)
base=select(False,rng)
counts=[]; allc=Counter()
N=20
for t in range(N):
    s=select(True,rng); counts.append(len(s)); allc.update(s)
counts=np.array(counts)
stable=[k for k,v in allc.items() if v==N]; unstable=[k for k,v in allc.items() if 0<v<N]
print(f"\n=== reproducibility tracing (N={N} runs, 0.01 mag jitter) ===")
print(f"  unperturbed candidates: {len(base)}")
print(f"  perturbed count: mean {counts.mean():.1f}, range [{counts.min()}, {counts.max()}], std {counts.std():.1f}")
print(f"  candidates appearing in ALL {N} runs (stable): {len(stable)}")
print(f"  candidates flipping in/out (unstable): {len(unstable)}")
print(f"  => a 0.01 mag numerical jitter---far below the {1.0857/15.7:.2f} mag photometric error---")
print(f"     moves {len(unstable)} candidates in or out through the greedy dedup + 0.5\" match.")
json.dump({'N':N,'base':len(base),'mean':float(counts.mean()),'min':int(counts.min()),
           'max':int(counts.max()),'std':float(counts.std()),'stable':len(stable),'unstable':len(unstable)},
          open(r'D:\Papers\NatureTop0630\JWST_FFP\reproducibility_tracing.json','w'),indent=2)
print("Saved -> reproducibility_tracing.json")
