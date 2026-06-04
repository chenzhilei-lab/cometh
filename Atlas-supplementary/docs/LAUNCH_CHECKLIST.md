# GitHub Public Launch Checklist

When the paper is accepted by Astronomy & Computing, execute in order.

## Day -3: Pre-flight

- [ ] Remove any hardcoded personal paths from code
  - [ ] `grep -r "D:\\\\Users\\\\37639" --include="*.py"` → fix
  - [ ] `grep -r "C:\\\\Users\\\\37639" --include="*.py"` → fix
- [ ] Verify LICENSE file is final (no placeholder text)
- [ ] Verify README badges point to correct URLs (repo name, etc.)
- [ ] Set repo to **public** in GitHub Settings
- [ ] Enable GitHub Issues (with templates)
- [ ] Enable GitHub Discussions (Q&A category)
- [ ] Add repo description: "Deep learning pipeline for comet dust characterization — CNN detection, PINN inversion, OOD detection"
- [ ] Add repo topics: `astronomy` `deep-learning` `pytorch` `comet` `physics-informed` `interstellar-objects`

## Day -1: Weights & Data

- [ ] Upload `cnn_detector.pt` (307MB) to Zenodo
  - [ ] Create new Zenodo record
  - [ ] Set title: "COMETH Detection CNN Weights — DIRTY 30k-sample, 113-epoch, RTX 3090"
  - [ ] Set authors: Zhilei Chen
  - [ ] Link to GitHub repo
  - [ ] Reserve DOI (don't publish yet)
- [ ] Upload training dataset to Zenodo (30,000 samples, ~6.6GB)
  - [ ] `images.npz` (6.5GB)
  - [ ] `spectra.npz` (91MB)
  - [ ] `parameters.yaml` (4KB)
  - [ ] Set title: "COMETH Synthetic Training Dataset — 30,000 DIRTY Radiative Transfer Comae"
  - [ ] Reserve DOI
- [ ] Create GitHub Release v0.1.0
  - [ ] Tag: `v0.1.0`
  - [ ] Title: "COMETH v0.1.0 — Initial Public Release"
  - [ ] Body: link to paper (arXiv DOI), link to Zenodo weights, quick start
  - [ ] Attach: nothing (weights are on Zenodo due to size)

## Day 0: Launch (same day paper appears online)

- [ ] Publish Zenodo records (both DOI)
- [ ] Update README.md:
  - [ ] Replace "submitted to A&C" → actual citation with DOI
  - [ ] Add arXiv badge: `[![arXiv](https://img.shields.io/badge/arXiv-XXXX.XXXXX-b31b1b.svg)](URL)`
  - [ ] Add Zenodo DOI badge for weights
  - [ ] Add Zenodo DOI badge for dataset
- [ ] Commit + push
- [ ] Publish GitHub Release
- [ ] Register `cometh` on PyPI: `pip install twine && twine upload dist/*`
- [ ] Post on social:
  - [ ] Twitter/X: "🚀 COMETH v0.1.0 is public — deep learning pipeline for comet dust characterization, validated on HST 2I/Borisov. Paper in A&C. github.com/cometh-project/cometh"
  - [ ] Bluesky: same
  - [ ] LinkedIn: same + capability statement link
  - [ ] ResearchGate: link to paper + code
  - [ ] r/astronomy, r/MachineLearning (Reddit)

## Day +1 to +7: Outreach

- [ ] Send Template A (CSST) — personalized
- [ ] Send Template B (Jewitt) — personalized
- [ ] Send Template C (academic collaborators) — as appropriate
- [ ] Reply to any GitHub Issues within 24 hours

## Day +30: Review

- [ ] GitHub stars / clones stats
- [ ] Zenodo download counts
- [ ] Paper citation count (Google Scholar)
- [ ] Adjust strategy based on traction
