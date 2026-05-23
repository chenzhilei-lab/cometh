"""
Adversarial Observing Strategy Optimization.
Implements §3.7 of the paper (Eq. 30).

Static grid-search optimizer for ToO program planning.
RL extension (§3.7.3) described but not implemented in this release.
"""

import torch
import numpy as np
from typing import Dict, List, Tuple, Optional
from itertools import product


class ObservingStrategyOptimizer:
    """
    Optimizes telescope time allocation for newly discovered interstellar comets.

    Given a discovery magnitude and available instruments, recommends the
    observing plan that minimizes expected posterior covariance (Eq. 30).

    Static (grid search) mode is production-ready.
    RL mode is described in the paper but not yet implemented.
    """
    def __init__(self):
        # Configurable options
        self.band_options = ['R-only', 'BVR', 'BVRI']
        self.spectroscopy_options = [True, False]
        self.epoch_options = [3, 5, 7, 10]
        self.cadence_options = ['uniform', 'perihelion-weighted']

    def recommend(self, discovery_magnitude: float,
                  r_h_range: Tuple[float, float],
                  available_instruments: List[str] = None,
                  total_budget_hours: float = 10.0) -> Dict:
        """
        Recommend optimal observing strategy for a discovery scenario.

        Args:
            discovery_magnitude: Approximate magnitude at discovery
            r_h_range: (r_h_min, r_h_max) in au
            available_instruments: List of available instruments
            total_budget_hours: Total telescope time available
        Returns:
            dict with recommended strategy and expected uncertainties
        """
        # Classify discovery scenario
        if discovery_magnitude < 18 and r_h_range[0] < 2.5:
            scenario = 'bright'
        elif discovery_magnitude > 20 or r_h_range[0] > 4:
            scenario = 'faint'
        else:
            scenario = 'nominal'

        # Pre-computed optimal strategies from Table 2 in the paper
        strategies = {
            'bright': {
                'bands': 'BVRI',
                'spectroscopy': True,
                'n_epochs': 5,
                'cadence': 'perihelion-weighted',
                'expected_dCO_H2O': 0.12,
                'expected_dQd': 0.08,
            },
            'nominal': {
                'bands': 'BVR',
                'spectroscopy': True,
                'n_epochs': 7,
                'cadence': 'uniform',
                'expected_dCO_H2O': 0.18,
                'expected_dQd': 0.12,
            },
            'faint': {
                'bands': 'R-only',
                'spectroscopy': False,
                'n_epochs': 10,
                'cadence': 'uniform',
                'expected_dCO_H2O': float('inf'),  # >50%, unconstrained
                'expected_dQd': 0.25,
            },
        }

        rec = strategies[scenario]
        # Compute per-epoch exposure from budget
        n_bands = len(rec['bands'].replace('-only', ''))
        if rec['spectroscopy']:
            spec_time = 1.5  # hours per spectroscopic epoch
            n_spec_epochs = 1
            img_time = total_budget_hours - spec_time * n_spec_epochs
        else:
            img_time = total_budget_hours

        exposure_per_epoch = img_time / rec['n_epochs'] / n_bands

        return {
            'scenario': scenario,
            'discovery_magnitude': discovery_magnitude,
            'r_h_range': r_h_range,
            **rec,
            'exposure_per_band_per_epoch_hours': round(exposure_per_epoch, 2),
            'spectroscopy_epochs': 1 if rec['spectroscopy'] else 0,
            'recommendation_note':
                self._get_note(scenario, rec['spectroscopy']),
        }

    def _get_note(self, scenario: str, spectroscopy: bool) -> str:
        notes = {
            'bright': ("Bright target with high SNR potential. "
                       "Spectroscopy strongly recommended — CO/H2O "
                       "constrained to ±12%."),
            'nominal': ("Typical interstellar comet. 7 epochs recommended. "
                        "Include at least one spectroscopic epoch for gas "
                        "abundance constraints (±18%)."),
            'faint': ("Faint target near detection limit. Spectroscopy not "
                      "recommended — gas abundances will be unconstrained. "
                      "Focus on dust parameters from multi-epoch R-band "
                      "photometry. OOD detector should be consulted for "
                      "all parameter estimates."),
        }
        return notes.get(scenario, "")

    def grid_search(self, discovery_magnitude: float,
                    r_h_range: Tuple[float, float],
                    n_synthetic: int = 100) -> List[Dict]:
        """
        Full grid search over configuration space (Eq. 30).
        Evaluates all combinations and ranks by expected covariance.

        Args:
            discovery_magnitude: Discovery magnitude
            r_h_range: Heliocentric distance range (au)
            n_synthetic: Number of synthetic comets per configuration
        Returns:
            Sorted list of (config, score) pairs
        """
        results = []
        configs = product(self.band_options, self.spectroscopy_options,
                          self.epoch_options, self.cadence_options)

        for bands, spec, epochs, cadence in configs:
            # Simulate expected uncertainty (simplified: uses analytic approx)
            n_band_count = len(bands.replace('-only', ''))
            base_snr = 20 * 10 ** (-0.2 * (discovery_magnitude - 18))

            # Dust constraint scales with SNR and number of bands
            dQd = 0.08 * (5 / base_snr) * (3 / n_band_count) * (5 / epochs)
            dQd = max(dQd, 0.03)  # Floor at 3%

            # Gas constraint requires spectroscopy
            if spec and base_snr > 3:
                dCO = 0.12 * (5 / base_snr)
            else:
                dCO = float('inf')

            score = 1.0 / (dQd + min(dCO, 1.0) + 1e-6)
            results.append({
                'bands': bands, 'spectroscopy': spec,
                'epochs': epochs, 'cadence': cadence,
                'expected_dQd': round(dQd, 3),
                'expected_dCO_H2O': round(dCO, 3) if dCO < float('inf') else 'unconstrained',
                'score': round(score, 6),
            })

        return sorted(results, key=lambda r: r['score'], reverse=True)


# ============================================================
# RL Extension (described in §3.7.3, not implemented)
# ============================================================

class RLObservingAgent:
    """
    Reinforcement Learning agent for dynamic cadence adjustment.
    Described in §3.7.3; NOT implemented in this release.

    Uses Proximal Policy Optimization (PPO) to learn adaptive
    observing strategies from simulated ToO episodes.

    This class is a placeholder documenting the planned interface.
    """
    def __init__(self):
        raise NotImplementedError(
            "RL observing agent is a proposed extension (§3.7.3) "
            "and has not been implemented. Use the static "
            "ObservingStrategyOptimizer for production use."
        )
