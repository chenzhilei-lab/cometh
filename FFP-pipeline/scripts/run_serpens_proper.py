#!/usr/bin/env python3
"""
Serpens FFP pipeline -- PROPER photometric calibration (supersedes run_serpens_full_v7701.py).
Fix: catalogue used mag = -2.5log10(DAOStarFinder_flux) + 26.5 (instrumental flux,
arbitrary single zero-point across SW/LW detectors -> cross-SW/LW colours wrong by
2.5log10(PIXAR_SR_LW/SW) = 1.549 mag). Here we do physical aperture photometry:
  F[Jy] = sum(SB[MJy/sr]) * 1e6 * PIXAR_SR[sr/pix], sky-subtracted, aperture-corrected,
  AB = -2.5log10(F/3631).  Detection / dedup / cross-match / colour box unchanged.
"""
import numpy as np, warnings, json, os
from collections import defaultdict
warnings.filterwarnings('ignore')
from astropy.io import fits
from astropy.wcs import WCS
from astropy.stats import sigma_clipped_stats
from photutils.detection import DAOStarFinder
from photutils.aperture import CircularAperture, CircularAnnulus, aperture_photometry, ApertureStats
from scipy.spatial import cKDTree
import pandas as pd

DATA = r'D:\JWST_FFP\serpens'
OUT  = r'D:\Papers\NatureTop0630\JWST_FFP\serpens_proper'
os.makedirs(OUT, exist_ok=True)
APCORR = json.load(open(r'D:\Papers\NatureTop0630\JWST_FFP\aperture_corrections.json'))
R_AP, SKY = 0.20, (0.70, 1.00)
COLOR_LIMITS = {'F140M_F210M': (-0.3, 2.0), 'F210M_F360M': (0.3, 2.5), 'F360M_F480M': (-0.2, 1.5)}
MAG_LIM = {'F140M':26.0, 'F210M':26.0, 'F360M':25.0, 'F480M':25.0}  # AB faint cut
FWHM, THRESH, TILE, MATCH_TOL = 3.0, 5.0, 3000, 0.3  # tightened 0.5->0.3": require independent per-band detection

def phot_ab(sci, pixar, scale, xs, ys):
    pos = list(zip(xs, ys))
    r = R_AP/scale
    sky = np.asarray(ApertureStats(sci, CircularAnnulus(pos, r_in=SKY[0]/scale, r_out=SKY[1]/scale)).median)
    raw = np.asarray(aperture_photometry(sci, CircularAperture(pos, r=r))['aperture_sum'])
    F = (raw - sky*np.pi*r**2)*1e6*pixar
    with np.errstate(invalid='ignore', divide='ignore'):
        return np.where(F>0, -2.5*np.log10(F/3631.0), np.nan)

# scan files by filter
fbf = defaultdict(list)
for fn in sorted(os.listdir(DATA)):
    if fn.endswith('.fits') and 'i2d' in fn:
        filt = fits.getheader(os.path.join(DATA, fn), 0).get('FILTER','')
        if filt in APCORR: fbf[filt].append(os.path.join(DATA, fn))
print('Files by filter:', {k:len(v) for k,v in fbf.items()})

catalogs = {}
for filt in ['F140M','F210M','F360M','F480M']:
    det = []
    for fp in fbf.get(filt, []):
        with fits.open(fp, memmap=True) as h:
            sci = np.asarray(h['SCI'].data, float); hd = h['SCI'].header
            pixar = hd.get('PIXAR_SR', fits.getheader(fp,0).get('PIXAR_SR'))
            w = WCS(hd)
        scale = np.sqrt(pixar)*206265.0; ny, nx = sci.shape
        xs_all, ys_all, sh_all = [], [], []
        for y0 in range(0, ny, TILE):
            for x0 in range(0, nx, TILE):
                tile = sci[y0:min(y0+TILE,ny), x0:min(x0+TILE,nx)]
                if np.all(~np.isfinite(tile)): continue
                _, med, std = sigma_clipped_stats(tile, sigma=3.0)
                if std<=0: continue
                s = DAOStarFinder(fwhm=FWHM, threshold=THRESH*std)(tile-med)
                if s is None: continue
                xs_all += list(np.array(s['xcentroid'])+x0)
                ys_all += list(np.array(s['ycentroid'])+y0)
                sh_all += list(np.array(s['sharpness']))
        if not xs_all: continue
        mag = phot_ab(sci, pixar, scale, xs_all, ys_all) - APCORR[filt]  # aperture-corrected AB
        ra, dec = w.all_pix2world(np.array(xs_all), np.array(ys_all), 0)
        det.append(pd.DataFrame({'ra':ra,'dec':dec,'mag':mag,'sharpness':sh_all}))
    if not det: continue
    cat = pd.concat(det, ignore_index=True)
    cat = cat[np.isfinite(cat['mag']) & (cat['mag'] < MAG_LIM[filt])].reset_index(drop=True)
    # dedup overlapping detectors (0.3"), keep brightest
    if len(cat) > 1:
        c = np.radians(cat[['ra','dec']].values); tree = cKDTree(c); tol=0.3/206265; keep=set(); seen=set()
        order = np.argsort(cat['mag'].values)  # brightest first
        for i in order:
            if i in seen: continue
            for j in tree.query_ball_point(c[i], tol): seen.add(j)
            keep.add(i)
        cat = cat.iloc[sorted(keep)].reset_index(drop=True)
    catalogs[filt] = cat
    print(f'{filt}: {len(cat)} sources (AB, aperture-corrected)')

