#!/usr/bin/env python3
"""Ablation experiment: decompose the 31->2 collapse into the contributions of
(a) photometric calibration and (b) cross-match radius. 2x2 factorial:
  photometry in {naive: DAOflux+zpt=26.5;  calibrated: aperture+PIXAR_SR+apcorr}
  match radius in {0.5", 0.3"}   (matching against per-band detection catalogues,
                                  so the radius sets how stringently an independent
                                  per-band detection is required).
Detection is done once per band; each cell only re-cross-matches (fast)."""
import numpy as np, warnings, json, glob, os
from collections import defaultdict
warnings.filterwarnings('ignore')
from astropy.io import fits
from astropy.wcs import WCS
from astropy.stats import sigma_clipped_stats
from photutils.detection import DAOStarFinder
from photutils.aperture import CircularAperture, CircularAnnulus, aperture_photometry, ApertureStats
from scipy.spatial import cKDTree
import pandas as pd

DATA=r'D:\JWST_FFP\serpens'
APCORR=json.load(open(r'D:\Papers\NatureTop0630\JWST_FFP\aperture_corrections.json'))
ZPT=26.5; TILE=3000
COLOR={'F140M_F210M':(-0.3,2.0),'F210M_F360M':(0.3,2.5),'F360M_F480M':(-0.2,1.5)}
MAGLIM_NAIVE={'F140M':26.0,'F210M':27.0,'F360M':25.5,'F480M':25.0}
MAGLIM_CAL={'F140M':26.0,'F210M':26.0,'F360M':25.0,'F480M':25.0}

fbf=defaultdict(list)
for fn in sorted(os.listdir(DATA)):
    if fn.endswith('.fits') and 'i2d' in fn:
        f=fits.getheader(os.path.join(DATA,fn),0).get('FILTER','')
        if f in APCORR: fbf[f].append(os.path.join(DATA,fn))

# detect once per band -> pos, naive mag, calibrated mag
cats={}
for filt in ['F140M','F210M','F360M','F480M']:
    rows=[]
    for fp in fbf[filt]:
        with fits.open(fp,memmap=True) as h:
            sci=np.asarray(h['SCI'].data,float); hd=h['SCI'].header
            pixar=hd.get('PIXAR_SR',fits.getheader(fp,0).get('PIXAR_SR')); w=WCS(hd)
        scale=np.sqrt(pixar)*206265.0; ny,nx=sci.shape
        xs,ys,fl=[],[],[]
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
                xs+=list(np.array(s[xc])+x0); ys+=list(np.array(s[yc])+y0); fl+=list(np.array(s['flux']))
        if not xs: continue
        xs=np.array(xs);ys=np.array(ys);fl=np.array(fl)
        naive=-2.5*np.log10(np.maximum(fl,1e-10))+ZPT
        pos=list(zip(xs,ys)); r=0.20/scale
        sky=np.asarray(ApertureStats(sci,CircularAnnulus(pos,r_in=0.7/scale,r_out=1.0/scale)).median)
        raw=np.asarray(aperture_photometry(sci,CircularAperture(pos,r=r))['aperture_sum'])
        F=(raw-sky*np.pi*r**2)*1e6*pixar
        with np.errstate(all='ignore'):
            cal=np.where(F>0,-2.5*np.log10(F/3631.0),np.nan)-APCORR[filt]
        ra,dec=w.all_pix2world(xs,ys,0)
        rows.append(pd.DataFrame({'ra':ra,'dec':dec,'naive':naive,'cal':cal,'flux':fl}))
    cats[filt]=pd.concat(rows,ignore_index=True)
    print(f'{filt}: {len(cats[filt])} raw detections')

def run_cell(photmode, radius):
    magcol = 'naive' if photmode=='naive' else 'cal'
    maglim = MAGLIM_NAIVE if photmode=='naive' else MAGLIM_CAL
    tol=radius/206265
    # per-band filtered+deduped catalogues
    bcat={}
    for f in cats:
        c=cats[f]; c=c[np.isfinite(c[magcol]) & (c[magcol]<maglim[f])].reset_index(drop=True)
        if len(c)>1:
            co=np.radians(c[['ra','dec']].values); tr=cKDTree(co); keep=set(); seen=set()
            for i in np.argsort(c[magcol].values):
                if i in seen: continue
                for j in tr.query_ball_point(co[i],0.3/206265): seen.add(j)
                keep.add(i)
            c=c.iloc[sorted(keep)].reset_index(drop=True)
        bcat[f]=c
    ref=bcat['F210M']; trees={f:cKDTree(np.radians(bcat[f][['ra','dec']].values)) for f in bcat}
    ncand=0
    for _,s in ref.iterrows():
        m={'F210M':s[magcol]}; ok=True
        for f in bcat:
            if f=='F210M': continue
            d,idx=trees[f].query(np.radians([[s['ra'],s['dec']]]))
            if float(d[0])>tol: ok=False; break
            m[f]=bcat[f].iloc[int(np.atleast_1d(idx[0])[0])][magcol]
        if not ok: continue
        for cn,(lo,hi) in COLOR.items():
            f1,f2=cn.split('_'); col=m[f1]-m[f2]
            if not (lo<col<hi): ok=False; break
        if ok: ncand+=1
    return ncand

print("\n=== 2x2 ablation: candidate count ===")
res={}
for pm in ['naive','calibrated']:
    for r in [0.5,0.3]:
        n=run_cell(pm,r); res[f'{pm}_{r}']=n
        print(f'  photometry={pm:10s} radius={r}\"  -> {n} candidates')
print("\n=== decomposition ===")
print(f"  baseline (naive, 0.5\")          : {res['naive_0.5']}")
print(f"  effect of calibration alone     : {res['naive_0.5']} -> {res['calibrated_0.5']}  (Delta={res['naive_0.5']-res['calibrated_0.5']})")
print(f"  effect of 0.3\" match alone       : {res['naive_0.5']} -> {res['naive_0.3']}  (Delta={res['naive_0.5']-res['naive_0.3']})")
print(f"  both (fully corrected)          : {res['calibrated_0.3']}")
json.dump(res,open(r'D:\Papers\NatureTop0630\JWST_FFP\ablation_experiment.json','w'),indent=2)
print("Saved -> ablation_experiment.json")
