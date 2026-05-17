"""
Hard Physical Constraints: Mass, Momentum, and Angular Momentum Conservation.
Implements §3.4.3 of the paper (Eq. 13-16).

These are deterministic, non-trainable transforms embedded in the PINN
forward pass. They guarantee physical consistency regardless of data quality.
"""

import torch
import torch.nn as nn
from typing import Tuple


# Physical constants
G_Msun = 1.3271244e20    # m^3/s^2 (solar gravitational parameter × AU^3)
AU = 1.495978707e11       # m
k_B = 1.380649e-23        # J/K


class MassConservation(nn.Module):
    """
    Hard mass conservation: n_d(r) = Q_d / (4π r^2 v_d). Eq. 13.

    The dust number density is computed deterministically from
    the production rate Q_d and dust velocity v_d. No free parameters.
    """
    def forward(self, Q_d: torch.Tensor, r: torch.Tensor,
                v_d: torch.Tensor) -> torch.Tensor:
        """
        Args:
            Q_d: Dust production rate (kg/s), shape (B,)
            r:  Radial distances (au), shape (B, N_r)
            v_d: Dust velocities (m/s), shape (B, N_r)
        Returns:
            n_d: Dust number density (m^{-3}), shape (B, N_r)
        """
        r_m = r * AU  # au → m
        n_d = Q_d.unsqueeze(-1) / (4 * torch.pi * r_m ** 2 * v_d + 1e-30)
        return n_d


class MomentumConservation(nn.Module):
    """
    Dust-gas drag momentum conservation. Eq. 14-15.

    Terminal velocity approximation (Eq. 14) or full ODE (Eq. 15)
    solved via 4th-order Runge-Kutta with 100 radial steps.
    """
    def __init__(self, use_ode: bool = True, n_steps: int = 100, C_D: float = 2.0):
        """
        Args:
            use_ode: If True, solve full ODE (Eq. 15). If False, use terminal approx (Eq. 14).
            n_steps: Number of RK4 steps (for ODE mode).
            C_D: Drag coefficient (dimensionless, ~0.5-2.0 for cometary grains).
        """
        super().__init__()
        self.use_ode = use_ode
        self.n_steps = n_steps
        self.C_D = C_D

    def forward(self, v_g: torch.Tensor, mdot_g: torch.Tensor,
                rho_d: torch.Tensor, a: torch.Tensor,
                r_n: torch.Tensor, r: torch.Tensor) -> torch.Tensor:
        """
        Args:
            v_g: Gas expansion velocity (m/s), shape (B,)
            mdot_g: Total gas mass loss rate (kg/s), shape (B,)
            rho_d: Grain density (kg/m^3), shape (B,)
            a: Grain radius (μm), shape (B,)
            r_n: Nucleus radius (km), shape (B,)
            r: Radial grid (au), shape (B, N_r)
        Returns:
            v_d: Dust velocity field (m/s), shape (B, N_r)
        """
        if not self.use_ode:
            return self._terminal_velocity(v_g, mdot_g, rho_d, a, r_n, r)
        return self._solve_ode(v_g, mdot_g, rho_d, a, r_n, r)

    def _terminal_velocity(self, v_g, mdot_g, rho_d, a, r_n, r):
        """Eq. 14: Terminal velocity approximation."""
        r_m = r * AU
        r_n_m = r_n * 1e3  # km → m
        a_m = a * 1e-6      # μm → m

        # Dimensionless drag parameter
        drag_param = (3 * self.C_D * mdot_g.unsqueeze(-1)) / \
                     (16 * torch.pi * rho_d.unsqueeze(-1) * a_m.unsqueeze(-1) *
                      v_g.unsqueeze(-1) ** 2 * r_n_m.unsqueeze(-1))

        # (r - r_n) / r factor
        radial_factor = (r_m - r_n_m.unsqueeze(-1)) / (r_m + 1e-30)

        v_d = v_g.unsqueeze(-1) * torch.sqrt(
            1.0 - torch.exp(-drag_param * radial_factor) + 1e-30
        )
        # Clamp negative/NaN values at r < r_n
        v_d = torch.clamp(v_d, min=0.0)
        return v_d

    def _solve_ode(self, v_g, mdot_g, rho_d, a, r_n, r):
        """Eq. 15: 4th-order Runge-Kutta ODE solver."""
        B = r.shape[0]
        N_r = r.shape[1]
        device = r.device

        r_n_m = r_n * 1e3
        a_m = a * 1e-6

        # Radial grid in meters
        r_grid = r * AU  # (B, N_r)

        # Initialize velocity array
        v_d = torch.zeros(B, N_r, device=device)
        v_d[:, 0] = 0.0  # Boundary condition: v_d(r_n) = 0

        dr = (r_grid[:, -1] - r_grid[:, 0]) / self.n_steps

        for i in range(1, N_r):
            r_i = r_grid[:, i]
            v_prev = v_d[:, i - 1]

            # RK4 step
            k1 = self._ode_rhs(r_i, v_prev, v_g, mdot_g, rho_d, a_m, r_n_m)
            k2 = self._ode_rhs(r_i + 0.5 * dr, v_prev + 0.5 * dr * k1,
                               v_g, mdot_g, rho_d, a_m, r_n_m)
            k3 = self._ode_rhs(r_i + 0.5 * dr, v_prev + 0.5 * dr * k2,
                               v_g, mdot_g, rho_d, a_m, r_n_m)
            k4 = self._ode_rhs(r_i + dr, v_prev + dr * k3,
                               v_g, mdot_g, rho_d, a_m, r_n_m)

            v_d[:, i] = v_prev + (dr / 6.0) * (k1 + 2 * k2 + 2 * k3 + k4)
            v_d[:, i] = torch.clamp(v_d[:, i], min=0.0)

        return v_d

    def _ode_rhs(self, r, v_d, v_g, mdot_g, rho_d, a_m, r_n_m):
        """Right-hand side of the dust-gas drag ODE (Eq. 15)."""
        # Gas density at radius r (all inputs (B,) during ODE stepping)
        rho_g = mdot_g / (4 * torch.pi * r ** 2 * v_g + 1e-30)

        # Drag term
        drag = (3 * self.C_D * rho_g * (v_g - v_d) ** 2) / \
               (4 * rho_d * a_m + 1e-30)

        # Solar gravity deceleration
        gravity = G_Msun / (r ** 2 + 1e-30)

        # dv_d/dr × v_d = drag - gravity  →  dv_d/dr = (drag - gravity) / v_d
        dv_d_dr = (drag - gravity) / (v_d + 1e-30)
        return dv_d_dr