# cross-match on F210M
ref = catalogs['F210M']; tol=MATCH_TOL/206265
trees = {f:cKDTree(np.radians(catalogs[f][['ra','dec']].values)) for f in catalogs}
matched = []
for i, s in ref.iterrows():
    sd = {'id':f'SRC-{i:06d}','ra':round(float(s['ra']),6),'dec':round(float(s['dec']),6),
          'F210M_mag':round(float(s['mag']),3),'F210M_sharpness':round(float(s['sharpness']),3)}
    ok=True
    for f in catalogs:
        if f=='F210M': continue
        d,idx = trees[f].query(np.radians([[s['ra'],s['dec']]]))
        if float(d[0]) > tol: ok=False; break
        j=int(np.atleast_1d(idx[0])[0]); sd[f'{f}_mag']=round(float(catalogs[f].iloc[j]['mag']),3)
        sd[f'{f}_sharpness']=round(float(catalogs[f].iloc[j]['sharpness']),3)
    if ok: matched.append(sd)
print(f'\nMatched in all 4 bands: {len(matched)}')

# colour selection
cands, bg = [], []
for src in matched:
    ok=True
    for cn,(lo,hi) in COLOR_LIMITS.items():
        f1,f2=cn.split('_'); col=src[f'{f1}_mag']-src[f'{f2}_mag']
        if not (lo<col<hi): ok=False; break
    (cands if ok else bg).append(src)
print(f'FFP candidates: {len(cands)}   background: {len(bg)}')

json.dump({'n_sources':{k:len(v) for k,v in catalogs.items()},'n_matched':len(matched),
           'n_candidates':len(cands),'n_background':len(bg)}, open(f'{OUT}\\serpens_results.json','w'), indent=2)
json.dump(cands, open(f'{OUT}\\serpens_candidates.json','w'), indent=2)
json.dump(bg, open(f'{OUT}\\serpens_background.json','w'), indent=2)

# C09 tracking: find the F210M source CLOSEST to C09's exact coord (not just any within 0.5")
print('\n--- C09 (RA=277.4501, Dec=1.2315): closest F210M detections ---')
c09c = np.radians([[277.450081, 1.231493]])
dref, iref = cKDTree(np.radians(ref[['ra','dec']].values)).query(c09c, k=3)
for rank in range(3):
    j = int(np.atleast_1d(iref[0])[rank]); sep = float(np.atleast_1d(dref[0])[rank])*206265
    s = ref.iloc[j]
    # is this F210M source in the 4-band matched set?
    mid = f'SRC-{j:06d}'
    m = next((x for x in matched if x['id']==mid), None)
    if m:
        status = f"4-band matched, F210M-F360M={m['F210M_mag']-m['F360M_mag']:.2f}, candidate={'YES' if m in cands else 'NO'}"
    else:
        status = "NOT 4-band matched (no independent LW detection within 0.3\")"
    print(f"  sep={sep:.3f}\"  F210M={s['mag']:.2f}  sharp={s['sharpness']:.2f}  -> {status}")

print(f'\n--- The {len(cands)} surviving candidates ---')
for c in cands:
    print(f"  {c['id']}: RA={c['ra']:.4f} Dec={c['dec']:.4f} F210M={c['F210M_mag']} "
          f"F140M-F210M={c['F140M_mag']-c['F210M_mag']:.2f} "
          f"F210M-F360M={c['F210M_mag']-c['F360M_mag']:.2f} "
          f"F360M-F480M={c['F360M_mag']-c['F480M_mag']:.2f}")
print(f'\nSaved -> {OUT}')
