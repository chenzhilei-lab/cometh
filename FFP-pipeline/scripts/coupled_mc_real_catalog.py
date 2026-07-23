#!/usr/bin/env python3
"""Coupl MC with real source positions. Uses serpens_candidates.json
31 sources + real F360M catalogue positions for neighbour tracking."""
import numpy as np, json, warnings
warnings.filterwarnings('ignore')
from scipy.spatial import cKDTree

rng=np.random.default_rng(42); N=50000
cands=json.load(open('serpens_candidates.json'))
# get real F360M positions from the calibrated catalogue
import pandas as pd
from astropy.io import fits
from astropy.stats import sigma_clipped_stats
from photutils.detection import DAOStarFinder
from astropy.wcs import WCS

DATA='D:/JWST_FFP/serpens'; TILE=3000
f360_ra,f360_dec=[],[]
for fn in sorted(__import__('os').listdir(DATA)):
    if 'i2d' not in fn: continue
    f=fits.getheader(f'{DATA}/{fn}',0).get('FILTER','')
    if f!='F360M': continue
    with fits.open(f'{DATA}/{fn}') as h: sci=h['SCI'].data; w=WCS(h['SCI'].header)
    ny,nx=sci.shape; s=sci.astype(float)
    for y0 in range(0,ny,TILE):
        for x0 in range(0,nx,TILE):
            t=s[y0:min(y0+TILE,ny),x0:min(x0+TILE,nx)]
            if np.all(~np.isfinite(t)): continue
            _,med,std=sigma_clipped_stats(t,sigma=3.0)
            if std<=0: continue
            src=DAOStarFinder(fwhm=3.0,threshold=5*std)(t-med)
            if src is None: continue
            xc='xcentroid' if 'xcentroid' in src.colnames else 'x_centroid'
            yc='ycentroid' if 'ycentroid' in src.colnames else 'y_centroid'
            ra,dec=w.all_pix2world(np.array(src[xc])+x0, np.array(src[yc])+y0,0)
            f360_ra+=list(ra); f360_dec+=list(dec)
f360_coords=np.radians(np.column_stack([f360_ra,f360_dec]))
tree360=cKDTree(f360_coords); rho_global=len(f360_ra)/((max(f360_ra)-min(f360_ra))*(max(f360_dec)-min(f360_dec))*3600*3600)
print(f'F360M catalogue: {len(f360_ra)} sources, rho={rho_global:.4f}/sq arcsec')

# build synthetic stars with real density
ra_syn=rng.uniform(min(f360_ra),max(f360_ra),N)
dec_syn=rng.uniform(min(f360_dec),max(f360_dec),N)
idx=rng.choice(len(f360_ra),N) # nearest real source as template
rho_local=np.array([len(tree360.query_ball_point([np.radians(ra_syn[i]),np.radians(dec_syn[i])],5/206265)) for i in range(N)])/(np.pi*25)

c12=rng.normal(-0.3,0.5,N); c23=rng.normal(-0.2,0.4,N); c34=rng.normal(0,0.3,N)
Av=rng.lognormal(np.log(2),0.7,N); Av=np.clip(Av,0,15)
c12+=0.09*Av; c23+=0.04*Av; c34+=0.01*Av
OFFSET=-1.549; SCATTER=0.49
c23=c23+OFFSET+rng.normal(0,SCATTER,N)

box=(-0.3<c12)&(c12<2.0)&(0.3<c23)&(c23<2.5)&(-0.2<c34)&(c34<1.5)
print(f'  post-ext+bias box rate: {float(np.mean(box))*100:.1f}%')

results={}
for r_as in [0.3,0.5]:
    for rho_tag,rho in [('mean',rho_global),('med',np.median(rho_local)),('p90',np.percentile(rho_local,90))]:
        P=1-np.exp(-rho*np.pi*r_as**2)
        c23b=c23.copy(); blended=rng.random(N)<P
        if np.any(blended): c23b[blended]+=rng.normal(0.8,0.5,np.sum(blended))
        inbox=(-0.3<c12)&(c12<2.0)&(0.3<c23b)&(c23b<2.5)&(-0.2<c34)&(c34<1.5)
        results[f'r={r_as}"_{rho_tag}']=round(float(np.mean(inbox)*100),2)
        print(f'  r={r_as}" rho={rho:.4f}({rho_tag}) P={P:.3f} -> {results[f"r={r_as}\"_{rho_tag}"]}%')
json.dump(results,open('coupled_mc_real_catalog.json','w'),indent=2)
print('Saved -> coupled_mc_real_catalog.json')
