# Session Log — 2026-05-22

## Phase 1: V4 Review + Critical Fixes

### V4 identified as the working version
- `main_methodology_v4.tex` (1042 lines): Title "COMETH: A Physics-Constrained Multimodal Fusion Framework"
- Key differences from V3: broader framing (§1.1 "Multimodal Fusion Challenge"), compressed abstract (217 words), same cuts as V3 (no RL/GAN/BNN/Neural ODE, no Migration Guide)

### 12 issues found and fixed in V4:

| # | Issue | Location | Fix |
|---|-------|----------|-----|
| 1 | Conclusions claimed unimplemented "layered PINN architecture supporting non-spherical grains" | L1028 | Removed; changed "six innovations" → "five innovations" |
| 2 | §1.4 residual RL extension reference | L69 | Removed RL extension + layered PINN from innovation list; "six" → "five" |
| 3 | Hale-Bopp called "most CO-rich solar system comet" — C/2016 R2 is more extreme | L751, L753 | Changed to "among the most CO-rich"; cited biver18 for C/2016 R2 |
| 4 | 4 truncated `\tablecomments` (tab:ood_perf, tab:hyperparams, tab:timing, tab:key_numbers) | Multiple | Completed text + closed braces |
| 5 | 1 additional truncated `\tablecomments` (tab:traditional_comparison) | L834 | Completed + closed |
| 6 | tab:grain_sensitivity missing column headers + wrong column count | L998-1001 | Added 5-column header; `{lccc}` → `{lcccc}` |
| 7 | tab:key_numbers header copied from wrong table (grain_sensitivity) | L929-932 | Replaced with correct 3-column header |
| 8 | 3I/ATLAS paragraph: 8+ specific claims without citations | L49 | Added `\citep{jewitt25}` for HST nucleus; added FIXME comment for 7 remaining claims |
| 9 | 9 table header rows missing `\\` (deluxetable→tabular migration bug) | Multiple tables | Added `\\` to all |
| 10 | `\argmin` undefined | L551 | Added `\DeclareMathOperator*{\argmin}{arg\,min}` to preamble |
| 11 | `\tablecomments` undefined in mnras.cls | — | Added `\newcommand{\tablecomments}[1]{\par\smallskip{\footnotesize #1}}` to preamble |
| 12 | `$~au` — `~` inside math mode (illegal) | L583 | Changed to `~au` (text mode) |

### V4 compilation: SUCCESS
- 21 pages, 699 KB PDF
- 0 errors, 0 undefined citations, 0 undefined references
- Full pdflatex→bibtex→pdflatex→pdflatex cycle clean

## Phase 2: Reviewer Feedback Analysis (v4fix.docx)

### Reviewer 1 — Core Issues

| # | Reviewer claim | Verified? | Notes |
|---|---------------|-----------|-------|
| 🔴1 | No same-data comparison | TRUE | V4 acknowledges at L837; reviewer considers this basic requirement for methods paper |
| 🔴2 | N=1 acknowledged but unresolved | TRUE | δ_domain provisional, spherical grain bias ~8%, If-Then guide says don't use for CO/H₂O >> 2 |
| 🟡3 | Observing strategy optimizer unvalidated | TRUE | V4 L586 already says "presented as proposed method... not validated" |
| 🟡4 | **Table 13 correction direction contradicted** | **REVIEWER WRONG** | Text says spherical grain OVERESTIMATES Q_d by ~8%; table says "Subtract 8.2%". If Mie > T-matrix by 8.2%, subtracting from Mie gives T-matrix. Direction IS correct. |

### Reviewer 1 — New Issues

| Issue | Verified? |
|-------|-----------|
| Stress Test 6 adaptive constraint only proposed, not implemented | TRUE — V4 says "not implemented... architecturally straightforward" |
| MMD gap needs N≥5, currently N=1 | TRUE — §4.6.4 already discusses this |
| Green region boundary SNR>5 may be too conservative | DEBATABLE — Green="all methods work" includes traditional Afρ which needs SNR>3-5 |

### Reviewer 2: Figure readability, table formatting, DIRTY config — minor
### Reviewer 3: Fusion method experimental comparison missing, FLOPs analysis missing, 40% desk reject risk

## Phase 3: Same-Data Comparison — Data Download

### Strategy: re-implement Afρ+Haser on same 2I/Borisov images as COMETH framework

### Target datasets:
1. **HST/WFC3 + ACS** (MAST) — proposals 16009, 16044, 16041
2. **ESO FORS2 R-band** (ESO Archive) — programs 2104.C-5035, 110.23ZJ.001  
3. **ESO MUSE IFU** (ESO Archive)

### MAST download:
- 138 observations across 3 proposals
- 63 calibrated FLC files identified
- 1 file downloaded (ie6k01u6q_flc.fits, 40 MB) — rest pending (slow network)
- Download script: `download_borisov.py` (supports resume)

### ESO download:
- Requires browser login at archive.eso.org
- Manual instructions in download script

### Files created/modified:
| File | Status |
|------|--------|
| `main_methodology_v4.tex` | 12 fixes applied, compiles clean (21pp) |
| `download_borisov.py` | MAST auto-download + ESO manual instructions |
| `borisov_data/` | Download directory created; 1 HST FLC file downloaded |

## Next Steps (for next session)

### Data (offline, user to complete):
1. Run `python download_borisov.py` to finish HST download (resume supported)
2. Manually download ESO FORS2 data from archive.eso.org
3. Report total file count and size

### Code (after data is ready):
4. Build Afρ pipeline (photutils) + Haser model fitting (sbpy)
5. Run COMETH frozen inference on same FITS files
6. Produce same-data comparison table (Afρ vs Haser vs COMETH on identical images)
7. Update V4 with results

### Paper (pending):
8. Fill 7 missing 3I/ATLAS citations (user to provide ADS export)
9. Reviewer response letter
