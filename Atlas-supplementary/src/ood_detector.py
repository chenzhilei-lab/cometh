"""
Self-Diagnosing Out-of-Distribution (OOD) Detector.
Implements §3.6 of the paper (Eq. 22-24).

Gaussian Mixture Model in PINN latent space with automatic
confidence interval inflation on OOD detection.
"""

import torch
import torch.nn as nn
import numpy as np
from sklearn.mixture import GaussianMixture
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler
from typing import Tuple, Optional
import pickle


class OODDetector(nn.Module):
    """
    GMM-based OOD detector in PINN encoder latent space.

    Fits a K-component GMM to training latent codes (Eq. 22).
    At inference, flags inputs whose GMM log-likelihood falls below
    the 5th percentile of the validation distribution (Eq. 23).
    On OOD flag, automatically inflates CI by 3× (§3.6.2).
    """
    def __init__(self, latent_dim: int = 256, n_components: int = 10,
                 pca_variance: float = 0.95, threshold_percentile: float = 5.0,
                 ci_inflation: float = 3.0):
        super().__init__()
        self.latent_dim = latent_dim
        self.n_components = n_components
        self.pca_variance = pca_variance
        self.threshold_percentile = threshold_percentile
        self.ci_inflation = ci_inflation

        # To be fitted
        self.scaler = StandardScaler()
        self.pca = PCA(n_components=pca_variance)
        self.gmm = GaussianMixture(n_components=n_components, covariance_type='full',
                                   random_state=42)
        self.threshold = None
        self._fitted = False

    def fit(self, latent_codes: np.ndarray):
        """
        Fit GMM on PINN encoder latent codes from synthetic training set.

        Args:
            latent_codes: shape (N_train, 256) — PINN encoder penultimate layer outputs
        """
        # Standardize
        latent_scaled = self.scaler.fit_transform(latent_codes)

        # PCA whitening (retain pca_variance fraction of variance)
        self.pca = PCA(n_components=self.pca_variance, whiten=True)
        latent_pca = self.pca.fit_transform(latent_scaled)
        actual_dim = latent_pca.shape[1]
        print(f"PCA: {self.latent_dim}d → {actual_dim}d "
              f"(retained {self.pca_variance:.0%} variance)")

        # Fit GMM (Eq. 22)
        self.gmm = GaussianMixture(n_components=self.n_components,
                                   covariance_type='full', random_state=42)
        self.gmm.fit(latent_pca)

        # Set threshold at specified percentile of training scores (Eq. 23)
        train_scores = self.gmm.score_samples(latent_pca)
        self.threshold = np.percentile(train_scores, self.threshold_percentile)
        self._fitted = True
        print(f"GMM fitted: K={self.n_components}, threshold={self.threshold:.2f} "
              f"(at {self.threshold_percentile}th percentile)")

    def forward(self, latent: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor]:
        """
        Detect OOD inputs and return OOD flag + inflated flag.

        Args:
            latent: PINN encoder output, shape (B, 256)
        Returns:
            is_ood: bool tensor, shape (B,) — True if OOD detected
            scores: log-likelihood scores, shape (B,)
        """
        if not self._fitted:
            raise RuntimeError("OODDetector must be fitted before inference. "
                               "Call .fit(latent_codes) first.")

        latent_np = latent.detach().cpu().numpy()
        latent_scaled = self.scaler.transform(latent_np)
        latent_pca = self.pca.transform(latent_scaled)
        scores = self.gmm.score_samples(latent_pca)

        is_ood = torch.tensor(scores < self.threshold, device=latent.device)
        scores_tensor = torch.tensor(scores, device=latent.device)
        return is_ood, scores_tensor

    def apply_ci_inflation(self, params: dict, is_ood: torch.Tensor) -> dict:
        """
        Apply 3× CI inflation for OOD-flagged inputs (§3.6.2).

        Args:
            params: Parameter dict with 'mu' and 'sigma' keys
            is_ood: OOD flag, shape (B,)
        Returns:
            params with inflated sigma for OOD samples
        """
        inflated = {}
        for key, value in params.items():
            mu = value['mu'].clone()
            sigma = value['sigma'].clone()
            # Inflate sigma by ci_inflation factor where OOD
            sigma[is_ood] = sigma[is_ood] * self.ci_inflation
            inflated[key] = {'mu': mu, 'sigma': sigma}
        return inflated

    def save(self, path: str):
        """Save fitted detector to disk."""
        state = {
            'scaler': self.scaler,
            'pca': self.pca,
            'gmm': self.gmm,
            'threshold': self.threshold,
            'latent_dim': self.latent_dim,
            'n_components': self.n_components,
            'pca_variance': self.pca_variance,
            'threshold_percentile': self.threshold_percentile,
            'ci_inflation': self.ci_inflation,
            '_fitted': self._fitted,
        }
        with open(path, 'wb') as f:
            pickle.dump(state, f)

    @classmethod
    def load(cls, path: str) -> 'OODDetector':
        """Load fitted detector from disk."""
        with open(path, 'rb') as f:
            state = pickle.load(f)
        detector = cls(
            latent_dim=state['latent_dim'],
            n_components=state['n_components'],
            pca_variance=state['pca_variance'],
            threshold_percentile=state['threshold_percentile'],
            ci_inflation=state['ci_inflation'],
        )
        detector.scaler = state['scaler']
        detector.pca = state['pca']
        detector.gmm = state['gmm']
        detector.threshold = state['threshold']
        detector._fitted = state['_fitted']
        return detector


# ============================================================
# Performance Metrics
# ============================================================

def compute_ood_metrics(is_ood_pred: torch.Tensor, is_ood_true: torch.Tensor) -> dict:
    """Compute OOD detection performance metrics with binomial CI."""
    n = len(is_ood_true)
    tp = ((is_ood_pred == 1) & (is_ood_true == 1)).sum().item()
    tn = ((is_ood_pred == 0) & (is_ood_true == 0)).sum().item()
    fp = ((is_ood_pred == 1) & (is_ood_true == 0)).sum().item()
    fn = ((is_ood_pred == 0) & (is_ood_true == 1)).sum().item()

    tpr = tp / (tp + fn + 1e-10)  # True positive rate (OOD recall)
    fpr = fp / (fp + tn + 1e-10)  # False positive rate

    # Binomial 95% CI (Wilson score interval)
    z = 1.96
    p = tpr
    denominator = 1 + z**2 / n
    centre = (p + z**2 / (2 * n)) / denominator
    margin = z * np.sqrt((p * (1 - p) + z**2 / (4 * n)) / n) / denominator
    ci_lower = max(0, centre - margin)
    ci_upper = min(1, centre + margin)

    return {
        'TPR': tpr, 'FPR': fpr,
        'TP': tp, 'TN': tn, 'FP': fp, 'FN': fn,
        '95%_CI': [ci_lower, ci_upper]
    }