class AngularMomentumConservation(nn.Module):
    """
    Hard angular momentum conservation via jet collimation angle. Eq. 16.

    The jet opening angle is thermodynamically constrained by the
    sublimation pressure of the dominant volatile.
    """
    def __init__(self, volatile: str = "CO"):
        super().__init__()
        self.volatile = volatile
        # Clausius-Clapeyron parameters for CO
        if volatile == "CO":
            self.A = 1e10   # Pa (prefactor)
            self.B = 764.0  # K   (sublimation enthalpy / R)
        elif volatile == "H2O":
            self.A = 3.56e12
            self.B = 6141.0
        else:
            raise ValueError(f"Unknown volatile: {volatile}")

    def sublimation_pressure(self, T: torch.Tensor) -> torch.Tensor:
        """Clausius-Clapeyron: P_sub(T) = A * exp(-B / T)."""
        return self.A * torch.exp(-self.B / (T + 1e-30))

    def forward(self, mdot_g: torch.Tensor, v_g: torch.Tensor,
                r_n: torch.Tensor, T: torch.Tensor) -> torch.Tensor:
        """
        Args:
            mdot_g: Gas mass loss rate (kg/s), shape (B,)
            v_g: Gas velocity (m/s), shape (B,)
            r_n: Nucleus radius (km), shape (B,)
            T: Equilibrium temperature (K), shape (B,)
        Returns:
            theta_jet: Jet opening angle (radians), shape (B,)
        """
        r_n_m = r_n * 1e3
        P_sub = self.sublimation_pressure(T)

        # Energy-limited outflow: sin(theta) ∝ sqrt(mdot_g * v_g / (r_n^2 * P_sub))
        ratio = (mdot_g * v_g) / (4 * torch.pi * r_n_m ** 2 * P_sub + 1e-30)
        sin_theta = torch.sqrt(torch.clamp(ratio, max=1.0))

        theta_jet = 2 * torch.asin(sin_theta)
        return theta_jet
