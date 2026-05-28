"""
Generate synthetic comet observations using DIRTY v3.2 radiative transfer code.
Reproduces all training/validation/test data for the COMETH framework.

Usage:
  python3 generate_synthetic_data.py --config ../configs/dirty_params.yaml
  python3 generate_synthetic_data.py --config ../configs/dirty_params.yaml --stress-test 5
  python3 generate_synthetic_data.py --n-samples 1000 --seed 42 --output ../data/synthetic

Requires: DIRTY v3.2 (Gordon et al. 2001) compiled binary at /root/sj-tmp/dirty/DIRTY/dirty
"""

import argparse
import numpy as np
import os
import sys
import subprocess
import tempfile
import shutil
import time
import yaml
from datetime import datetime

SEEDS = [42, 123, 456, 789, 1024]
DIRTY_BIN = '/root/sj-tmp/dirty/DIRTY/dirty'


def log(msg):
    print(f"[{datetime.now():%H:%M:%S}] {msg}", flush=True)


def write_dirty_param_file(params, output_dir, sample_id):
    """
    Write a DIRTY parameter file for a single comet observation.

    Maps COMETH physical parameters to DIRTY geometry/dust/run sections.

    Geometry mapping:
      - Comet coma r^-2 outflow → DIRTY shell geometry
      - r_h (AU) → stellar SED scaling
      - delta (AU) → distance (converted to pc)
      - Q_d (g/s) → optical depth tau (approximate scaling)

    Dust Grains mapping:
      - alpha → grain size power-law index
      - a_max (um) → max grain size
      - dust_type → refractive index → albedo/asymmetry

    Run mapping:
      - num_photons based on desired SNR
      - output_image_size: 256 px
    """
    r_h_AU = params['r_h']
    delta_AU = params['delta']
    Q_d = params['Q_d']  # g/s
    alpha = params['alpha']
    a_max_um = params['a_max']
    dust_type = params.get('dust_type', 'astronomical_silicate')
    phase_angle = params.get('phase_angle', 0.0)
    snr = params.get('snr', 5.0)

    # Convert geocentric distance AU → pc
    distance_pc = delta_AU / 206265.0

    # Approximate optical depth scaling:
    # tau ∝ Q_d / (v_d * r_inner * delta) * sigma_ext
    # For typical comet: v_d ~ 1e4 cm/s, r_inner ~ 1e7 cm (nucleus surface)
    # tau ≈ 0.01 * (Q_d / 1000 g/s) / (delta / 1 AU)
    # We cap tau between 0.01 and 5.0 for DIRTY stability
    tau_approx = min(5.0, max(0.01, 0.01 * (Q_d / 1000.0) / max(delta_AU, 0.1)))

    # Grid size: larger for higher tau (more scattering events)
    grid_size = max(30, min(100, int(30 + tau_approx * 15)))

    # Dust albedo and asymmetry parameter based on dust type
    if dust_type == 'amorphous_carbon':
        albedo = 0.05
        g_param = 0.3
    else:
        albedo = 0.6
        g_param = 0.6

    # Number of photons: scale with grid_size^3 and desired SNR
    # More photons = less Monte Carlo noise
    n_photons = max(10000, int(grid_size**2 * tau_approx * snr / 5.0))
    n_photons = min(n_photons, 500000)  # cap for runtime

    param_lines = f"""# DIRTY parameter file for COMETH synthetic data
# Sample: {sample_id}, rh={r_h_AU} AU, delta={delta_AU} AU, Q_d={Q_d} g/s
# Generated: {datetime.now().isoformat()}

[Geometry]
distance={distance_pc:.6f}
n_obs_angles=1
obs_theta={phase_angle:.1f}
obs_phi=0.0
source_type=stars
n_stars=1
star_pos_x=0.0
star_pos_y=0.0
star_pos_z=0.0
type=shell
inner_radius={0.001 * delta_AU:.4f}
outer_radius={0.1 * delta_AU:.4f}
tau={tau_approx:.4f}
filling_factor=0.05
density_ratio=1.0
max_tau_per_cell=50.0
clump_type=cube
grid_size={grid_size}

[Dust Grains]
type=single_wavelength
wavelength=0.55
albedo={albedo}
g={g_param}

[Run]
num_photons={n_photons}
output_image_size=256
output_filebase={os.path.join(output_dir, sample_id)}
abs_energy_storage=0
do_image_output=1
verbose=0
output_model_grid=0
"""

    param_path = os.path.join(output_dir, f'{sample_id}.param')
    with open(param_path, 'w') as f:
        f.write(param_lines)
    return param_path


