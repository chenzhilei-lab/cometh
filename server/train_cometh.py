"""
COMETH Training Script (Single-Seed, 3090 24GB)
===============================================
Reproduces: Detection CNN + PINN inversion weights for same-data comparison.

Usage:
  python train_cometh.py                          # full training
  python train_cometh.py --cnn-only               # CNN only (~60h)
  python train_cometh.py --pinn-only              # PINN only (~140h)
  python train_cometh.py --resume cnn             # resume interrupted CNN

Outputs:
  weights/cnn_detector.pt       (~180 MB)
  weights/pinn_inversion.pt     (~450 MB)
  weights/ood_detector.pkl      (~5 MB)

Estimated time on RTX 3090 (24GB):
  Data generation: 4-6 hours (CPU/IO-bound, depends on DIRTY)
  CNN training:    ~55-65 hours
  PINN training:   ~130-150 hours
  OOD fitting:     <5 minutes
  -------------------------------------------------
  Total:           ~190-215 hours (~8-9 days)

Hardware check on startup:
  - VRAM >= 20 GB (uses ~18-22 GB at peak)
  - CUDA 12.1+ recommended
"""

import os, sys, argparse, time, json, yaml
from pathlib import Path
from datetime import datetime

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.utils.data import DataLoader, TensorDataset
from torch.cuda.amp import GradScaler, autocast

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from cnn_detection import DetectionCNN
from pinn_inversion import PINNInversion
from ood_detector import OODDetector

# ============================================================
# Configuration
# ============================================================

SEED = 42
DEVICE = torch.device('cuda' if torch.cuda.is_available() else 'cpu')

# Hyperparameters from configs/hyperparams.yaml
CNN_HP = {
    'lr': 2.1e-4, 'batch_size': 32, 'se_reduction': 16,
    'lambda_ssim': 0.5, 'lambda_edge': 0.3, 'lambda_flux': 0.1,
    'gamma_attn': 0.2, 'lambda_neg': 0.5,
    'max_epochs': 300, 'patience': 50,
}

PINN_HP = {
    'lr': 5.6e-5, 'batch_size': 8, 'dropout': 0.12,
    'gamma_pde': 1.0, 'gamma_bc': 0.5, 'gamma_cons': 0.3,
    'max_epochs': 300, 'patience': 50,
    'mc_samples': 50,
}

# ============================================================
# Utility
# ============================================================

def log(msg):
    stamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f"[{stamp}] {msg}", flush=True)

def check_hardware():
    if not torch.cuda.is_available():
        raise RuntimeError("CUDA not available. Training requires GPU.")
    vram_gb = torch.cuda.get_device_properties(0).total_memory / 1e9
    if vram_gb < 20:
        log(f"WARNING: VRAM = {vram_gb:.1f} GB. Training may OOM. Recommended >= 20 GB.")
    log(f"GPU: {torch.cuda.get_device_name(0)} | VRAM: {vram_gb:.1f} GB")
    log(f"PyTorch: {torch.__version__} | CUDA: {torch.version.cuda}")

# ============================================================
# Data loading (pre-generated synthetic data)
# ============================================================

def load_synthetic_data(data_dir, n_samples=None):
    """
    Load pre-generated synthetic data from .pt files.
    If data_dir doesn't exist, prints instructions to run generate_synthetic_data.py first.
    """
    data_path = Path(data_dir)
    if not data_path.exists():
        log(f"ERROR: {data_dir} not found.")
        log("Run first: python data_generation/generate_synthetic_data.py --config configs/dirty_params.yaml")
        sys.exit(1)

    img_files = sorted(data_path.glob('*_img.pt'))
    spec_files = sorted(data_path.glob('*_spec.pt'))
    param_files = sorted(data_path.glob('*_params.pt'))

    if len(img_files) == 0:
        log(f"ERROR: No .pt files found in {data_dir}")
        sys.exit(1)

    log(f"Loading {len(img_files)} samples from {data_dir}...")
    images, spectra, params = [], [], []
    for i, (ifile, sfile, pfile) in enumerate(zip(img_files, spec_files, param_files)):
        images.append(torch.load(ifile))
        spectra.append(torch.load(sfile))
        params.append(torch.load(pfile))
        if n_samples and i + 1 >= n_samples:
            break

    images = torch.stack(images)       # (N, C, H, W)
    spectra = torch.stack(spectra)     # (N, L)
    params = torch.stack(params)       # (N, 5): Qd, alpha, a_max, CO/H2O, C2/CN
    log(f"Loaded: images {list(images.shape)}, spectra {list(spectra.shape)}, params {list(params.shape)}")
    return images, spectra, params


