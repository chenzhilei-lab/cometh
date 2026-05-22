# Session Log — 2026-05-21

## Phase 1: Appeal Letter Fact-Check
- Checked `appeal letter.docx` (English) vs `apeal.txt` (Chinese draft)
- Found: Oumuamua already corrected to 3I/ATLAS in English version
- Found: "fewer than 5 papers on 3I/ATLAS" → actually ~20 (Lintott's "50+" also wrong)
- Found: SNR 1–5 claim unsupported by cited Jewitt 2020 / Bodewits 2020 papers
- Found: Jewitt 2020 cited for 3I/ATLAS but published 5 years before its discovery
- Created and sent `correction_letter.docx` covering both errors

## Phase 2: Paper 2 Reference Verification (10 papers checked)

### Downloaded & verified by user:
| # | File | Bib Key | Key Findings |
|---|------|---------|-------------|
| 1 | `Unusual polarimetric properties...docx` | bagnulo21 | PSG values 0.34--0.74 (%/100nm), not 0.35±0.05; phase-angle dependent |
| 2 | `Dust Production...docx` | clements21 | Q_d=11.2--16.4 kg/s (Afρ scaling, a=100μm, v=7m/s) |
| 3 | `Dust Environment Model...docx` | cremonese20 | Q_d=30--35 kg/s (probabilistic tail model, v=3m/s, α=4.5) |
| 4 | `Initial characterization...2I.docx` (Guzik) | guzik19 | Nucleus ~1km, S'=12.5%/100nm, Afρ~100cm |
| 5 | `2I-Borisov A C2-depleted...docx` (Opitom) | opitom19 | log(C2/CN) < −0.54 (UPPER LIMIT, not measurement) |
| 6 | `Detection of CN Gas...docx` | fitzsimmons19 | Q(CN)=3.9×10²⁴ at 2.66au, C2≤4×10²⁴ (not yet establishing depletion) |
| 7 | `Initial Characterization...2I-2.docx` (Jewitt) | jewitt19 | Activity onset ~4.5au, Q_d~2 kg/s (NOT 4.1) |
| 8 | `a1.tex` | bodewits20 | CO/H₂O=130--155% (=1.3--1.55), NOT >1.73. CO=6.4--10.7×10²⁶ molec/s |
| 9 | `a2.tex` / `2105.09305v1.pdf` | guzik21 | Ni=0.9×10²² atoms/s, 0.002% OH, parent lifetime 340s |
| 10 | `The similarity...2I.pdf` | opitom21 | C2 DETECTED (Swan bands)! UVES high-res broke the opitom19 upper limit |

## Phase 3: Paper 2 Edits Applied
1. **3I/ATLAS literature** (Lines 32-33): "no peer-reviewed characterization" → acknowledge ~20 studies
2. **3I/ATLAS data section** (Lines 60-62): Updated from "only discovery astrometry" to acknowledge published constraints
3. **Dust production validation** (Lines 115-116): Completely rewritten with accurate values from each paper, methodological context
4. **C₂/CN notation** (Line 133): Changed from "≈ −0.6" to upper limit "< −0.54", added Fitzsimmons CN value
5. **Table 7** (Lines 233-240): Fixed Q_d (11-16/30-35), PSG (0.34-0.74†), C2/CN (< −0.54), updated references
6. **Discussion section** (Line 215): Updated 3I/ATLAS description
7. **Introduction summary** (Line 38): Updated 3I/ATLAS framing

### Bib fixes:
- `jewitt19`: Fixed DOI (ab5861→ab530b) and title (C2-depleted→Initial Characterization)
- Added `jewitt25` (Jewitt & Luu 2025, 3I/ATLAS HST, ApJL 994)
- Added `opitom19` (Opitom et al. 2019, A&A 631, L8 — the actual C2-depletion paper)

## Phase 4: Session Persistence Setup
- Added Stop hook to `.claude/settings.local.json` — auto-logs session timestamps
- Created memory files at `~/.claude/projects/...memory/`
- Activated project memory system

## Remaining Issues (Not Yet Fixed)
1. **CO/H₂O >1.73** attributed to bodewits20 — actual value is 130-155% (=1.3-1.55)
2. **C₂ depletion narrative** — opitom21 (UVES) detected C₂; upper-limit story needs updating

## Files Modified
- `main_application.tex` — 7 edits (sections 1-5 fixed)
- `references.bib` — 3 entries added/fixed

## Context for Next Session
- Paper 1 (methodology) under appeal at ApJ; correction letter sent
- Paper 2 (application): CO/H₂O and C₂ fixes applied (5 locations)
- 10 of ~14 key references verified
- All remaining fact-check fixes applied to main_application.tex

## Phase 5: Lintott Appeal Response Analysis (May 21, part 2)
- Received Chris Lintott's rejection of appeal (5-point rebuttal)
- Fact-checked each of his 5 points against paper text and ADS:
  - Point 5 (86 papers): Lintott used full-text search inflating count; actual characterization papers ~35-50. Paper underestimated but Lintott's method is apples-to-oranges.
  - Point 1 ("intrinsically fainter"): Partially valid — abstract used "intrinsic" inappropriately for N=2
  - Point 2 (no traditional comparison): His Zhang17 claim wrong; broader point about no real-data comparison correct
  - Point 3 (spectroscopy trivial): Lintott correct
  - Point 4 (writing style): Subjective but has merit
  - LLM accusation: Serious, unsubstantiated allegation
- Decision: NOT to appeal further. Improve paper per feedback, resubmit to MNRAS.

## Phase 6: Paper 1 (methodology) Revision for MNRAS (May 21, part 3)
- Applied 12 content edits addressing all 5 Lintott critiques (Phase 1 complete):
  1. Abstract: "intrinsic faintness" → observational circumstances + N=2 caveat
  2. §1.1: "Extreme faintness" → "Observational faintness" + N=2 qualifiers
  3. 3I/ATLAS footnote: Updated to ~35-50 characterization papers
  4. §1.2: "systematically fall outside" → qualified with N=2
  5. §1.4: Added literature comparison as explicit contribution + same-data caveat
  6. §3.7: Downgraded spectroscopy claim ("not a novel finding")
  7. Failure Mode 4: "Key finding" → "Interpretation" / "confirmation"
  8. **MAJOR**: New §4.6.2.1 with explicit Framework-vs-Traditional comparison table (Table `tab:traditional_comparison`), discussion of what is/isn't demonstrated, explanation of why literature comparison
  9. Language: Added plain-language sentences to Abstract and §1.1
  10. §4.1.1: Explicit 3-category taxonomy (traditional cometary / general image processing / DL baselines)
  11. Conclusions: Added literature comparison bullet + synthetic-only caveat on detection floor
  12. Conclusions: Expanded N=1 caveat to mention same-data validation need
- Also fixed: remaining >1.73 → 1.30-1.55 in methodology paper (L785)
- Phase 2 (MNRAS format conversion) deferred — user wants content finalized first
- Braces verified balanced (1419/1419) — structurally sound

## Phase 7: MNRAS Format Conversion (May 21, part 4)
- Switched document class: `aastex631` → `mnras.cls` (with `usenatbib`)
- Restored author block placeholder (MNRAS single-blind) — user must fill in full details
- Removed AAS-specific: `\received`, `\revised`, `\accepted`, `\published`, `\lineno`, `\hyperref`, `\shorttitle`, `\shortauthors`
- Added MNRAS-recommended: `newtxtext`, `newtxmath`, `T1{fontenc}`, `booktabs`
- Converted 12 `deluxetable*` → standard `table*` + `tabular`:
  - All `\colhead{...}` wrappers removed
  - All headers restored from original (multi-column labels with `&`)
  - All caption braces fixed
  - `\toprule`/`\midrule`/`\bottomrule` added via `booktabs`
- Keywords: `\keywords{}` → `\begin{keywords}...\end{keywords}`
- Acknowledgments: `\begin{acknowledgments}` → `\section*{Acknowledgements}` (mnras.cls doesn't define acknowledgements environment)
- Bibliography: Added `\bibliographystyle{mnras}`
- "AAS manuscript submission system" → "journal's online submission system" (all occurrences)
- Fixed `\end{document` → `\end{document}`
- Fixed `\textsc{Cometh}` caption truncation in Table KPI
- Fixed missing `}` after `\rm{sys` → `\rm{sys}`
- Compiles successfully (22 pages, 806KB PDF) on this machine after commenting out newtx (font not available locally; re-enabled for user)
- **TO DO for user**: Install newtx fonts (`tlmgr install newtx`) or the MiKTeX equivalent; fill in author block with full names, affiliations, email

## Phase 8: 改稿思路 Review + V3 Creation (May 21, part 5)
- Reviewed all documents in `改稿思路/` directory:
  - `修改思路.docx`: Narrative pivot + necessity argument + traditional method redefinition + real data comparison + synthetic visualization
  - `总体印象.docx`: Honest assessment — tech depth 9/10 but science story 4/10. Core critique: "博士论文级技术汇编，不是期刊论文"
  - `一个更聪明的办法.docx`: "小样本不是不需要ML的理由，而是更需要ML的理由"
  - `重新定义分类.docx` / `redefineclass.tex` / `rebuildclass.tex`: Table 5 restructure with Category column

### Phase 8a: Applied changes from 修改思路.docx
- Added §1.5 "Why a Deep Learning Framework for a Small Population?" with 7-row necessity table
- Restructured Table 5: Added Category column (Traditional image processing / Traditional cometary / Generic DL baseline / Proposed framework)
- Added Afρ and Haser rows to Table 5
- Added §2.2 "Synthetic Data Fidelity" — addresses Lintott's "not shown synthetic images"
- Fixed Hale-Bopp "most CO-rich" claim → "notably CO-rich" (C/2016 R2 is more extreme)
- Added bagnulo21 bib fix, added biver18 reference
- Updated newtx font maps (initexmf --update-fndb + updmap) → fonts now compile
- Full compile cycle: 0 errors, 0 undefined references

### Phase 8b: V3 created (main_methodology_v3.tex, 20 pages)
Per 总体印象.docx critique ("技术汇编→科学故事"):
1. **Abstract rewritten**: From architecture inventory → physical results (human 31% vs machine 78%, 2I/Borisov 12% MAD, detection floor SNR~0.75, spherical grain bias ~8%)
2. **3I/ATLAS literature**: Expanded from footnote → proper paragraph (~15 key findings: water ice, H₂O production, CO₂ enrichment, IRAM molecules, ALMA CH₃OH/HCN, antitail, Ni/Fe evolution, HST nucleus)
3. **Cut RL extension** (§3.7.4): Entire unimplemented subsection removed
4. **Compressed layered PINN + GAN**: ~60 lines → 2 sentences ("deferred to future work")
5. **Compressed Limitations**: 8 items → 4 (removed Neural ODE, BNN, GAN, multi-target generalization)
6. **Removed Migration Guide**: Entire section deleted (unvalidated recipe)
7. Page count: 21→20

### Key files state
| File | Status |
|------|--------|
| `main_methodology_v2.tex` | Phase 1+2 complete, MNRAS format, compiles 21pp |
| `main_methodology_v3.tex` | V3 with cuts + lit review + new abstract, compiles 20pp |
| `main_application.tex` | CO/H₂O + C₂ fixes complete |
| `references.bib` | bagnulo21 fixed, biver18 added |
| `coverletter_mnras.txt` | Clean MNRAS cover letter (no ApJ/Lintott mention) |

## Remaining for Next Session
- User must fill in author block (name, affiliation, email) — applies to both v2 and v3
- Decide: submit v2 or v3?
- If v3: check for orphaned references from deleted sections (RL eq, Migration Guide items)
- MNRAS submission
- Draft MNRAS cover letter
- One factual check: Hale-Bopp as "most CO-rich solar system comet" — C/2016 R2 may have higher CO/H2O
- Any remaining polish per user preference
- One factual check: Hale-Bopp as "most CO-rich solar system comet" — C/2016 R2 may have higher CO/H2O
- Update "AAS manuscript submission system" references → MNRAS/Zenodo
- Draft MNRAS cover letter
- Papers still needed: jewitt20 (optional, HST outburst)
- Downloaded papers in: `D:\Users\37639\Desktop\3I-Atlas\Final-Atlas\Download\`
