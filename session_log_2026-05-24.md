# Session Log — 2026-05-24

## Phase 1: V12 Review & Critical Fixes (morning)

### Issues from v12-2fix.docx (29 items, 8 unfixed)
- Angular momentum → energy-limited jet collimation (physical accuracy)
- Momentum equation dimensional error: removed algebraic form, kept ODE solver
- Hard/soft constraint architecture: clarified as two-level (soft penalties + hard transforms)
- SNR gain → PSNR-based detection-image-quality gain (throughout)
- 201/209 measurement counts unified with raw/filtered distinction
- Human CI method documented (Clopper-Pearson exact binomial)
- Q_dust formula corrected: 0.004-0.09 → 7-300 kg/s
- 3I/ATLAS §4.6.5 deleted; §1.1 clarification added
- Carbon footprint uncertainty added (±20 kg CO2)
- Keywords, β values, DOI verified as correct

### V12 → V13 → V14
- V13: All major fixes from v12-2fix applied
- V14: 3 A&C reviewer minor issues fixed + terminology sweep

## Phase 2: A&C Reviewer Perspective Audit (afternoon)

### Reviewer feedback on V14
1. Gradient continuity at min() in Eq.16: Added technical note explaining subgradient behavior, PyTorch autograd implementation, and AdaptiveConstraintManager safeguards
2. Software comparison incomplete: Added Tycho Tracker + DIRTY to comparison table
3. Minor fixes: 201/209 consistency, Human CI method

### Final V14
- 26 pages, 0 errors, 0 undefined references
- Anonymous code: https://anonymous.4open.science/r/cometh-F185
- Zenodo DOI: placeholder (embargoed until acceptance)
- Double-blind: author info withheld

## Files Created/Modified Today

| File | Action |
|------|--------|
| main_methodology_v12.tex/.pdf | Archival (26pp) |
| main_methodology_v13.tex/.pdf | Archival (25pp) |
| main_methodology_v14.tex/.pdf | Current (26pp) |
| coverletter.txt | A&C submission cover letter |
| session_log_2026-05-24.md | This file |
| references.bib | +tychotracker reference |
| v12.2_v13_comparison.pdf | Review comparison document |

## Key Decisions
- arXiv preprint: NOT submitted (no institutional mentor endorsement)
- Double-blind: Author info withheld from manuscript
- Anonymous code: 4open.science mirror of chenzhilei-lab/cometh
- N=1 honesty: All claims explicitly qualified as feasibility demonstration
- 3I/ATLAS: No COMETH inference performed; real observations cited as motivation only

## Remaining
- Journal submission: A&C Editorial Manager (user to complete)
- Model weights: Zenodo after acceptance
- DIRTY code: Must be obtained separately from Gordon et al.
