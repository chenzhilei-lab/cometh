"""
Physics-Informed Neural Network (PINN) for Dust and Gas Parameter Inversion.
Implements §3.4 of the paper (Eq. 17-19, Table 1).

Two jointly trained networks:
  1. u_theta: Physics network — radiative transfer forward model
  2. p_phi:   Inversion network — observables → physical parameters

Hard constraints (§3.4.3) are embedded as deterministic transforms
in the forward pass via the hard_constraints.py module.
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
from typing import Tuple, Dict
from .hard_constraints import MassConservation, MomentumConservation, \
    AngularMomentumConservation


class FourierFeatureMapping(nn.Module):
    """Random Fourier feature mapping for high-frequency spatial variations."""
    def __init__(self, in_dim: int, out_dim: int, sigma: float = 10.0):
        super().__init__()
        self.B = nn.Parameter(torch.randn(in_dim, out_dim // 2) * sigma,
                              requires_grad=False)
        self.out_dim = out_dim

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        proj = x @ self.B
        return torch.cat([torch.sin(proj), torch.cos(proj)], dim=-1)


class Swish(nn.Module):
    """Swish activation: x * sigmoid(x)."""
    def forward(self, x): return x * torch.sigmoid(x)


class PhysicsNetwork(nn.Module):
    """
    PINN physics network u_theta: (r, lambda, r_h, Delta) → I_lambda.
    8-layer MLP with Fourier features, Swish activations.
    Implements Table 1 (top section) in the paper.
    """
    def __init__(self, in_dim: int = 6, hidden_dim: int = 256,
                 n_hidden: int = 6, fourier_dim: int = 128):
        super().__init__()
        self.fourier = FourierFeatureMapping(in_dim, fourier_dim)
        layers = []
        prev_dim = fourier_dim
        for i in range(n_hidden + 1):
            if i == 0:
                layers.append(nn.Linear(prev_dim, hidden_dim))
            else:
                layers.append(nn.Linear(hidden_dim, hidden_dim))
            layers.append(Swish())
            prev_dim = hidden_dim
        layers.append(nn.Linear(hidden_dim, 1))
        layers.append(nn.Softplus())
        self.net = nn.Sequential(*layers)

    def forward(self, r: torch.Tensor, lam: torch.Tensor,
                r_h: torch.Tensor, Delta: torch.Tensor) -> torch.Tensor:
        """
        Args:
            r: Line-of-sight distance grid (au), shape (B, N_r, 3)
            lam: Wavelengths (nm), shape (B, N_lam)
            r_h: Heliocentric distances (au), shape (B,)
            Delta: Geocentric distances (au), shape (B,)
        Returns:
            I_lam: Specific intensity (W/m^2/sr/nm), shape (B, N_lam)
        """
        # Flatten spatial + wavelength dimensions for MLP input
        B = r.size(0)
        r_flat = r.view(B, -1, 3)  # (B, N_r, 3)
        # Build input: (r_x, r_y, r_z, lambda, r_h, Delta)
        lam_expanded = lam.unsqueeze(1).expand(-1, r_flat.size(1), -1)
        # Simplified: mean over radial dimension for demo
        r_mean = r_flat.mean(dim=1)          # (B, 3)
        x = torch.cat([r_mean, lam.mean(dim=1, keepdim=True),
                       r_h.unsqueeze(-1), Delta.unsqueeze(-1)], dim=-1)
        return self.net(x)


class CrossModalAttention(nn.Module):
    """Cross-modal attention fusion of imaging and spectroscopic features."""
    def __init__(self, img_dim: int, spec_dim: int, hidden_dim: int = 256,
                 n_heads: int = 4):
        super().__init__()
        self.attn = nn.MultiheadAttention(hidden_dim, n_heads, batch_first=True)
        self.img_proj = nn.Linear(img_dim, hidden_dim)
        self.spec_proj = nn.Linear(spec_dim, hidden_dim)

    def forward(self, img_feat: torch.Tensor,
                spec_feat: torch.Tensor) -> torch.Tensor:
        """Fuse imaging and spectral features via cross-attention."""
        img_h = self.img_proj(img_feat).unsqueeze(1)   # (B, 1, H)
        spec_h = self.spec_proj(spec_feat).unsqueeze(1) # (B, 1, H)
        fused, _ = self.attn(img_h, spec_h, spec_h)
        return fused.squeeze(1)


class InversionNetwork(nn.Module):
    """
    PINN inversion network p_phi: (I_obs, P_obs) → (Q_d, alpha, a_max, Q_gas).
    CNN encoder for imaging + FC for spectroscopy + cross-modal attention.
    Implements Table 1 (middle section) in the paper.
    """
    def __init__(self, n_bands: int = 4, spec_dim: int = 128,
                 hidden_dim: int = 256, n_res_blocks: int = 4):
        super().__init__()
        # Imaging encoder (strided CNN)
        self.img_encoder = nn.Sequential(
            nn.Conv2d(n_bands, 64, 3, padding=1), nn.ReLU(),
            nn.Conv2d(64, 64, 3, stride=2, padding=1), nn.ReLU(),
            nn.Conv2d(64, 128, 3, stride=2, padding=1), nn.ReLU(),
            nn.Conv2d(128, 256, 3, stride=2, padding=1), nn.ReLU(),
            nn.Conv2d(256, 512, 3, stride=2, padding=1), nn.ReLU(),
            nn.AdaptiveAvgPool2d(1),
        )

        # Spectroscopy encoder
        self.spec_encoder = nn.Sequential(
            nn.Linear(1, 64), nn.ReLU(),  # Wavelength → features
            nn.Linear(64, spec_dim), nn.ReLU(),
        )

        # Cross-modal fusion
        self.fusion = CrossModalAttention(512, spec_dim, hidden_dim)

        # Residual blocks after fusion
        res_blocks = []
        for _ in range(n_res_blocks):
            block = nn.Sequential(
                nn.Linear(hidden_dim, hidden_dim), nn.ReLU(),
                nn.Linear(hidden_dim, hidden_dim),
            )
            res_blocks.append(block)
        self.res_blocks = nn.ModuleList(res_blocks)

        # Uncertainty heads: (mu, sigma) for each parameter
        self.head_Qd = nn.Sequential(nn.Linear(hidden_dim, 64), nn.ReLU(),
                                     nn.Linear(64, 2))        # (mu, sigma)
        self.head_alpha = nn.Sequential(nn.Linear(hidden_dim, 64), nn.ReLU(),
                                        nn.Linear(64, 2))
        self.head_amax = nn.Sequential(nn.Linear(hidden_dim, 64), nn.ReLU(),
                                       nn.Linear(64, 2))
        self.head_CO_H2O = nn.Sequential(nn.Linear(hidden_dim, 64), nn.ReLU(),
                                          nn.Linear(64, 2))
        self.head_C2_CN = nn.Sequential(nn.Linear(hidden_dim, 64), nn.ReLU(),
                                         nn.Linear(64, 2))

    def forward(self, img: torch.Tensor, spec: torch.Tensor) -> Dict[str, torch.Tensor]:
        """
        Args:
            img: Multi-band images, shape (B, N_bands, H, W)
            spec: Spectra, shape (B, N_lambda)
        Returns:
            params: Dict with (mu, sigma) for Q_d, alpha, a_max, CO/H2O, C2/CN
        """
        # Encode modalities
        img_feat = self.img_encoder(img).flatten(1)   # (B, 512)
        spec_feat = self.spec_encoder(spec.unsqueeze(-1)).mean(dim=1)  # (B, 128)

        # Fuse
        fused = self.fusion(img_feat, spec_feat)

        # Residual blocks
        for res_block in self.res_blocks:
            fused = fused + res_block(fused)

        # Parameter heads
        Qd_out = self.head_Qd(fused)
        alpha_out = self.head_alpha(fused)
        amax_out = self.head_amax(fused)
        co_out = self.head_CO_H2O(fused)
        c2_out = self.head_C2_CN(fused)

        return {
            'Q_d':     {'mu': Qd_out[:, 0], 'sigma': F.softplus(Qd_out[:, 1])},
            'alpha':   {'mu': alpha_out[:, 0], 'sigma': F.softplus(alpha_out[:, 1])},
            'a_max':   {'mu': F.softplus(amax_out[:, 0]), 'sigma': F.softplus(amax_out[:, 1])},
            'CO_H2O':  {'mu': F.softplus(co_out[:, 0]), 'sigma': F.softplus(co_out[:, 1])},
            'C2_CN':   {'mu': c2_out[:, 0], 'sigma': F.softplus(c2_out[:, 1])},
        }


class PINNInversion(nn.Module):
    """
    Full PINN: PhysicsNetwork + InversionNetwork + Hard Constraints.
    Bayesian uncertainty via MC Dropout (Eq. 18).
    """
    def __init__(self, n_bands: int = 4, hard_constraints: bool = True):
        super().__init__()
        self.physics = PhysicsNetwork()
        self.inversion = InversionNetwork(n_bands=n_bands)
        self.hard_constraints = hard_constraints
        self.mass_cons = MassConservation()
        self.momentum_cons = MomentumConservation(use_ode=True)
        self.angular_cons = AngularMomentumConservation(volatile="CO")
        self.dropout = nn.Dropout(0.12)  # MC Dropout rate

    def forward(self, img: torch.Tensor, spec: torch.Tensor,
                r: torch.Tensor, r_h: torch.Tensor, Delta: torch.Tensor,
                mc_samples: int = 50) -> Tuple[Dict, Dict]:
        """
        Args:
            img, spec: Observational inputs
            r, r_h, Delta: Geometry
            mc_samples: Number of MC dropout samples for uncertainty
        Returns:
            params: Parameter estimates with uncertainty
            fields: Physically constrained density/velocity fields
        """
        # MC Dropout for Bayesian uncertainty (Eq. 18)
        self.train()  # Enable dropout at inference
        all_params = []
        for _ in range(mc_samples):
            params = self.inversion(img, spec)
            all_params.append(params)
        self.eval()

        # Aggregate MC samples
        agg_params = {}
        for key in all_params[0].keys():
            mus = torch.stack([p[key]['mu'] for p in all_params])
            sigmas = torch.stack([p[key]['sigma'] for p in all_params])
            agg_params[key] = {
                'mu': mus.mean(dim=0),
                'sigma': (mus.var(dim=0) + sigmas.mean(dim=0)).sqrt()
            }

        # Hard constraint transforms (Eq. 13-16)
        fields = {}
        if self.hard_constraints:
            Q_d = agg_params['Q_d']['mu']
            alpha = agg_params['alpha']['mu']
            CO_H2O = agg_params['CO_H2O']['mu']
            # Derive derived quantities
            v_g = 0.5 * torch.ones_like(Q_d) * 1e3  # m/s (typical)
            mdot_g = Q_d * CO_H2O  # Approximate gas mass loss
            rho_d = 1000 * torch.ones_like(Q_d)     # kg/m^3 (silicate)
            a_median = 1.0 * torch.ones_like(Q_d)   # μm
            r_n = 1.0 * torch.ones_like(Q_d)        # km
            T = 180 * torch.ones_like(Q_d)           # K (typical at 3 au)

            # Build radial grid
            B = img.size(0)
            r_grid = torch.linspace(1.0, 10.0, 100, device=img.device)
            r_grid = r_grid.unsqueeze(0).expand(B, -1)

            fields['n_d'] = self.mass_cons(Q_d, r_grid,
                                           torch.ones_like(r_grid) * v_g.unsqueeze(-1))
            fields['v_d'] = self.momentum_cons(v_g, mdot_g, rho_d, a_median, r_n, r_grid)
            fields['theta_jet'] = self.angular_cons(mdot_g, v_g, r_n, T)

        return agg_params, fields

    @classmethod
    def from_pretrained(cls, path: str, **kwargs) -> 'PINNInversion':
        """Load pre-trained weights."""
        model = cls(**kwargs)
        state_dict = torch.load(path, map_location='cpu', weights_only=True)
        model.load_state_dict(state_dict)
        model.eval()
        return model


# ============================================================
# Loss Functions (Eq. 17)
# ============================================================

class PINNLoss(nn.Module):
    """
    Composite PINN loss: L_data + gamma_1 * L_PDE + gamma_2 * L_BC + gamma_3 * L_cons.
    Eq. 17 in the paper.
    """
    def __init__(self, gamma_1: float = 1.0, gamma_2: float = 0.5,
                 gamma_3: float = 0.3):
        super().__init__()
        self.gamma_1 = gamma_1
        self.gamma_2 = gamma_2
        self.gamma_3 = gamma_3

    def forward(self, I_pred: torch.Tensor, I_obs: torch.Tensor,
                n_d: torch.Tensor, sigma_d: torch.Tensor,
                I_nucleus: Optional[torch.Tensor] = None,
                mdot_g: Optional[torch.Tensor] = None,
                theta_jet: Optional[torch.Tensor] = None) -> Tuple[torch.Tensor, dict]:
        """
        Args:
            I_pred: Predicted intensity
            I_obs: Observed intensity
            n_d: Dust number density (from mass conservation)
            sigma_d: Scattering cross-section
            I_nucleus: Boundary condition at nucleus surface
        """
        # Data fidelity (Eq. not numbered separately)
        L_data = F.mse_loss(I_pred, I_obs)

        # PDE residual (Eq. 19 in paper): dI/ds + n_d*sigma_d*I - n_d*sigma_d*B = 0
        # Simplified finite-difference approximation
        dI_ds = (I_pred[:, 1:] - I_pred[:, :-1])  # First difference
        B_lambda = I_obs.mean(dim=-1, keepdim=True)  # Approximate Planck function
        residual = dI_ds + n_d[:, 1:] * sigma_d[:, 1:] * I_pred[:, 1:] - \
                   n_d[:, 1:] * sigma_d[:, 1:] * B_lambda[:, 1:]
        L_PDE = (residual ** 2).mean()

        # Boundary condition (Eq. 21)
        L_BC = torch.tensor(0.0, device=I_pred.device)
        if I_nucleus is not None:
            L_BC = F.mse_loss(I_pred[:, 0], I_nucleus)

        # Conservation loss (hard constraint satisfaction check)
        L_cons = torch.tensor(0.0, device=I_pred.device)
        if mdot_g is not None and theta_jet is not None:
            # Angular momentum flux should be monotonic in mdot_g
            L_cons = F.mse_loss(torch.sin(theta_jet) ** 2,
                                torch.clamp(mdot_g.unsqueeze(-1) / 1e6, max=1.0))

        total = L_data + self.gamma_1 * L_PDE + self.gamma_2 * L_BC + \
                self.gamma_3 * L_cons

        return total, {'L_data': L_data.item(), 'L_PDE': L_PDE.item(),
                       'L_BC': L_BC.item(), 'L_cons': L_cons.item()}
