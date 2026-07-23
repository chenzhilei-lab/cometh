#!/usr/bin/env python3
"""
8-detector SW completeness DIFFERENTIAL measurement.
Instead of injecting artificial stars (which requires correct flux scaling for
each detector's gain/background), we compare the PER-DETECTOR source density
in magnitude bins, normalised to the same sky area, using the real DAOStarFinder
catalogue. The brightest bins serve as a common completeness plateau; the
fractional excess or deficit at fainter bins relative to the ensemble mean
quantifies the per-detector completeness offset.

This is a DIFFERENTIAL completeness matrix: it does not give absolute detection
efficiency, but it shows which detectors are deeper/shallower than the field mean
at each magnitude, enabling a per-detector correction factor.
"""
import numpy as np, warnings, json, os, glob
from collections import defaultdict
warnings.filterwarnings('ignore')
from astropy.io import fits
from astropy.stats import sigma_clipped_stats
from photutils.detection import DAOStarFinder
from scipy.spatial import cKDTree

DATA=r'D:\JWST_FFP\serpens'; FWHM=3.0; THRESH=5.0; TILE=3000; MAGBINS=np.arange(20,27,0.5)

by_det=defaultdict(list)
for fn in sorted(os.listdir(DATA)):
    if not fn.endswith('.fits') or 'i2d' not in fn: continue
    det=fn.split('_')[3]
    f=fits.getheader(os.path.join(DATA,fn),0).get('FILTER','')
    if f=='F210M' and det.startswith('nrc'): by_det[det].append(os.path.join(DATA,fn))

print(f"SW detectors: {len(by_det)}")

# detect per-detector, accumulating into magnitude histograms
det_hist={}; det_npx={}
for det,fps in sorted(by_det.items()):
    mags=[]; total_pix=0
    for fp in fps:
        with fits.open(fp) as h: sci=np.asarray(h['SCI'].data,float)
        ny,nx=sci.shape; total_pix+=ny*nx
        for y0 in range(0,ny,TILE):
            for x0 in range(0,nx,TILE):
                t=sci[y0:min(y0+TILE,ny),x0:min(x0+TILE,nx)]
                if np.all(~np.isfinite(t)): continue
                _,med,std=sigma_clipped_stats(t,sigma=3.0)
                if std<=0: continue
                s=DAOStarFinder(fwhm=FWHM,threshold=THRESH*std)(t-med)
                if s is None: continue
                fl=np.array(s['flux']); m=-2.5*np.log10(np.maximum(fl,1e-10))+26.5
                mags+=list(m)
    hist,_=np.histogram(mags,bins=MAGBINS)
    det_hist[det]=hist; det_npx[det]=total_pix
    print(f"  {det}: {len(mags)} sources over {total_pix/1e6:.1f} Mpx ({len(fps)} frames)")

# normalise to per-Mpx source density
ref_area=min(det_npx.values())
dens={d:det_hist[d]/det_npx[d]*ref_area for d in det_hist}
# field mean density per bin
mean_dens=np.mean([v for v in dens.values()],axis=0)
# per-detector relative completeness (ratio to mean, bright-bin normalised)
bright_baseline=np.mean([dens[d][:4] for d in dens],axis=0)  # bins 20-22 (bright)
correction={}
for d in dens:
    rel=dens[d]/np.maximum(mean_dens,1)  # relative to mean
    corr=rel/np.mean(rel[:4])  # normalise to bright end = 1.0
    correction[d]=list(corr)
print(f"\nPer-detector relative completeness (bright-normalised):")
print(f"{'det':8s}", ' '.join([f'{m:.1f}' for m in MAGBINS[:-1]]))
for d in sorted(correction):
    print(f"{d:8s}", ' '.join([f'{v:.3f}' for v in correction[d]]))
print(f"\nStd dev among detectors per bin:")
stds=[np.std([correction[d][i] for d in correction]) for i in range(len(MAGBINS)-1)]
for m,s in zip(MAGBINS[:-1],stds): print(f"  {m:.1f}: {s:.3f}")

json.dump({'per_detector_correction':{d:list(c) for d,c in correction.items()},
           'magnitude_bins':list(MAGBINS[:-1]),'std_dev_per_bin':stds},
          open(r'D:\Papers\NatureTop0630\JWST_FFP\eight_detector_completeness.json','w'), indent=2)
print("Saved -> eight_detector_completeness.json")
