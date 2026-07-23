#!/usr/bin/env python3
"""C09 body -- definitive FORCED aperture photometry at its exact SW coordinate
in all four bands (no KDTree cross-match; avoids the 0.41" bright neighbour).
Consistent method: r=0.20" aperture, per-band empirical aperture correction,
sky annulus 0.7-1.0". Then ATMO2020 mass from the corrected F210M.
NOTE: F360M/F480M forced values are contaminated by the wing of the bright
neighbour 0.41" away -> they are upper limits on C09's true LW brightness."""
import numpy as np, warnings, json, glob
warnings.filterwarnings('ignore')
from astropy.io import fits
from astropy.wcs import WCS
from photutils.aperture import CircularAperture, CircularAnnulus, aperture_photometry, ApertureStats
from scipy.interpolate import LinearNDInterpolator

RA, DEC = 277.450081, 1.231493
DIR = r'D:\JWST_FFP\serpens'
APCORR = json.load(open(r'D:\Papers\NatureTop0630\JWST_FFP\aperture_corrections.json'))
ABV = {'F140M':1.124,'F210M':1.806,'F360M':2.862,'F480M':3.436}
FILES = {'F140M':'jw01611002001_02101_00005_nrcb3_i2d.fits',
         'F210M':'jw01611002001_02103_00005_nrcb3_i2d.fits',
         'F360M':'jw01611002001_02101_00005_nrcblong_i2d.fits',
         'F480M':'jw01611002001_02103_00005_nrcblong_i2d.fits'}

def forced_ab(band):
    fp=f'{DIR}\\{FILES[band]}'
    with fits.open(fp) as h:
        sci=np.asarray(h['SCI'].data,float); hd=h['SCI'].header
        pixar=hd.get('PIXAR_SR',fits.getheader(fp,0).get('PIXAR_SR')); w=WCS(hd)
    scale=np.sqrt(pixar)*206265.0
    x,y=w.all_world2pix(RA,DEC,0); pos=[(float(x),float(y))]
    sk=float(ApertureStats(sci,CircularAnnulus(pos,r_in=0.7/scale,r_out=1.0/scale)).median[0])
    r=0.20/scale; raw=float(aperture_photometry(sci,CircularAperture(pos,r=r))['aperture_sum'][0])
    F=(raw-sk*np.pi*r**2)*1e6*pixar
    return (-2.5*np.log10(F/3631.0) - APCORR[band]) if F>0 else np.nan

mags={b:round(forced_ab(b),2) for b in FILES}
print("C09 body -- forced aperture photometry (AB, aperture-corrected):")
for b in ['F140M','F210M','F360M','F480M']:
    print(f"   {b} = {mags[b]:.2f}")
print(f"\nColours:")
print(f"   F140M-F210M = {mags['F140M']-mags['F210M']:.2f}   (box -0.3..2.0)")
print(f"   F210M-F360M = {mags['F210M']-mags['F360M']:.2f}   (box  0.3..2.5)  [LW contaminated -> lower limit]")
print(f"   F360M-F480M = {mags['F360M']-mags['F480M']:.2f}   (box -0.2..1.5)")

# ATMO2020 mass from corrected F210M
MJUP=1047.57; DM=5*np.log10(436.0)-5
rows=[]
for f in sorted(glob.glob(r'D:\Papers\NatureTop0630\JWST_FFP\evolutionary_tracks\ATMO_CEQ\JWST_photometry\JWST_phot_NIRCAM_modAB_mean\*.txt')):
    a=np.genfromtxt(f,comments='#')
    if a.ndim==1: a=a[None,:]
    for r in a: rows.append((r[0]*MJUP,r[1]*1000,r[2],r[9]))
d=np.array(rows); sel=(d[:,0]<=25)&(d[:,1]>=0.9)&(d[:,1]<=6)
ipm=LinearNDInterpolator(np.column_stack([np.log10(d[sel,0]),np.log10(d[sel,1])]), d[sel,3])
ipt=LinearNDInterpolator(np.column_stack([np.log10(d[sel,0]),np.log10(d[sel,1])]), d[sel,2])
Mvega=(mags['F210M']-ABV['F210M'])-DM
print(f"\nATMO2020 mass from F210M={mags['F210M']} (M_F210M,Vega={Mvega:.2f}):")
mg=np.logspace(np.log10(0.5),np.log10(20),500)
for age in [1.0,2.0,3.0]:
    col=ipm(np.log10(mg),np.log10(age)*np.ones_like(mg)); ok=np.isfinite(col); o=np.argsort(col[ok])
    m=np.interp(Mvega,col[ok][o],mg[ok][o],left=np.nan,right=np.nan)
    t=float(ipt(np.log10(m),np.log10(age))) if np.isfinite(m) else np.nan
    print(f"   age {age:.0f} Myr: mass = {m:.2f} MJup, Teff = {t:.0f} K")
json.dump({'forced_AB':mags,'M_F210M_vega':round(float(Mvega),2)},
          open(r'D:\Papers\NatureTop0630\JWST_FFP\c09_forced_4band.json','w'), indent=2)
print("\nSaved -> c09_forced_4band.json")
