# RAA-FFP: Phantom FFP Candidates from Archival JWST Pipelines

## Overview

This repository contains the complete analysis pipeline, data products, and reproducibility tests for the manuscript:

> **Phantom multi-band free-floating planet candidates from archival JWST pipelines: Quantifying photometric and crowding systematics that collapse 31 candidates to zero robust detections**

submitted to *Research in Astronomy and Astrophysics (RAA)*.

The paper demonstrates that naive archival JWST NIRCam pipelines systematically manufacture spurious free-floating planet (FFP) candidates in crowded star-forming regions. Two failure modes are identified and quantified analytically:
1. **Photometric miscalibration** — a fixed 1.549 mag cross-detector colour bias from using a single zero-point across SW/LW detectors with different pixel solid angles
2. **Cross-match blending** — Poisson neighbour misassignment at a rate P = 1 − exp(−ρπr²), reaching 26% in dense cores

## Repository Structure

```
├── scripts/                  # Core analysis scripts
│   ├── run_serpens_proper.py          # Physically calibrated pipeline
│   ├── ablation_experiment.py         # 2×2 ablation experiment
│   ├── yso_spectral_grid.py           # ATMO2020 spectral classification
│   ├── eight_detector_completeness.py # 8-detector differential completeness
│   ├── coupled_mc_real_catalog.py     # 3-way coupled contamination MC
│   ├── decompose_candidate_jitter.py  # KDTree/dedup/float decomposition
│   ├── c09_forced_4band.py            # C09 forced aperture photometry
│   └── reproducibility_tracing.py     # Reproducibility perturbation test
├── data/                     # Output data products (JSON)
│   ├── serpens_candidates.json        # Naive pipeline 31-candidate catalogue
│   ├── serpens_results.json           # Pipeline detection statistics
│   ├── c09_snr_comparison.json        # C09 SNR comparison
│   ├── c09_sharpness_full.json        # C09 morphology
│   ├── simbad_verification_full.json  # SIMBAD cross-match verification
│   ├── aperture_corrections.json      # Per-band empirical aperture corrections
│   ├── yso_spectral_grid.json         # ATMO2020 model colour boundaries
│   ├── eight_detector_completeness.json # Per-detector relative completeness
│   ├── candidate_jitter_decomposition.json # 3-way decomposition results
│   └── coupled_mc_real_catalog.json   # Coupled contamination rates
├── figures/                  # Supplementary figures
│   ├── paper_framework_mindmap.png    # Paper framework overview
│   └── version_evolution_7701_to_7776.png # Version evolution timeline
└── requirements.txt          # Python environment specification
```

## Reproducibility

All results reported in the paper can be reproduced by running the scripts in order:

1. `run_serpens_proper.py` — Runs the physically calibrated pipeline on the GO-1611 i2d images
2. `ablation_experiment.py` — Runs the 2×2 ablation experiment
3. `yso_spectral_grid.py` — Computes ATMO2020-based colour boundaries
4. `eight_detector_completeness.py` — Measures per-detector differential completeness
5. `coupled_mc_real_catalog.py` — Runs the 3-way coupled contamination Monte Carlo
6. `decompose_candidate_jitter.py` — Decomposes candidate-count instability
7. `c09_forced_4band.py` — Performs forced aperture photometry on C09
8. `reproducibility_tracing.py` — Traces run-to-run variation to dedup ordering

### Requirements

```bash
pip install -r requirements.txt
```

Key dependencies: `numpy`, `scipy`, `astropy`, `photutils`, `matplotlib`, `astroquery`

### Data Access

The JWST NIRCam i2d images (GO-1611, Serpens Main) are publicly available at the Mikulski Archive for Space Telescopes (MAST): https://mast.stsci.edu

Filter transmission curves are from the SVO Filter Profile Service: http://svo2.cab.inta-csic.es

ATMO2020 model atmospheres (Phillips et al. 2020) are from: http://perso.ens-lyon.fr/isabelle.baraffe/ATMO2020/

## Version History

The full version chain from initial FFP candidate search (v7701) to final submission (v7779) is archived in the evidence package at Zenodo (DOI: 10.5281/zenodo.21287544). The paper was originally a free-floating planet candidate search and pivoted to a methods cautionary paper after reproducibility testing revealed the two failure modes.

## License

This repository is provided for reproducibility purposes. Reuse of code and data with attribution is permitted.
