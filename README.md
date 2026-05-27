# COMETH — Supplementary Code Package

This repository contains the reference implementation of **COMETH** (COmet MEasurement via deep learning and Hard-constraints), as described in:

> *A Benchmarking Study of Deep Learning Methods for Faint Comet Characterization: Where Traditional Methods Fail and Physics-Informed Neural Networks Excel* (submitted to ApJ, 2026).

## Quick Start (3 minutes)

```bash
# 1. Create environment
conda env create -f environment.yml
conda activate cometh

# 2. Install dependencies
pip install -r requirements.txt

# 3. Run the demo
jupyter notebook notebooks/demo_workflow.ipynb
```

The demo notebook processes a sample synthetic comet image through the full pipeline (detection → inversion → OOD check) in ~30 seconds on CPU, producing figures analogous to those in the paper.

## Contents

```
├── src/
│   ├── cnn_detection.py     # Multi-scale CNN + SE attention + Grad-CAM
│   ├── pinn_inversion.py    # PINN with hard constraints (mass, momentum, angular momentum)
│   ├── ood_detector.py      # GMM-based OOD detector with CI inflation
│   ├── domain_adapt.py      # MAML + adversarial domain adaptation
│   ├── obs_optimizer.py     # Static + RL observing strategy optimizer
│   └── hard_constraints.py  # Mass/momentum/angular momentum constraint transforms
├── notebooks/
│   └── demo_workflow.ipynb  # End-to-end demonstration notebook
├── configs/
│   ├── dirty_params.yaml    # DIRTY radiative transfer parameters
│   └── hyperparams.yaml     # Training hyperparameters (Table 1 in paper)
├── weights/
│   ├── cnn_detector.pt      # Pre-trained detection CNN weights
│   └── pinn_inversion.pt    # Pre-trained PINN weights
├── data/
│   └── sample_input/        # 5 sample synthetic images + injection masks
├── requirements.txt
├── environment.yml
└── README.md
```

## Requirements

- Python 3.10+
- PyTorch 2.1+ with CUDA 12.1 (CPU inference works for demo)
- 4 GB RAM minimum (demo mode)

## Pre-trained Models

Weights for the detection CNN and PINN inversion network are in `weights/`. These were trained on synthetic DIRTY data and frozen before any real-object evaluation. Load them via:

```python
import torch
from src.cnn_detection import DetectionCNN
from src.pinn_inversion import PINNInversion

cnn = DetectionCNN.from_pretrained('weights/cnn_detector.pt')
pinn = PINNInversion.from_pretrained('weights/pinn_inversion.pt')
```

## Reproducing Paper Results

The full synthetic training set (~50,000 DIRTY comae, ~100 GB) and training scripts are not included in this supplementary package due to size constraints. They will be released on Zenodo upon acceptance. For peer review, the demo notebook and pre-trained weights enable verification of:

1. **Detection inference** (§4.1): Run `cnn_detection.py` on sample images → verify SNR gain and Grad-CAM heatmaps.
2. **PINN inversion** (§4.4): Run `pinn_inversion.py` on sample spectra → verify Qd and CO/H2O estimates.
3. **OOD detection** (§3.6): Trigger OOD flag on out-of-distribution sample → verify CI inflation.
4. **Attention consistency** (§3.2): Compare Grad-CAM IoU with injection mask.

## Citation

If you use this code, please cite the paper (reference to be updated upon publication).

## License

MIT License. See LICENSE file (to be added upon public release).
