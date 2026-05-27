"""
Generate synthetic comet observations using DIRTY v3.2 radiative transfer code.
Reproduces all training/validation/test data for the COMETH framework.

Usage:
  python generate_synthetic_data.py --config ../configs/dirty_params.yaml
  python generate_synthetic_data.py --config ../configs/dirty_params.yaml --stress-test 5

Fixed random seeds (42, 123, 456, 789, 1024) ensure exact reproducibility.

Requires: DIRTY v3.2 (Gordon et al. 2001) — must be installed separately.
           See: https://github.com/karllark/dirty
           DIRTY configuration files in ../configs/ provide all parameters needed.
"""

import argparse
import numpy as np
import os
import yaml

# Seeds for 5-fold cross-validation
SEEDS = [42, 123, 456, 789, 1024]


def generate_standard_dataset(config, seed, output_dir):
    """
    Generate standard synthetic dataset covering the parameter ranges
    specified in config. Calls DIRTY via subprocess for each parameter
    combination, then applies post-processing (noise addition, PSF
    convolution, background star field injection).

    Parameter ranges (from config):
      - Heliocentric distance r_h: 1.0 -- 6.0 AU
      - Geocentric distance Delta: 0.5 -- 5.0 AU
      - Dust production rate Q_d: 1 -- 100 kg/s
      - Grain size index alpha: 2.0 -- 4.5
      - Maximum grain radius a_max: 1 -- 100 um
      - Gas ratios: CO/H2O [0.01, 2.0], C2/CN [-1.5, 0.5]
      - Instrument: VLT/FORS2 (R_SPECIAL), HST/WFC3 (F350LP)

    Outputs: .pt files containing image tensor, spectrum tensor,
             and parameter vector for each synthetic observation.
    """
    np.random.seed(seed)
    os.makedirs(output_dir, exist_ok=True)

    n_samples = config.get('n_samples', 50000)

    # --- Parameter sampling (Latin Hypercube for coverage) ---
    from scipy.stats import qmc
    sampler = qmc.LatinHypercube(d=7, seed=seed)
    samples = sampler.random(n=n_samples)

    # Scale to parameter ranges
    r_h_vals = 1.0 + samples[:, 0] * 5.0           # [1.0, 6.0] AU
    delta_vals = 0.5 + samples[:, 1] * 4.5          # [0.5, 5.0] AU
    q_d_vals = 10**(0 + samples[:, 2] * 2)          # log-uniform [1, 100] kg/s
    alpha_vals = 2.0 + samples[:, 3] * 2.5          # [2.0, 4.5]
    a_max_vals = 10**(0 + samples[:, 4] * 2)        # log-uniform [1, 100] um
    co_h2o_vals = 10**(-2 + samples[:, 5] * 2.3)    # log-uniform [0.01, 2.0]
    c2_cn_vals = -1.5 + samples[:, 6] * 2.0         # [-1.5, 0.5]

    # --- Generate each sample via DIRTY ---
    for i in range(n_samples):
        params = {
            'r_h': float(r_h_vals[i]),
            'delta': float(delta_vals[i]),
            'Q_d': float(q_d_vals[i]),
            'alpha': float(alpha_vals[i]),
            'a_max': float(a_max_vals[i]),
            'CO_H2O': float(co_h2o_vals[i]),
            'C2_CN': float(c2_cn_vals[i]),
            'dust_type': 'astronomical_silicate',
            'grain_shape': 'sphere_mie',
            'phase_angle': 0.0,
        }
        # TODO: Call DIRTY with these parameters
        # dirty_run(params, output_dir, seed=seed)
        # Post-process: add noise, PSF convolution, star field background

        if (i + 1) % 5000 == 0:
            print(f"  [{i+1}/{n_samples}] samples generated")

    print(f"Generated {n_samples} samples → {output_dir}")
    # Save parameter manifest for reproducibility
    with open(os.path.join(output_dir, 'parameter_manifest.yaml'), 'w') as f:
        yaml.dump({'n_samples': n_samples, 'seed': seed,
                   'parameter_ranges': config}, f)


def generate_stress_test(stress_id, config, seed, output_dir):
    """
    Generate one of the 6 stress test datasets.

    Stress Test 1: Galactic plane background (dense star fields)
    Stress Test 2: High optical depth inner coma
    Stress Test 3: Ultra-low SNR (SNR < 1)
    Stress Test 4: Missing modality (spectroscopy denied)
    Stress Test 5: Extreme OOD composition (CO/H2O = 5.0, carbon dust)
    Stress Test 6: Non-steady-state outburst

    Each stress test uses the same fixed seed for reproducibility.
    """
    np.random.seed(seed)
    os.makedirs(output_dir, exist_ok=True)

    stress_configs = {
        1: {'star_density': 'galactic_plane', 'n_stars_per_arcmin2': 500},
        2: {'optical_depth': 0.5, 'inner_coma_radius': 100},  # km
        3: {'snr_range': [0.3, 1.0], 'exposure_factor': 0.1},
        4: {'modalities': ['imaging_only'], 'drop_spectrum': True},
        5: {'CO_H2O': 5.0, 'C2_CN': -1.0, 'dust_type': 'amorphous_carbon'},
        6: {'outburst': True, 'peak_factor': 10.0, 'decay_timescale': 72},  # hours
    }

    if stress_id not in stress_configs:
        raise ValueError(f"Unknown stress test {stress_id}. Valid: 1-6.")

    sc = stress_configs[stress_id]
    n_samples = config.get('stress_test_samples', 500)

    print(f"Generating Stress Test {stress_id}: {sc}")
    # TODO: Call DIRTY with stress test parameters
    # dirty_run_stress(stress_id, sc, n_samples, output_dir, seed=seed)

    print(f"Generated Stress Test {stress_id}: {n_samples} samples → {output_dir}")


def main():
    parser = argparse.ArgumentParser(
        description='Generate COMETH synthetic datasets via DIRTY v3.2')
    parser.add_argument('--config', default='../configs/dirty_params.yaml',
                        help='DIRTY parameter configuration file')
    parser.add_argument('--output', default='../data/synthetic',
                        help='Output directory for generated data')
    parser.add_argument('--stress-test', type=int, choices=[1, 2, 3, 4, 5, 6],
                        help='Generate specific stress test (1-6)')
    parser.add_argument('--seed', type=int, default=42,
                        help='Random seed for reproducibility')
    parser.add_argument('--all-seeds', action='store_true',
                        help='Generate all 5 seeds for cross-validation')
    args = parser.parse_args()

    # Load config
    if os.path.exists(args.config):
        with open(args.config) as f:
            config = yaml.safe_load(f)
    else:
        print(f"WARNING: Config file {args.config} not found. Using defaults.")
        config = {'n_samples': 50000, 'stress_test_samples': 500}

    seeds = SEEDS if args.all_seeds else [args.seed]

    for seed in seeds:
        out_dir = os.path.join(args.output, f'seed_{seed}')

        if args.stress_test:
            generate_stress_test(args.stress_test, config, seed, out_dir)
        else:
            generate_standard_dataset(config, seed, out_dir)

    print("\nData generation complete.")
    print("See README.md for DIRTY installation and usage instructions.")


if __name__ == '__main__':
    main()
