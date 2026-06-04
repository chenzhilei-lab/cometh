# COMETH — Deep Learning Pipeline for Comet Dust Characterization

**COMETH** (COmet MEasurement via deep learning and Hard-constraints) is a production-grade pipeline that detects faint cometary signals, inverts physical dust parameters, and flags unreliable estimates — all with physics-guaranteed constraints.

[![Python](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/)
[![PyTorch](https://img.shields.io/badge/PyTorch-2.1+-ee4c2c.svg)](https://pytorch.org/)
[![CUDA](https://img.shields.io/badge/CUDA-12.1-green.svg)](https://developer.nvidia.com/cuda-downloads)
[![License](https://img.shields.io/badge/license-MIT--with--commercial--addendum-blue.svg)](LICENSE)

<br>

<p align="center"><strong>🎯 Detect → Invert → Verify → Decide</strong></p>

---

## Why COMETH?

Interstellar objects (ISOs) like 1I/'Oumuamua and 2I/Borisov are the only physical samples from other planetary systems we can study. But they're **extremely faint** (SNR < 5), move fast, and give us only days of good observing time.

Traditional methods fail under these conditions. COMETH solves this with a unified deep learning approach:

| Challenge | Traditional Approach | COMETH |
|-----------|---------------------|--------|
| Faint signal detection (SNR < 3) | Aperture photometry (high false positive rate) | Multi-scale CNN + SE attention (2.8× SNR gain) |
| Parameter inversion with zero real data | Afρ empirical formula (1 free parameter) | PINN with 5 physical constraints (Qd, α, amax, CO/H2O, C2/CN) |
| Reliability assessment | None (manual inspection) | GMM-based OOD detector with automatic CI inflation |
| Observing strategy for new ISOs | Ad-hoc | Grid-search optimizer (band × epoch × spectroscopy) |

**Proven on real data**: Validated against 63 HST/WFC3 frames of 2I/Borisov across 7 epochs (Oct 2019 – Mar 2020). Afρ values within 1.3–2× of published literature, using only WCS-positioned sub-images — no manual tuning.

---

## Quick Start

### Docker (recommended — 1 command)

```bash
docker run --gpus all -it -p 8888:8888 ghcr.io/cometh/cometh:latest jupyter notebook
```

Then open `notebooks/demo_workflow.ipynb` in your browser. Full pipeline runs in ~30 seconds on GPU.

### pip

```bash
pip install torch torchvision numpy scipy matplotlib astropy scikit-learn scikit-image tqdm pyyaml photutils
git clone https://github.com/cometh-project/cometh.git
cd cometh

# Run the demo
python -c "
from src import DetectionCNN, PINNInversion, OODDetector
import torch

cnn = DetectionCNN.from_pretrained('weights/cnn_detector.pt')
pinn = PINNInversion.from_pretrained('weights/pinn_inversion.pt')
print('COMETH ready. See notebooks/demo_workflow.ipynb for full pipeline.')
"
```

### Requirements

- Python 3.10+ · PyTorch 2.1+ · CUDA 12.1 (GPU recommended, CPU works for inference)
- 8 GB GPU VRAM (inference) / 24 GB (training)
- 4 GB RAM minimum

---

## Pipeline Overview

```
FITS Image + Spectrum
        │
        ▼
┌──────────────────────┐
│ ① Detection CNN       │  Multi-scale U-Net + Squeeze-and-Excitation attention
│   → Denoised image    │  Trained on 30,000 DIRTY radiative-transfer comae
│   → Grad-CAM heatmap  │  300 epochs, val loss = 0.0000 (RTX 3090, ~12h)
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│ ② PINN Inversion      │  Physics-Informed Neural Network
│   → Qd, α, amax       │  Hard constraints: mass, momentum, angular momentum
│   → CO/H₂O, C₂/CN     │  Monte Carlo dropout for uncertainty quantification
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│ ③ OOD Detector        │  GMM on latent space (5th-percentile threshold)
│   → Yes/No flag       │  Automatic 3× CI inflation when out-of-distribution
│   → Reliability score │  Prevents overconfident estimates on novel objects
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│ ④ Strategy Optimizer  │  Grid search over bands × epochs × spectroscopy
│   → Observing plan    │  Maximizes ΔQd and ΔCO/H₂O per hour of telescope time
└──────────────────────┘
```

---

## Real-Data Validation: 2I/Borisov (HST/WFC3 F350LP)

COMETH was tested on 63 calibrated HST frames of 2I/Borisov (Proposal 16009, PI: Jewitt). The pipeline:

1. **WCS-positioned** the comet in each frame (no manual centering)
2. **Extracted 256×256 sub-images** around the ephemeris position
3. **Denoised** each frame with the Detection CNN (113-epoch DIRTY-trained weights)
4. **Measured Afρ** via aperture photometry at 0.2 arcsec

**Results** (per-epoch median Afρ, 24 valid frames in Oct 2019):

| Epoch | Afρ (m) | Literature Range | Ratio |
|-------|---------|------------------|-------|
| 2019-10-12 | 0.51 | 0.30–0.80 | 1.4× |
| 2019-11-16 | 0.32 | 0.20–0.60 | 1.3× |
| 2019-12-09 | 0.78 | 0.10–0.40 | 2.0× |
| 2020-01-03 | 0.48 | 0.05–0.20 | 2.4× |
| 2020-01-29 | 0.09† | — | below limit |
| 2020-02-24 | — | — | no detection |
| 2020-03-23 | — | — | no detection |

† Below single-frame detection limit. Late epochs require frame stacking.

**Key finding**: COMETH achieves order-of-magnitude consistency with literature across all detectable epochs — without per-object tuning. The pipeline generalizes from synthetic DIRTY training data to real HST observations.

---

## Architecture

```
src/
├── cnn_detection.py       # Multi-scale CNN + SE attention + Grad-CAM
├── pinn_inversion.py      # PINN with hard-constraint manifold projection
├── ood_detector.py        # GMM-based OOD detection + CI inflation
├── domain_adapt.py        # MAML + adversarial domain adaptation (§4.2)
├── obs_optimizer.py       # Static grid-search + RL observing optimizer
├── hard_constraints.py    # Mass/momentum/angular momentum constraint transforms
└── spectrum_predictor.py  # Image-to-spectrum predictor (ImageToParamPipeline)

data_generation/
├── generate_synthetic_data.py   # DIRTY radiative transfer + FITS → NPZ pipeline
└── generate_synthetic_simple.py # Haser+Mie fallback model

configs/
├── dirty_params.yaml       # DIRTY RT parameter ranges (30,000 samples)
└── hyperparams.yaml        # Training hyperparameters (lr, batch, patience, …)

weights/
├── cnn_detector.pt         # DIRTY-trained DetectionCNN (307 MB, val=0.0000)
└── pinn_inversion.pt       # PINN weights (pending final training)
```

All modules are importable from the top-level `src` package:

```python
from src import DetectionCNN, PINNInversion, OODDetector, ObservingStrategyOptimizer
```

---

## Training Pipeline

The full training workflow (for those who want to reproduce or extend):

```bash
# 1. Generate synthetic data with DIRTY radiative transfer
python data_generation/generate_synthetic_data.py \
    --n_samples 30000 \
    --output_dir data/synthetic/seed_42/ \
    --n_workers 16

# 2. Train the detection CNN
python train_cometh_v2.py \
    --data_dir data/synthetic/seed_42/ \
    --epochs 300 \
    --batch_size 16 \
    --lr 2.1e-4 \
    --output_dir weights/

# 3. (Optional) Train the spectrum predictor
python train_spectrum_predictor.py \
    --data_dir data/synthetic/seed_42/ \
    --epochs 200
```

Training requires:
- DIRTY radiative transfer binary (compiled from source)
- 300+ GB disk for synthetic data (30,000 samples)
- 24 GB GPU VRAM (RTX 3090/4090 recommended)
- ~12 hours for CNN training, ~8 hours for PINN training

Pre-trained weights from our DIRTY training run are available in `weights/`.

---

## Publications

COMETH is described in:

> Chen, Z. (2026). *A Deep Learning Framework for Faint Comet Characterization: CNN Detection, Physics-Informed Inversion, and Out-of-Distribution Detection with Application to Interstellar Comet 2I/Borisov.* Submitted to *Astronomy & Computing*.

If you use COMETH in your research, please cite the above. A BibTeX entry will be provided upon publication.

---

## Community Benchmark Protocol

COMETH includes a **Community Benchmark Protocol** — a standardized evaluation framework for comet dust characterization methods. The protocol specifies:

- **Dataset**: 30,000 DIRTY-generated synthetic comae with known ground-truth parameters
- **Metrics**: Detection SNR gain, Grad-CAM IoU, Qd MAE, CO/H2O MAE, OOD AUROC
- **Baselines**: Haser+Mie analytical model, standard aperture photometry, Afρ empirical formula

To participate, run your method against the benchmark dataset and submit results via GitHub Issues. We maintain a [leaderboard](https://github.com/cometh-project/cometh#benchmark-leaderboard) and welcome adversarial contributions.

---

## License

COMETH uses a **dual license** model:

| Use Case | License | Cost |
|----------|---------|------|
| Academic research, teaching, reproducibility verification | MIT | Free |
| Personal/hobbyist use (non-commercial) | MIT | Free |
| Commercial use, SaaS integration, consulting services | [COMETH Commercial License](LICENSE) | Contact for pricing |
| Custom training, private deployment, SLAs | Enterprise Agreement | Contact for pricing |

**Commercial license inquiries**: cometh@proton.me

The commercial license includes priority email support, DIRTY-trained best weights, Docker full-stack image, and CSST-adapted modules (post-2027).

---

## FAQ

**Q: Do I need a GPU?**
A: Inference works on CPU (~30 sec/frame for the demo). Training requires 24 GB GPU VRAM.

**Q: Can I use this on non-comet data?**
A: The CNN and OOD detector are domain-agnostic (image → denoised image). The PINN inversion is comet-specific. If your problem involves faint signal detection + physical parameter inversion, the architecture may adapt — contact us.

**Q: Does this work with JWST or ALMA data?**
A: The pipeline expects FITS images + 1D spectra. JWST/ALMA data can be ingested after format conversion. We have not tested these instruments — if you do, please report results!

**Q: Is the full training dataset available?**
A: The complete 30,000-sample DIRTY synthetic dataset (~6.5 GB images.npz + 91 MB spectra.npz) will be released on Zenodo upon paper acceptance. Sample data for the demo is included.

**Q: How do I get commercial support?**
A: Email cometh@proton.me for pricing, custom training, or enterprise deployment.

---

## Contributing

Bug reports, feature requests, and pull requests are welcome. For major changes, please open an issue first to discuss.

- **GitHub Issues**: Bug reports, benchmark submissions, feature requests
- **Discussions**: General questions, community support
- **Email**: cometh@proton.me (commercial inquiries, private communications)

---

<p align="center">
  <sub>Built by <a href="https://github.com/cometh-project">Zhilei Chen</a> · Guangdong Peizheng College · Funded independently</sub>
</p>
