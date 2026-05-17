"""
COMETH — COmet MEasurement via deep learning and Hard-constraints.

Reference implementation of the framework described in:
  "A Benchmarking Study of Deep Learning Methods for Faint Comet
   Characterization: Where Traditional Methods Fail and Physics-Informed
   Neural Networks Excel" (submitted to ApJ, 2026).
"""

from .cnn_detection import DetectionCNN, DetectionLoss
from .pinn_inversion import PINNInversion, PINNLoss
from .ood_detector import OODDetector, compute_ood_metrics
from .domain_adapt import MAMLAdapter, compute_mmd
from .obs_optimizer import ObservingStrategyOptimizer
from .hard_constraints import (MassConservation, MomentumConservation,
                                AngularMomentumConservation)