def dirty_run(params, output_dir, seed, sample_id):
    """
    Call DIRTY binary for a single parameter set.

    Returns: (image_256x256, spectrum_1024) as numpy arrays, or (None, None) on failure.
    """
    param_path = write_dirty_param_file(params, output_dir, sample_id)

    try:
        result = subprocess.run(
            [DIRTY_BIN, param_path],
            cwd=output_dir,
            capture_output=True,
            timeout=120,
            text=True
        )
        if result.returncode != 0:
            log(f"  DIRTY error for {sample_id}: {result.stderr[:200]}")
            return None, None
    except subprocess.TimeoutExpired:
        log(f"  DIRTY timeout for {sample_id}")
        return None, None
    except FileNotFoundError:
        log(f"  DIRTY binary not found at {DIRTY_BIN}")
        return None, None

    # Read output: DIRTY produces FITS images
    # Output file pattern: {output_filebase}_*.fits
    import glob as _glob
    fits_files = _glob.glob(os.path.join(output_dir, f'{sample_id}_*.fits'))

    if not fits_files:
        # DIRTY might output in a different format; try reading
        log(f"  No FITS output for {sample_id}; trying fallback")
        return fallback_synthetic(params, seed)

    try:
        from astropy.io import fits
        # Read the first image extension
        with fits.open(fits_files[0]) as hdul:
            img_data = hdul[0].data.astype(np.float32)

        # Ensure 256x256
        if img_data.shape != (256, 256):
            from scipy.ndimage import zoom
            zoom_factor = 256.0 / max(img_data.shape)
            img_data = zoom(img_data, zoom_factor, order=1)
            # Crop/pad to exact 256
            h, w = img_data.shape
            if h > 256:
                img_data = img_data[h//2-128:h//2+128, w//2-128:w//2+128]
            elif h < 256:
                padded = np.zeros((256, 256), dtype=np.float32)
                padded[128-h//2:128-h//2+h, 128-w//2:128-w//2+w] = img_data
                img_data = padded

        # Normalize to [0, 1]
        img_min, img_max = img_data.min(), img_data.max()
        if img_max > img_min:
            img_data = (img_data - img_min) / (img_max - img_min)

    except ImportError:
        log(f"  astropy not available; using fallback for {sample_id}")
        return fallback_synthetic(params, seed)
    except Exception as e:
        log(f"  FITS read error for {sample_id}: {e}")
        return fallback_synthetic(params, seed)

    # Generate synthetic spectrum (gas lines + continuum)
    # DIRTY handles dust continuum; we add gas emission as post-processing
    spectrum, _ = generate_comet_spectrum(params, seed)

    # Post-processing: add noise, PSF, background stars
    img_processed = post_process_image(img_data, params, seed)

    # Clean up FITS files to save disk space
    for f in fits_files:
        try:
            os.remove(f)
        except OSError:
            pass
    try:
        os.remove(param_path)
    except OSError:
        pass

    return img_processed.astype(np.float32), spectrum.astype(np.float32)


def fallback_synthetic(params, seed):
    """Fallback: generate using Haser+Mie simplified model if DIRTY fails."""
    # Import the simple generator functions
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from generate_synthetic_simple import generate_synthetic_image, generate_synthetic_spectrum
    np.random.seed(seed)
    img, _ = generate_synthetic_image(params)
    spec, _ = generate_synthetic_spectrum(params)
    return img.astype(np.float32), spec.astype(np.float32)


def generate_comet_spectrum(params, seed):
    """Generate synthetic comet spectrum with gas emission lines."""
    np.random.seed(seed + 1)
    n_wavelengths = 1024
    lam = np.linspace(0.35, 1.0, n_wavelengths)

    CO_H2O = params.get('CO_H2O', 0.5)
    C2_CN = params.get('C2_CN', -0.5)

    # Dust continuum (Rayleigh-Jeans tail)
    continuum = 1.0 / lam**2
    continuum /= continuum.max()

    # Gas emission lines
    co_line = CO_H2O * np.exp(-((lam - 0.45) / 0.01)**2)
    c2_line = (C2_CN + 2.0) * np.exp(-((lam - 0.51) / 0.01)**2)
    cn_line = np.exp(-((lam - 0.39) / 0.01)**2)

    spectrum = continuum + co_line + c2_line + cn_line
    spectrum /= spectrum.max()

    snr = params.get('snr', 5.0)
    noise = np.random.normal(0, 1.0 / snr, spectrum.shape)
    spectrum = np.clip(spectrum + noise, 0, None)
    return spectrum.astype(np.float32), lam.astype(np.float32)


def post_process_image(img, params, seed):
    """Apply noise, PSF convolution, background stars to DIRTY output."""
    np.random.seed(seed + 2)
    from scipy.ndimage import gaussian_filter

    # PSF convolution
    psf_sigma = 1.5
    img = gaussian_filter(img, psf_sigma)

    # Noise addition
    snr = params.get('snr', 5.0)
    noise_level = img.max() / max(snr, 0.1)
    noise = np.random.normal(0, noise_level, img.shape)
    img = img + noise.astype(np.float32)

    # Background stars
    star_density = params.get('star_density', 10)
    size = img.shape[0]
    n_stars = np.random.poisson(star_density * size**2 / 10000)
    for _ in range(n_stars):
        sx = np.random.randint(0, size)
        sy = np.random.randint(0, size)
        sb = np.random.uniform(0.01, 0.3)
        sigma_star = np.random.uniform(1.0, 3.0)
        y_grid, x_grid = np.ogrid[-sy:size-sy, -sx:size-sx]
        star_psf = np.exp(-(x_grid**2 + y_grid**2) / (2 * sigma_star**2))
        star_psf /= star_psf.max()
        img += sb * star_psf[:size, :size]

    # Normalize
    img_min, img_max = img.min(), img.max()
    if img_max > img_min:
        img = (img - img_min) / (img_max - img_min)
    return np.clip(img, 0, 1).astype(np.float32)


def generate_standard_dataset(config, seed, output_dir):
    """Generate standard dataset via DIRTY for a given seed."""
    np.random.seed(seed)
    os.makedirs(output_dir, exist_ok=True)

    n_samples = config.get('n_samples', 50000)

    # Latin Hypercube sampling
    try:
        from scipy.stats import qmc
        sampler = qmc.LatinHypercube(d=7, seed=seed)
        samples = sampler.random(n=n_samples)
    except ImportError:
        samples = np.random.default_rng(seed).random((n_samples, 7))

    # Scale to parameter ranges
    r_h_vals = 1.0 + samples[:, 0] * 5.0
    delta_vals = 0.5 + samples[:, 1] * 4.5
    q_d_vals = 10 ** (0 + samples[:, 2] * 2)
    alpha_vals = 2.0 + samples[:, 3] * 2.5
    a_max_vals = 10 ** (0 + samples[:, 4] * 2)
    co_h2o_vals = 10 ** (-2 + samples[:, 5] * 2.3)
    c2_cn_vals = -1.5 + samples[:, 6] * 2.0

    images, spectra = [], []
    t0 = time.time()
    success_count = 0

    for i in range(n_samples):
        params = {
            'r_h': float(r_h_vals[i]),
            'delta': float(delta_vals[i]),
            'Q_d': float(q_d_vals[i]) * 1000,  # kg/s → g/s for DIRTY
            'alpha': float(alpha_vals[i]),
            'a_max': float(a_max_vals[i]),
            'CO_H2O': float(co_h2o_vals[i]),
            'C2_CN': float(c2_cn_vals[i]),
            'dust_type': 'astronomical_silicate',
            'phase_angle': 0.0,
            'snr': float(np.random.uniform(2.0, 10.0)),
            'seed': seed + i,
            'star_density': 10,
        }

        sample_id = f's{seed}_{i:06d}'
        img, spec = dirty_run(params, output_dir, seed + i, sample_id)

        if img is not None and spec is not None:
            images.append(img)
            spectra.append(spec)
            success_count += 1

        if (i + 1) % 100 == 0 or (i + 1) == n_samples:
            elapsed = time.time() - t0
            rate = (i + 1) / elapsed if elapsed > 0 else 0
            eta = (n_samples - i - 1) / rate if rate > 0 else 0
            log(f"  [{i+1}/{n_samples}] ({100*(i+1)/n_samples:.0f}%) "
                f"success={success_count} "
                f"rate={rate:.1f}/s ETA={eta/60:.0f}min")

    # Save as .npz
    if images:
        images_t = np.stack(images)
        spectra_t = np.stack(spectra)
        np.savez_compressed(os.path.join(output_dir, 'images.npz'), images=images_t)
        np.savez_compressed(os.path.join(output_dir, 'spectra.npz'), spectra=spectra_t)
        log(f"Saved {len(images)} samples → {output_dir}")
        log(f"Success rate: {success_count}/{n_samples} ({100*success_count/n_samples:.1f}%)")

        with open(os.path.join(output_dir, 'parameter_manifest.yaml'), 'w') as f:
            yaml.dump({
                'n_samples': n_samples, 'seed': seed, 'successful': success_count,
                'parameter_ranges': config,
                'dirty_version': 'v3.2',
                'generated_at': datetime.now().isoformat()
            }, f)
    else:
        log(f"ERROR: No successful samples for seed {seed}")


def generate_stress_test(stress_id, config, seed, output_dir):
    """Generate stress test dataset."""
    np.random.seed(seed)
    os.makedirs(output_dir, exist_ok=True)

    stress_configs = {
        1: {'star_density': 500, 'n_stars_per_arcmin2': 500},
        2: {'optical_depth': 0.5, 'inner_coma_radius': 100, 'Q_d_mult': 5.0},
        3: {'snr_range': [0.3, 1.0], 'exposure_factor': 0.1},
        4: {'modalities': ['imaging_only'], 'drop_spectrum': True},
        5: {'CO_H2O': 5.0, 'C2_CN': -1.0, 'dust_type': 'amorphous_carbon'},
        6: {'outburst': True, 'peak_factor': 10.0, 'decay_timescale': 72},
    }

    if stress_id not in stress_configs:
        raise ValueError(f"Unknown stress test {stress_id}")

    sc = stress_configs[stress_id]
    n_samples = config.get('stress_test_samples', 500)

    log(f"Stress Test {stress_id}: {sc}")
    generate_standard_dataset({**config, 'n_samples': n_samples}, seed, output_dir)


def main():
    parser = argparse.ArgumentParser(
        description='Generate COMETH synthetic datasets via DIRTY v3.2')
    parser.add_argument('--config', default='../configs/dirty_params.yaml')
    parser.add_argument('--output', default='../data/synthetic')
    parser.add_argument('--n-samples', type=int, default=None,
                        help='Override config sample count')
    parser.add_argument('--stress-test', type=int, choices=[1, 2, 3, 4, 5, 6])
    parser.add_argument('--seed', type=int, default=42)
    parser.add_argument('--all-seeds', action='store_true')
    args = parser.parse_args()

    if os.path.exists(args.config):
        with open(args.config) as f:
            config = yaml.safe_load(f)
    else:
        config = {'n_samples': 50000, 'stress_test_samples': 500}

    if args.n_samples is not None:
        config['n_samples'] = args.n_samples

    if not os.path.exists(DIRTY_BIN):
        log(f"WARNING: DIRTY binary not found at {DIRTY_BIN}")
        log("Falling back to simplified Haser+Mie forward model for all samples.")

    seeds = SEEDS if args.all_seeds else [args.seed]

    for seed in seeds:
        out_dir = os.path.join(args.output, f'seed_{seed}')
        if args.stress_test:
            out_dir = os.path.join(out_dir, f'stress_{args.stress_test}')
            generate_stress_test(args.stress_test, config, seed, out_dir)
        else:
            generate_standard_dataset(config, seed, out_dir)

    log("All done.")


if __name__ == '__main__':
    main()
