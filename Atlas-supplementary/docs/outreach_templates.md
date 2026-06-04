# COMETH Outreach Email Templates

Templates for first-contact emails. Replace `[BRACKETS]` with specifics.
Wait until paper is accepted before sending.

---

## Template A: CSST Science Working Group

**To:** CSST Science Center / Solar System Working Group lead
**Subject:** COMETH — Automated Comet Dust Pipeline for CSST Survey Data

```
Dear [NAME],

I am writing to introduce COMETH, a deep learning pipeline for automated
cometary dust characterization that may be relevant to CSST's solar system
science program.

COMETH provides a unified workflow:
  - CNN-based faint comet detection (2.8× SNR gain, validated on HST)
  - Physics-informed neural network (PINN) inversion of 5 dust parameters
  - Automatic out-of-distribution detection with uncertainty quantification
  - Benchmark protocol for cross-method comparison

The pipeline is designed for survey-scale data: a single RTX 3090 processes
~1,000 frames per hour end-to-end. It has been validated on 63 HST/WFC3
frames of interstellar comet 2I/Borisov across 7 epochs (Afρ within 1.3-2×
of published literature).

The manuscript is currently under review at Astronomy & Computing. The
codebase is available under a dual MIT/commercial license.

CSST's 2027 launch represents a unique opportunity to establish automated
solar system object characterization as a first-class citizen in the survey
data pipeline. I would welcome a brief discussion about whether COMETH
could contribute to CSST's science preparation efforts.

A 1-page capability statement is attached.

Best regards,
Zhilei Chen
Guangdong Peizheng College
cometh@proton.me
[ATTACH: COMETH_Capability_Statement.pdf]
```

---

## Template B: David Jewitt (UCLA) — 2I/Borisov Discoverer

**To:** David Jewitt <jewitt@ucla.edu>
**Subject:** COMETH — Deep learning analysis of your HST 2I/Borisov data (Proposal 16009)

```
Dear Prof. Jewitt,

I am writing to share results from COMETH, a deep learning pipeline I
developed for cometary dust characterization, which I applied to the HST/WFC3
F350LP observations of 2I/Borisov from your Proposal 16009.

Using WCS-positioned sub-images (no manual centering), COMETH's detection CNN
processed 63 frames across 7 epochs (Oct 2019 – Mar 2020). Key findings:

  - Afρ at 2019-10-12: 0.51 m (vs. literature 0.30-0.80 m, factor 1.4×)
  - Afρ at 2019-11-16: 0.32 m (vs. literature 0.20-0.60 m, factor 1.3×)
  - Late epochs (Jan-Mar 2020): below single-frame detection limit

The notable result is that the CNN generalizes from purely synthetic DIRTY
radiative transfer training data to real HST observations — without per-object
retraining. The manuscript is under review at Astronomy & Computing.

I would be grateful for any feedback on the methodology or results, and
welcome discussion about potential applications to future ISO discoveries.

A 1-page capability statement is attached.

Best regards,
Zhilei Chen
Guangdong Peizheng College
cometh@proton.me
[ATTACH: COMETH_Capability_Statement.pdf]
```

---

## Template C: Academic Collaborator (e.g., Guangzhou University)

**To:** [NAME]
**Subject:** Potential collaboration — COMETH deep learning pipeline for cometary science

```
Dear Prof. [NAME],

I am an independent researcher at Guangdong Peizheng College working on
deep learning methods for cometary dust characterization. My framework,
COMETH, combines CNN detection with physics-informed neural network inversion
and out-of-distribution detection — validated on HST observations of 2I/Borisov.

I am reaching out because [SPECIFIC REASON — e.g., your group's work on CSST
solar system science / cometary dust modeling / ISO research aligns with
COMETH's capabilities].

The manuscript is currently under review at Astronomy & Computing. I am
exploring potential collaborations for:

  1. Joint NSFC application (2027 cycle) — COMETH as CSST preparatory work
  2. Extending the validation to additional comets / observational datasets
  3. Benchmark Protocol community adoption

Would you be open to a brief discussion about possible synergies?

A 1-page capability statement is attached.

Best regards,
Zhilei Chen
Guangdong Peizheng College
cometh@proton.me
[ATTACH: COMETH_Capability_Statement.pdf]
```

---

## Template D: Commercial / Industrial Client

**To:** [NAME]
**Subject:** Automated defect/anomaly detection — physics-constrained deep learning

```
Dear [NAME],

I am reaching out about a technology with potential applications to [INDUSTRY —
e.g., semiconductor inspection / satellite debris detection / aerosol remote sensing].

My framework, COMETH, addresses a fundamental challenge in deep learning:
how to make reliable predictions when training data is scarce and targets are
faint. It combines:

  1. Multi-scale CNN detection (2.8× SNR gain at SNR < 3)
  2. Physics-informed neural network (PINN) with hard constraints
  3. Automatic out-of-distribution detection with confidence interval inflation

Originally developed for astronomical comet detection (validated on NASA/ESA
HST data, under peer review at Astronomy & Computing), the core architecture
is domain-agnostic and applicable to any problem involving:

  - Faint signal detection in high-noise environments
  - Physical parameter inversion with guaranteed constraint satisfaction
  - Reliable uncertainty quantification for safety-critical applications

I would welcome a brief discussion about whether this approach could address
challenges in your domain.

A 1-page technical capability statement is attached.

Best regards,
Zhilei Chen
cometh@proton.me
[ATTACH: COMETH_Capability_Statement.pdf]
```

---

## Sending Checklist

- [ ] Paper accepted (or at least arXiv preprint available)
- [ ] GitHub repo is public
- [ ] Recipient's recent work acknowledged (personalize each email)
- [ ] Capability statement attached as PDF
- [ ] BCC yourself for tracking
- [ ] Follow-up calendar reminder set (2 weeks if no reply)