def create_dataloaders(images, spectra, params, batch_size, train_frac=0.8):
    """60/20/20 split matching paper §3.6."""
    n = len(images)
    n_train = int(n * 0.6)
    n_val = int(n * 0.2)
    # n_test = n - n_train - n_val  (held out)

    indices = torch.randperm(n, generator=torch.Generator().manual_seed(SEED))
    train_idx = indices[:n_train]
    val_idx = indices[n_train:n_train + n_val]
    test_idx = indices[n_train + n_val:]

    train_ds = TensorDataset(images[train_idx], spectra[train_idx], params[train_idx])
    val_ds = TensorDataset(images[val_idx], spectra[val_idx], params[val_idx])

    train_dl = DataLoader(train_ds, batch_size=batch_size, shuffle=True,
                          num_workers=4, pin_memory=True, drop_last=True)
    val_dl = DataLoader(val_ds, batch_size=batch_size, shuffle=False,
                        num_workers=2, pin_memory=True)
    test_ds = TensorDataset(images[test_idx], spectra[test_idx], params[test_idx])

    log(f"Split: train={len(train_ds)}, val={len(val_ds)}, test={len(test_ds)}")
    return train_dl, val_dl, test_ds


# ============================================================
# Loss functions
# ============================================================

def ssim_loss(pred, target, window_size=11):
    """Simplified SSIM loss (1 - SSIM)."""
    from torch.nn.functional import conv2d
    C = pred.shape[1]
    # Gaussian window
    sigma = 1.5
    gauss = torch.exp(-((torch.arange(window_size, device=pred.device).float() - window_size//2)**2) / (2*sigma**2))
    gauss = (gauss / gauss.sum()).view(1, -1) * (gauss / gauss.sum()).view(-1, 1)
    window = gauss.expand(C, 1, window_size, window_size).contiguous()

    mu1 = conv2d(pred, window, padding=window_size//2, groups=C)
    mu2 = conv2d(target, window, padding=window_size//2, groups=C)
    mu1_sq, mu2_sq = mu1**2, mu2**2
    sigma1 = conv2d(pred*pred, window, padding=window_size//2, groups=C) - mu1_sq
    sigma2 = conv2d(target*target, window, padding=window_size//2, groups=C) - mu2_sq
    sigma12 = conv2d(pred*target, window, padding=window_size//2, groups=C) - mu1*mu2

    C1, C2 = 0.01**2, 0.03**2
    ssim_map = ((2*mu1*mu2 + C1) * (2*sigma12 + C2)) / \
               ((mu1_sq + mu2_sq + C1) * (sigma1 + sigma2 + C2) + 1e-8)
    return 1.0 - ssim_map.mean()


def edge_loss(pred, target):
    """Sobel edge-preserving loss."""
    sobel_x = torch.tensor([[-1,0,1],[-2,0,2],[-1,0,1]], dtype=torch.float32,
                           device=pred.device).view(1,1,3,3)
    sobel_y = torch.tensor([[-1,-2,-1],[0,0,0],[1,2,1]], dtype=torch.float32,
                           device=pred.device).view(1,1,3,3)
    # Apply per channel
    loss = 0.0
    for c in range(pred.shape[1]):
        gx_p = F.conv2d(pred[:,c:c+1], sobel_x, padding=1)
        gy_p = F.conv2d(pred[:,c:c+1], sobel_y, padding=1)
        gx_t = F.conv2d(target[:,c:c+1], sobel_x, padding=1)
        gy_t = F.conv2d(target[:,c:c+1], sobel_y, padding=1)
        loss += F.l1_loss(gx_p, gx_t) + F.l1_loss(gy_p, gy_t)
    return loss / pred.shape[1]


def flux_conservation_loss(pred, target):
    """Total flux should be conserved."""
    return F.l1_loss(pred.sum(dim=(2,3)), target.sum(dim=(2,3)))


# ============================================================
# CNN Training
# ============================================================

def train_cnn(data_dir, output_dir, n_samples=None):
    log("=" * 60)
    log("TRAINING: Detection CNN")
    log("=" * 60)

    images, spectra, params = load_synthetic_data(data_dir, n_samples)
    train_dl, val_dl, _ = create_dataloaders(images, spectra, params, CNN_HP['batch_size'])

    model = DetectionCNN(in_channels=1, out_channels=1, se_reduction=CNN_HP['se_reduction']).to(DEVICE)
    optimizer = torch.optim.Adam(model.parameters(), lr=CNN_HP['lr'],
                                  betas=(0.9, 0.999))
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=CNN_HP['max_epochs'])
    scaler = GradScaler()

    best_val_loss = float('inf')
    patience_counter = 0
    cnn_weights = Path(output_dir)

    for epoch in range(1, CNN_HP['max_epochs'] + 1):
        model.train()
        train_loss = 0.0
        t0 = time.time()

        for batch_img, _, _ in train_dl:
            batch_img = batch_img.to(DEVICE)
            optimizer.zero_grad()

            with autocast():
                noise = torch.randn_like(batch_img) * 0.05
                noisy = batch_img + noise
                denoised = model(noisy)
                l_mse = F.mse_loss(denoised, batch_img)
                l_ssim = CNN_HP['lambda_ssim'] * ssim_loss(denoised, batch_img)
                l_edge = CNN_HP['lambda_edge'] * edge_loss(denoised, batch_img)
                l_flux = CNN_HP['lambda_flux'] * flux_conservation_loss(denoised, batch_img)
                loss = l_mse + l_ssim + l_edge + l_flux

            scaler.scale(loss).backward()
            scaler.step(optimizer)
            scaler.update()
            train_loss += loss.item()

        train_loss /= len(train_dl)
        scheduler.step()

        # Validation
        model.eval()
        val_loss = 0.0
        with torch.no_grad():
            for batch_img, _, _ in val_dl:
                batch_img = batch_img.to(DEVICE)
                noise = torch.randn_like(batch_img) * 0.05
                denoised = model(batch_img + noise)
                val_loss += F.mse_loss(denoised, batch_img).item()
        val_loss /= len(val_dl)

        elapsed = time.time() - t0
        if epoch % 10 == 0 or epoch == 1:
            log(f"CNN Epoch {epoch:3d}/{CNN_HP['max_epochs']} | "
                f"train={train_loss:.4f} val={val_loss:.4f} | {elapsed:.0f}s")

        # Early stopping
        if val_loss < best_val_loss * 0.999:
            best_val_loss = val_loss
            patience_counter = 0
            torch.save(model.state_dict(), cnn_weights / 'cnn_detector.pt')
        else:
            patience_counter += 1
            if patience_counter >= CNN_HP['patience']:
                log(f"Early stopping at epoch {epoch}")
                break

    log(f"CNN training complete. Best val loss: {best_val_loss:.4f}")
    log(f"Weights saved to {cnn_weights / 'cnn_detector.pt'}")


# ============================================================
# PINN Training
# ============================================================

def train_pinn(data_dir, output_dir, n_samples=None):
    log("=" * 60)
    log("TRAINING: PINN Inversion")
    log("=" * 60)

    images, spectra, params = load_synthetic_data(data_dir, n_samples)
    train_dl, val_dl, _ = create_dataloaders(images, spectra, params, PINN_HP['batch_size'])

    model = PINNInversion(
        img_channels=1,
        spec_dim=spectra.shape[1],
        hidden_dim=256,
        num_blocks=6,
        dropout=PINN_HP['dropout'],
    ).to(DEVICE)

    optimizer = torch.optim.Adam(model.parameters(), lr=PINN_HP['lr'],
                                  betas=(0.9, 0.999))
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=PINN_HP['max_epochs'])
    scaler = GradScaler()

    best_val_loss = float('inf')
    patience_counter = 0
    pinn_weights = Path(output_dir)

    for epoch in range(1, PINN_HP['max_epochs'] + 1):
        model.train()
        train_loss = 0.0
        t0 = time.time()

        for batch_img, batch_spec, batch_params in train_dl:
            batch_img = batch_img.to(DEVICE)
            batch_spec = batch_spec.to(DEVICE)
            batch_params = batch_params.to(DEVICE)

            optimizer.zero_grad()

            with autocast():
                # Forward: CNN encoder → physics network → parameter prediction
                pred_params, latent = model(batch_img, batch_spec)

                # Data fidelity
                l_data = F.mse_loss(pred_params, batch_params)

                # Hard constraints are embedded in model architecture (no separate loss term)
                # Soft PDE/BC constraints are computed inside the PINN forward pass
                l_pde = model.compute_pde_residual(pred_params, batch_img)  # radiative transfer residual
                l_bc = model.compute_bc_residual(pred_params)               # boundary condition

                loss = l_data + PINN_HP['gamma_pde'] * l_pde + PINN_HP['gamma_bc'] * l_bc

            scaler.scale(loss).backward()
            scaler.step(optimizer)
            scaler.update()
            train_loss += loss.item()

        train_loss /= len(train_dl)
        scheduler.step()

        # Validation
        model.eval()
        val_loss = 0.0
        with torch.no_grad():
            for batch_img, batch_spec, batch_params in val_dl:
                batch_img, batch_spec = batch_img.to(DEVICE), batch_spec.to(DEVICE)
                batch_params = batch_params.to(DEVICE)
                pred_params, _ = model(batch_img, batch_spec)
                val_loss += F.mse_loss(pred_params, batch_params).item()
        val_loss /= len(val_dl)

        elapsed = time.time() - t0
        if epoch % 10 == 0 or epoch == 1:
            log(f"PINN Epoch {epoch:3d}/{PINN_HP['max_epochs']} | "
                f"train={train_loss:.4f} val={val_loss:.4f} | {elapsed:.0f}s")

        if val_loss < best_val_loss * 0.999:
            best_val_loss = val_loss
            patience_counter = 0
            torch.save(model.state_dict(), pinn_weights / 'pinn_inversion.pt')
        else:
            patience_counter += 1
            if patience_counter >= PINN_HP['patience']:
                log(f"Early stopping at epoch {epoch}")
                break

    log(f"PINN training complete. Best val loss: {best_val_loss:.4f}")


# ============================================================
# OOD Detector Fitting
# ============================================================

def fit_ood(data_dir, weights_dir, output_dir, n_samples=None):
    log("=" * 60)
    log("FITTING: OOD Detector (GMM)")
    log("=" * 60)

    images, spectra, _ = load_synthetic_data(data_dir, n_samples)

    # Load trained PINN for latent extraction
    pinn = PINNInversion(img_channels=images.shape[1], spec_dim=spectra.shape[1]).to(DEVICE)
    pinn.load_state_dict(torch.load(Path(weights_dir) / 'pinn_inversion.pt', map_location=DEVICE))
    pinn.eval()

    # Extract latent codes
    log("Extracting latent codes...")
    latent_codes = []
    bs = 32
    with torch.no_grad():
        for i in range(0, len(images), bs):
            batch_img = images[i:i+bs].to(DEVICE)
            batch_spec = spectra[i:i+bs].to(DEVICE)
            _, latent = pinn(batch_img, batch_spec)
            latent_codes.append(latent.cpu().numpy())

    latent_codes = np.concatenate(latent_codes, axis=0)
    log(f"Latent codes shape: {latent_codes.shape}")

    # Fit GMM
    ood = OODDetector(n_components=10, latent_dim=latent_codes.shape[1])
    ood.fit(latent_codes)

    ood_path = Path(output_dir) / 'ood_detector.pkl'
    ood.save(ood_path)
    log(f"OOD detector saved to {ood_path}")


# ============================================================
# Main
# ============================================================

def main():
    parser = argparse.ArgumentParser(description='COMETH Training (Single-Seed, 3090)')
    parser.add_argument('--data-dir', default='data/train',
                        help='Directory with pre-generated synthetic .pt files')
    parser.add_argument('--weights-dir', default='weights',
                        help='Output directory for trained weights')
    parser.add_argument('--cnn-only', action='store_true',
                        help='Train only the Detection CNN')
    parser.add_argument('--pinn-only', action='store_true',
                        help='Train only the PINN inversion')
    parser.add_argument('--ood-only', action='store_true',
                        help='Fit only the OOD detector (requires PINN weights)')
    parser.add_argument('--n-samples', type=int, default=None,
                        help='Limit training samples (for testing)')
    parser.add_argument('--resume', choices=['cnn', 'pinn'], default=None,
                        help='Resume from checkpoint')
    args = parser.parse_args()

    check_hardware()
    os.makedirs(args.weights_dir, exist_ok=True)

    # Set random seeds
    torch.manual_seed(SEED)
    np.random.seed(SEED)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(SEED)

    start_time = time.time()

    if args.ood_only:
        fit_ood(args.data_dir, args.weights_dir, args.weights_dir)
    elif args.cnn_only:
        train_cnn(args.data_dir, args.weights_dir, args.n_samples)
    elif args.pinn_only:
        train_pinn(args.data_dir, args.weights_dir, args.n_samples)
    else:
        # Full training pipeline
        train_cnn(args.data_dir, args.weights_dir, args.n_samples)
        train_pinn(args.data_dir, args.weights_dir, args.n_samples)
        fit_ood(args.data_dir, args.weights_dir, args.weights_dir)

    elapsed = (time.time() - start_time) / 3600
    log(f"Total wall time: {elapsed:.1f} hours")
    log("Training complete. Weights in: " + str(Path(args.weights_dir).absolute()))


if __name__ == '__main__':
    main()
