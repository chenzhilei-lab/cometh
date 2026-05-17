"""
Meta-Learning with Adversarial Domain Adaptation.
Implements §3.5 of the paper (Eq. 25-29).

MAML (Finn et al. 2017) + adversarial domain classifier (Ganin et al. 2016)
for few-shot transfer from solar system to interstellar comets.
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
from typing import Tuple, List
from collections import OrderedDict


class DomainClassifier(nn.Module):
    """
    Binary domain classifier D_psi: R^d → [0, 1].
    Discriminates source (solar system) from target (interstellar) features.
    3-layer MLP with LeakyReLU, as specified in Table 1 of the paper.
    """
    def __init__(self, input_dim: int = 256, hidden_dim: int = 128):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(input_dim, hidden_dim),
            nn.LeakyReLU(0.2),
            nn.Linear(hidden_dim, hidden_dim),
            nn.LeakyReLU(0.2),
            nn.Linear(hidden_dim, 1),
            nn.Sigmoid(),
        )

    def forward(self, features: torch.Tensor) -> torch.Tensor:
        return self.net(features)


class GradientReversalLayer(torch.autograd.Function):
    """Gradient reversal for adversarial training (Ganin et al. 2016)."""
    @staticmethod
    def forward(ctx, x, lambda_val=1.0):
        ctx.lambda_val = lambda_val
        return x.view_as(x)

    @staticmethod
    def backward(ctx, grad_output):
        return grad_output.neg() * ctx.lambda_val, None


def grad_reverse(x: torch.Tensor, lambda_val: float = 1.0) -> torch.Tensor:
    return GradientReversalLayer.apply(x, lambda_val)


class MAMLAdapter(nn.Module):
    """
    Model-Agnostic Meta-Learning (MAML) for comet domain adaptation.
    Eq. 28 in the paper.

    Learns network initializations that can adapt to new comet types
    with K=10 support examples.
    """
    def __init__(self, feature_dim: int = 256, inner_lr: float = 0.01):
        super().__init__()
        self.feature_dim = feature_dim
        self.inner_lr = inner_lr
        self.domain_classifier = DomainClassifier(feature_dim)

    def adapt(self, support_x: torch.Tensor, support_y: torch.Tensor,
              n_steps: int = 5) -> OrderedDict:
        """
        Fast adaptation to a new comet type.
        Eq. 28: theta' = theta - alpha * grad L_task(theta)

        Args:
            support_x: K support images, shape (K, ...)
            support_y: K support labels
            n_steps: Number of inner-loop gradient steps
        Returns:
            Adapted parameters
        """
        params = OrderedDict(self.domain_classifier.named_parameters())
        for _ in range(n_steps):
            pred = self.domain_classifier(support_x)
            loss = F.binary_cross_entropy(pred, support_y)
            grads = torch.autograd.grad(loss, params.values(), create_graph=True)
            for (name, p), g in zip(params.items(), grads):
                params[name] = p - self.inner_lr * g
        return params

    def forward(self, features: torch.Tensor,
                domain_labels: torch.Tensor,
                lambda_adv: float = 1.0) -> Tuple[torch.Tensor, torch.Tensor]:
        """
        Adversarial domain alignment (Eq. 29).
        Returns domain classifier loss for both forward (feature extractor)
        and backward (domain classifier) optimization.
        """
        reversed_features = grad_reverse(features, lambda_adv)
        domain_pred = self.domain_classifier(reversed_features)
        loss_dom = F.binary_cross_entropy(domain_pred.squeeze(), domain_labels)
        return domain_pred, loss_dom


# ============================================================
# MMD Computation (Eq. 25)
# ============================================================

def compute_mmd(x: torch.Tensor, y: torch.Tensor,
                kernel: str = 'gaussian') -> float:
    """
    Maximum Mean Discrepancy between two feature distributions.
    Eq. 25 in the paper.

    Args:
        x: Source features, shape (n_s, d)
        y: Target features, shape (n_t, d)
        kernel: 'gaussian' or 'linear'
    Returns:
        mmd: MMD value
    """
    if kernel == 'gaussian':
        # Median heuristic for bandwidth
        pairwise_dist = torch.cdist(x, y, p=2)
        sigma = pairwise_dist.median()
        k_xx = torch.exp(-torch.cdist(x, x, p=2) ** 2 / (2 * sigma ** 2))
        k_yy = torch.exp(-torch.cdist(y, y, p=2) ** 2 / (2 * sigma ** 2))
        k_xy = torch.exp(-torch.cdist(x, y, p=2) ** 2 / (2 * sigma ** 2))
    else:
        k_xx = x @ x.T
        k_yy = y @ y.T
        k_xy = x @ y.T

    mmd = k_xx.mean() + k_yy.mean() - 2 * k_xy.mean()
    return mmd.item()
