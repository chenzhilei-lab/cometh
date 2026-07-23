#!/usr/bin/env python3
"""
YSO spectral classification grid from ATMO2020 (Phillips+2020) CEQ model spectra.
Computes F210M and F360M synthetic magnitudes for all available model spectra
using real NIRCam filter transmission curves, then maps the F210M-F360M colour
as a function of Teff and log g to determine where planetary-mass objects,
brown dwarfs, and low-mass stars fall in colour space.

The output is an objective, spectroscopically grounded replacement for the
purely empirical F210M-F360M=1.5 threshold used in the paper.
"""
import numpy as np, glob, os, json, warnings, urllib.request
warnings.filterwarnings('ignore')

BASE = r'D:\Papers\NatureTop0630\JWST_FFP'
SPECDIR = os.path.join(BASE, 'atmosphere_models', 'CEQ_spectra')
OUT = os.path.join(BASE, 'yso_spectral_grid.json')

# ── Step 1: Load NIRCam filter transmission curves ──
# Already downloaded from SVO earlier; store locally as simple (wl_um, transmission) arrays
# F210M and F360M from earlier fetch: stored in sed_output/ or we recompute from SVO data
# Use the SVO filter data we already have
filter_data = {}
for name, fid in [('F210M','JWST/NIRCam.F210M'), ('F360M','JWST/NIRCam.F360M')]:
    url = f'http://svo2.cab.inta-csic.es/svo/theory/fps/getdata.php?format=ascii&id={fid}'
    try:
        with urllib.request.urlopen(url, timeout=20) as r:
            text = r.read().decode()
        wl, tx = [], []
        for line in text.split('\n'):
            if line.strip() and not line.startswith('#'):
                p = line.split()
                if len(p) >= 2:
                    wl.append(float(p[0])/1e4)  # Angstrom -> micron
                    tx.append(float(p[1]))
        if wl: filter_data[name] = (np.array(wl), np.array(tx))
    except Exception as e:
        print(f'  {name}: SVO fetch failed: {e}')
        # fallback: approximate rectangular filters
        if name == 'F210M': filter_data[name] = (np.linspace(1.8,2.4,100), np.ones(100))
        if name == 'F360M': filter_data[name] = (np.linspace(3.2,4.0,100), np.ones(100))

# ── Step 2: Load ATMO2020 CEQ spectra ──
spec_files = sorted(glob.glob(os.path.join(SPECDIR, 'spec_T*_CEQ.txt')))
print(f'ATMO2020 CEQ spectra found: {len(spec_files)}')

def load_spectrum(fpath):
    """Return (wl_um, fnu_arbitrary). ATMO spectra are: wl[micron], flam[W/m2/micron].
    Convert flam -> fnu (flam * wl^2) for synthetic photometry."""
    a = np.genfromtxt(fpath, comments='#')
    if a.ndim == 1: a = a[None, :]
    wl = a[:,0]  # micron
    flam = a[:,1]  # W/m2/micron
    fnu = flam * wl**2  # shape proxy for f_nu
    return wl, fnu

# ── Step 3: Synthetic photometry ──
def synth_mag(wl_spec, fnu_spec, filt_wl, filt_tx):
    """AB magnitude from spectrum integrated through filter."""
    fnu_interp = np.interp(filt_wl, wl_spec, fnu_spec, left=0, right=0)
    num = np.trapezoid(fnu_interp * filt_tx / filt_wl, filt_wl)
    den = np.trapezoid(filt_tx / filt_wl, filt_wl)
    fnu_avg = num/den if den > 0 else 1e-30
    return -2.5*np.log10(max(fnu_avg, 1e-30)) - 48.60

# ── Step 4: Process all spectra ──
results = []
for fp in spec_files:
    fname = os.path.basename(fp)
    # parse Teff and log g from filename: spec_T1000_lg3.5_CEQ.txt
    teff = int(fname.split('_')[1][1:])  # 'T1000' -> 1000
    logg = float(fname.split('_')[2][2:])  # 'lg3.5' -> 3.5
    wl, fnu = load_spectrum(fp)
    mags = {}
    for band in ['F210M', 'F360M']:
        fw, ft = filter_data[band]
        mags[band] = synth_mag(wl, fnu, fw, ft)
    c23 = mags['F210M'] - mags['F360M']
    # classify: low-gravity (logg <= 4.0) = planetary-mass; logg 4.0-5.0 = brown dwarf; logg>5.0 = stellar
    if logg <= 4.0: category = 'planetary'
    elif logg <= 5.0: category = 'brown_dwarf'
    else: category = 'stellar'
    results.append({'Teff': teff, 'logg': logg, 'category': category,
                    'F210M_synth': round(float(mags['F210M']), 3),
                    'F360M_synth': round(float(mags['F360M']), 3),
                    'F210M_F360M': round(float(c23), 3)})
    print(f"  Teff={teff:5d}K logg={logg:.1f} -> F210M-F360M={c23:.2f}  ({category})")

# ── Step 5: Determine objective classification boundaries ──
planetary = [r['F210M_F360M'] for r in results if r['category'] == 'planetary']
bd = [r['F210M_F360M'] for r in results if r['category'] == 'brown_dwarf']
stellar = [r['F210M_F360M'] for r in results if r['category'] == 'stellar']
print(f'\n=== Spectral-grid colour boundaries ===')
if planetary:
    print(f'  Planetary (log g<=4.0):  F210M-F360M = [{min(planetary):.2f}, {max(planetary):.2f}]  median {np.median(planetary):.2f}')
if bd:
    print(f'  Brown dwarf (log g 4-5): F210M-F360M = [{min(bd):.2f}, {max(bd):.2f}]  median {np.median(bd):.2f}')
if stellar:
    print(f'  Stellar (log g>5):       F210M-F360M = [{min(stellar):.2f}, {max(stellar):.2f}]  median {np.median(stellar):.2f}')

# objective threshold: upper envelope of planetary + lower envelope of BD
if planetary and bd:
    plan_max = max(planetary); bd_min = min(bd)
    threshold = (plan_max + bd_min)/2
    print(f'\n  Objective planetary/BD colour boundary: {threshold:.2f}')
    print(f'  (contrast with empirical F210M-F360M=1.5 used in paper)')

json.dump({'spectra': results, 'planetary_range': [float(min(planetary)), float(max(planetary))] if planetary else [],
           'bd_range': [float(min(bd)), float(max(bd))] if bd else [],
           'stellar_range': [float(min(stellar)), float(max(stellar))] if stellar else [],
           'objective_threshold': float(threshold) if (planetary and bd) else None},
          open(OUT, 'w'), indent=2)
print(f'\nSaved -> {OUT}')
