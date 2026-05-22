"""
Download 2I/Borisov archival data for same-data comparison.
Handles MAST (HST) via astroquery + provides ESO manual instructions.

Usage: python download_borisov.py
  - Resumes partial downloads automatically (checks for existing files)
  - Download ~2 GB total; may take hours on slow connections
"""

import os, sys, time
import numpy as np
from astroquery.mast import Observations

OUTDIR = os.path.join(os.path.dirname(__file__), "borisov_data")
os.makedirs(OUTDIR, exist_ok=True)

# ============================================================
# HST Data from MAST
# ============================================================
print("=" * 60)
print("Downloading HST 2I/Borisov data from MAST")
print("=" * 60)

# Confirmed proposals that observed 2I/Borisov
PROPOSALS = {
    '16009': 'Jewitt — WFC3/UVIS F350LP (nucleus detection)',
    '16044': 'Jewitt — ACS/WFC F475W/F606W/F775W (coma morphology)',
    '16041': 'Jewitt — WFC3/UVIS F350LP (follow-up)',
}

all_obs = []
for pid, desc in PROPOSALS.items():
    try:
        obs = Observations.query_criteria(proposal_id=pid, obs_collection='HST')
        if obs is not None and len(obs) > 0:
            all_obs.append(obs)
            print(f"  Proposal {pid} ({desc}): {len(obs)} obs")
    except Exception as e:
        print(f"  Proposal {pid}: ERROR — {e}")

if not all_obs:
    print("ERROR: No HST data found. Check network connection.")
    sys.exit(1)

from astropy.table import vstack
all_data = vstack(all_obs)
print(f"\nTotal: {len(all_data)} HST observations")

# Get products
print("Querying available data products...")
products = Observations.get_product_list(all_data)
print(f"Total products available: {len(products)}")

# Download calibrated science frames (FLC = CTE-corrected, flat-fielded)
mask = np.array([str(f).endswith('flc.fits') for f in products['productFilename']])
calib = products[mask]
if len(calib) == 0:
    mask = np.array([str(f).endswith('flt.fits') for f in products['productFilename']])
    calib = products[mask]
print(f"Calibrated science frames to download: {len(calib)}")

# Download (will skip existing files via cache=True)
if len(calib) > 0:
    print(f"Starting download ({len(calib)} files)...")
    print("(This may take 30-60 minutes. Already-downloaded files will be skipped.)")
    t0 = time.time()
    try:
        manifest = Observations.download_products(
            calib,
            download_dir=OUTDIR,
            cache=True  # skip existing
        )
        elapsed = time.time() - t0
        print(f"Download phase complete ({elapsed:.0f}s).")
    except Exception as e:
        print(f"Download interrupted: {e}")
        print("Re-run this script to resume.")

# Count what we got
fits_files = []
for root, dirs, files in os.walk(OUTDIR):
    for f in files:
        if f.endswith('.fits') or f.endswith('.fits.gz'):
            fits_files.append(os.path.join(root, f))

total_size = sum(os.path.getsize(fp) for fp in fits_files)
print(f"\nDownloaded: {len(fits_files)} FITS files ({total_size/1024/1024:.0f} MB)")

# ============================================================
# ESO Data — Manual Instructions
# ============================================================
print("\n" + "=" * 60)
print("ESO FORS2/MUSE Data — Manual Download Required")
print("=" * 60)
print(f"""
The ESO archive requires browser-based login (Cloudflare-protected).
You need FORS2 R-band images for the same-data Afρ comparison.

Step 1: Go to http://archive.eso.org and register/login (free)

Step 2: Navigate to Science Archive → Raw Data Query

Step 3: Run these queries:

  Query 1 — FORS2 R-band imaging:
    Programme ID: 2104.C-5035
    Instrument: FORS2
    DPR CATG: SCIENCE
    DPR TYPE: IMAGE
    Filter: R_SPECIAL
    → Download all SCIENCE frames

  Query 2 — FORS2 polarimetry:
    Programme ID: 110.23ZJ.001
    Instrument: FORS2
    DPR CATG: SCIENCE
    → Download all SCIENCE frames

Step 4: Save all .fits and .fits.Z files to:
    {outdir}

Step 5: After download, re-run this script — it will count all files.
""".format(outdir=OUTDIR))

# ============================================================
# Final inventory
# ============================================================
print("=" * 60)
print("Data Inventory")
print("=" * 60)
print(f"HST WFC3/ACS calibrated frames: {len(fits_files)} files, {total_size/1024/1024:.0f} MB")
print(f"ESO FORS2 frames: download manually (see instructions above)")
print(f"\nAll data saved to: {OUTDIR}")
print("Done.")
