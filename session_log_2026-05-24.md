# Session Log — 2026-05-24 (Planned)

## Phase 1: GitHub Repository Setup

### Task: Create public code repository for COMETH

**Current state:**
- Paper (V8) contains placeholder URLs:
  - `https://github.com/cometh-framework/cometh` (does not exist)
  - `https://anonymous.4open.science/r/cometh-review` (does not exist)

**Steps:**

1. **Create GitHub repository**
   - Go to https://github.com and sign in (or create account)
   - Create new repository: `cometh-framework/cometh` (or any name)
   - Set to Public (for A&C review) or Private (with anonymous review link)

2. **Upload files to repository:**
   ```
   Atlas-supplementary/
   ├── src/                    (CNN, PINN, OOD, MAML, constraints, optimizer)
   ├── configs/                (hyperparams.yaml, dirty_params.yaml)
   ├── data_generation/        (generate_synthetic_data.py)
   ├── weights/                (README.md only; weights via Zenodo)
   ├── notebooks/              (demo_workflow.ipynb)
   ├── Dockerfile
   ├── environment.yml
   ├── requirements.txt
   └── README.md
   ```

3. **Create anonymous reviewer access (if using private repo):**
   - Go to https://anonymous.4open.science
   - Create a reviewable link that grants read access without revealing owner identity
   - This is standard for double-blind review

4. **Replace placeholder URLs in V8 paper:**
   - Find: `https://github.com/cometh-framework/cometh`
   - Replace with actual GitHub URL
   - Find: `https://anonymous.4open.science/r/cometh-review`
   - Replace with actual 4open.science URL

5. **Zenodo DOI (if time permits):**
   - Upload code + weights snapshot to https://zenodo.org
   - Obtain embargoed DOI (accessible to reviewers, public after acceptance)
   - Replace `10.5281/zenodo.XXXXXXX` with actual DOI

### After GitHub is ready:
- Update V8 paper with real URLs
- Re-compile → V9
- Submit to A&C with Cover Letter mentioning code availability

---

## Phase 2: arXiv Preprint Submission

### arXiv-ready files prepared in `arxiv_submission/`:
```
arxiv_submission/
├── main_arxiv.tex          (arXiv-ready, bbl inline, 25 pages)
├── fig4_training.png       (training curves)
├── fig8_borisov.png        (2I/Borisov same-data comparison)
└── README.md               (submission notes)
```

### arXiv submission steps:
1. Go to https://arxiv.org/user/register
   - Register with institutional email (.edu or .ac.cn)
   - Institutional affiliation required for first submission
2. Go to https://arxiv.org/submit
3. Click "Start New Submission"
4. Choose category: **astro-ph.IM** (Instrumentation and Methods)
5. Upload `main_arxiv.tex` as main file
6. arXiv will auto-detect `fig4_training.png` and `fig8_borisov.png`
7. Fill in:
   - Title: "COMETH: A Physics-Constrained Multimodal Fusion Framework for Faint Comet Characterization"
   - Authors: Zhilei Chen
   - Abstract: (copy from paper)
   - Comments: "25 pages, 2 figures. Code available at [GitHub URL]. Submitted to Astronomy & Computing."
8. Submit → announcement within 24-48 hours → permanent arXiv ID (e.g., arXiv:2605.XXXXX)

### After arXiv is live:
- Add arXiv ID to the paper
- Add arXiv ID to the GitHub README
- Mention arXiv preprint in the A&C cover letter
