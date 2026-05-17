"""
Multi-scale CNN with SE Attention for Faint Comet Feature Detection.
Implements §3.1 of the paper.

Architecture: U-Net encoder-decoder with parallel 3x3/5x5/7x7 kernels,
squeeze-and-excitation channel attention, and Grad-CAM support.
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
from typing import Tuple, Optional


class SEBlock(nn.Module):
    """Squeeze-and-Excitation channel attention (Hu et al. 2018, Eq. 5-7)."""
    def __init__(self, channels: int, reduction: int = 16):
        super().__init__()
        self.squeeze = nn.AdaptiveAvgPool2d(1)
        self.excitation = nn.Sequential(
            nn.Linear(channels, channels // reduction),
            nn.ReLU(inplace=True),
            nn.Linear(channels // reduction, channels),
            nn.Sigmoid()
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        b, c, _, _ = x.size()
        z = self.squeeze(x).view(b, c)          # Eq. 5
        s = self.excitation(z).view(b, c, 1, 1) # Eq. 6
        return x * s                              # Eq. 7


class MultiScaleConv(nn.Module):
    """Parallel 3x3, 5x5, 7x7 branches with channel concatenation (Eq. 4)."""
    def __init__(self, in_ch: int, out_ch: int):
        super().__init__()
        out_per_branch = out_ch // 3
        self.conv3 = nn.Conv2d(in_ch, out_per_branch, 3, padding=1)
        self.conv5 = nn.Conv2d(in_ch, out_per_branch, 5, padding=2)
        self.conv7 = nn.Conv2d(in_ch, out_per_branch, 7, padding=3)
        # Handle remainder channels if not divisible by 3
        rem = out_ch - 3 * out_per_branch
        self.conv_rem = nn.Conv2d(in_ch, rem, 1) if rem > 0 else None

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        h3 = self.conv3(x)
        h5 = self.conv5(x)
        h7 = self.conv7(x)
        out = torch.cat([h3, h5, h7], dim=1)
        if self.conv_rem is not None:
            out = torch.cat([out, self.conv_rem(x)], dim=1)
        return out


class ConvBlock(nn.Module):
    """Encoder/decoder convolutional block with BN+ReLU (Eq. 3)."""
    def __init__(self, in_ch: int, out_ch: int, use_se: bool = True):
        super().__init__()
        self.multi_conv = MultiScaleConv(in_ch, out_ch)
        self.bn = nn.BatchNorm2d(out_ch)
        self.se = SEBlock(out_ch) if use_se else nn.Identity()

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = self.multi_conv(x)
        x = self.bn(x)
        x = F.relu(x, inplace=True)
        x = self.se(x)
        return x


class DetectionCNN(nn.Module):
    """
    U-Net-style multi-scale CNN for faint feature detection.
    5-scale encoder-decoder with skip connections, SE attention,
    and multi-scale parallel kernels.

    Input:  (B, N_bands, H, W)  — multi-band comet image
    Output: (B, N_bands, H, W)  — denoised / feature-enhanced image
    """
    def __init__(self, in_channels: int = 1, base_channels: int = 64):
        super().__init__()
        # Encoder (5 scales)
        self.enc1 = ConvBlock(in_channels, base_channels)
        self.enc2 = ConvBlock(base_channels, base_channels * 2)
        self.enc3 = ConvBlock(base_channels * 2, base_channels * 4)
        self.enc4 = ConvBlock(base_channels * 4, base_channels * 8)
        self.enc5 = ConvBlock(base_channels * 8, base_channels * 16)

        self.pool = nn.MaxPool2d(2)

        # Bottleneck
        self.bottleneck = ConvBlock(base_channels * 16, base_channels * 16)

        # Decoder (5 scales, with skip connections)
        # Input channels = upsampled channels + skip connection channels
        self.up5 = nn.ConvTranspose2d(base_channels * 16, base_channels * 8, 2, stride=2)
        self.dec5 = ConvBlock(base_channels * 24, base_channels * 8)

        self.up4 = nn.ConvTranspose2d(base_channels * 8, base_channels * 4, 2, stride=2)
        self.dec4 = ConvBlock(base_channels * 12, base_channels * 4)

        self.up3 = nn.ConvTranspose2d(base_channels * 4, base_channels * 2, 2, stride=2)
        self.dec3 = ConvBlock(base_channels * 6, base_channels * 2)

        self.up2 = nn.ConvTranspose2d(base_channels * 2, base_channels, 2, stride=2)
        self.dec2 = ConvBlock(base_channels * 3, base_channels)

        self.up1 = nn.ConvTranspose2d(base_channels, base_channels, 2, stride=2)
        self.dec1 = ConvBlock(base_channels * 2, base_channels)

        # Output
        self.out_conv = nn.Conv2d(base_channels, in_channels, 1)

        # Grad-CAM hook storage
        self.gradcam_features = {}
        self.gradcam_gradients = {}
        self._register_gradcam_hooks()

    def _register_gradcam_hooks(self):
        """Register hooks on final decoder layer for Grad-CAM (Eq. 9)."""
        def save_features(name):
            def hook(module, input, output):
                self.gradcam_features[name] = output
            return hook

        def save_gradients(name):
            def hook(module, grad_input, grad_output):
                self.gradcam_gradients[name] = grad_output[0]
            return hook

        target_layer = self.dec1
        target_layer.register_forward_hook(save_features('dec1'))
        target_layer.register_full_backward_hook(save_gradients('dec1'))

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        # Encoder
        e1 = self.enc1(x)
        e2 = self.enc2(self.pool(e1))
        e3 = self.enc3(self.pool(e2))
        e4 = self.enc4(self.pool(e3))
        e5 = self.enc5(self.pool(e4))

        # Bottleneck
        b = self.bottleneck(self.pool(e5))

        # Decoder with skip connections
        d5 = self.dec5(torch.cat([self.up5(b), e5], dim=1))
        d4 = self.dec4(torch.cat([self.up4(d5), e4], dim=1))
        d3 = self.dec3(torch.cat([self.up3(d4), e3], dim=1))
        d2 = self.dec2(torch.cat([self.up2(d3), e2], dim=1))
        d1 = self.dec1(torch.cat([self.up1(d2), e1], dim=1))

        return self.out_conv(d1)

    def compute_gradcam(self, x: torch.Tensor, target_class: Optional[int] = None) -> torch.Tensor:
        """
        Compute Grad-CAM heatmap (Eq. 9).
        Returns: (B, H, W) normalized heatmap.
        """
        output = self.forward(x)
        if target_class is None:
            target_class = output.mean(dim=(1, 2, 3)).argmax()

        self.zero_grad()
        score = output[:, target_class].sum() if output.dim() > 2 else output[target_class]
        score.backward(retain_graph=True)

        features = self.gradcam_features['dec1']       # (B, C, H, W)
        gradients = self.gradcam_gradients['dec1']      # (B, C, H, W)

        # Global average pool gradients → alpha weights
        alpha = gradients.mean(dim=(2, 3), keepdim=True)  # (B, C, 1, 1)
        heatmap = (alpha * features).sum(dim=1)            # (B, H, W)
        heatmap = F.relu(heatmap)

        # Normalize per sample
        b, h, w = heatmap.size()
        heatmap_flat = heatmap.view(b, -1)
        heatmap_min = heatmap_flat.min(dim=1, keepdim=True)[0].view(b, 1, 1)
        heatmap_max = heatmap_flat.max(dim=1, keepdim=True)[0].view(b, 1, 1)
        heatmap = (heatmap - heatmap_min) / (heatmap_max - heatmap_min + 1e-8)

        return heatmap

    @classmethod
    def from_pretrained(cls, path: str) -> 'DetectionCNN':
        """Load pre-trained weights."""
        model = cls()
        state_dict = torch.load(path, map_location='cpu', weights_only=True)
        model.load_state_dict(state_dict)
        model.eval()
        return model


# ============================================================
# Loss Functions (Eq. 8, 10, 11 in paper)
# ============================================================

class DetectionLoss(nn.Module):
    """
    Composite loss: MSE + SSIM + Edge + Flux + Attention Consistency.
    Eq. 8 and Eq. 11 in the paper.
    """
    def __init__(self, lambda_ssim: float = 0.5, lambda_edge: float = 0.3,
                 lambda_flux: float = 0.1, gamma_attn: float = 0.2,
                 lambda_neg: float = 0.5):
        super().__init__()
        self.lambda_ssim = lambda_ssim
        self.lambda_edge = lambda_edge
        self.lambda_flux = lambda_flux
        self.gamma_attn = gamma_attn
        self.lambda_neg = lambda_neg

    def forward(self, pred: torch.Tensor, target: torch.Tensor,
                heatmap: Optional[torch.Tensor] = None,
                injection_mask: Optional[torch.Tensor] = None) -> Tuple[torch.Tensor, dict]:
        # MSE (Eq. 1 in paper, used as L_MSE)
        loss_mse = F.mse_loss(pred, target)

        # SSIM loss (Eq. 2)
        loss_ssim = 1.0 - self._ssim(pred, target)

        # Edge preservation (Eq. 3)
        laplacian = torch.tensor([[[[0., 1., 0.], [1., -4., 1.], [0., 1., 0.]]]],
                                 device=pred.device)
        edge_pred = F.conv2d(pred, laplacian, padding=1)
        edge_target = F.conv2d(target, laplacian, padding=1)
        loss_edge = (edge_pred - edge_target).abs().mean()

        # Flux conservation (Eq. 4)
        loss_flux = (pred.sum(dim=(2, 3)) - target.sum(dim=(2, 3))).abs().mean()

        total = (loss_mse + self.lambda_ssim * loss_ssim +
                 self.lambda_edge * loss_edge + self.lambda_flux * loss_flux)

        # Attention consistency loss (Eq. 10)
        loss_attn = torch.tensor(0.0, device=pred.device)
        if heatmap is not None and injection_mask is not None:
            mse_attn = F.mse_loss(heatmap, injection_mask)
            neg_penalty = (heatmap * (1 - injection_mask)).sum(dim=(1, 2)).mean()
            loss_attn = mse_attn + self.lambda_neg * neg_penalty
            total = total + self.gamma_attn * loss_attn

        losses = {'mse': loss_mse.item(), 'ssim': loss_ssim.item(),
                  'edge': loss_edge.item(), 'flux': loss_flux.item(),
                  'attn': loss_attn.item(), 'total': total.item()}
        return total, losses

    @staticmethod
    def _ssim(x: torch.Tensor, y: torch.Tensor, window_size: int = 11) -> torch.Tensor:
        """Structural similarity index (Wang et al. 2004)."""
        c1, c2 = 0.01 ** 2, 0.03 ** 2
        mu_x = F.avg_pool2d(x, window_size, 1, window_size // 2)
        mu_y = F.avg_pool2d(y, window_size, 1, window_size // 2)
        sigma_x = F.avg_pool2d(x * x, window_size, 1, window_size // 2) - mu_x * mu_x
        sigma_y = F.avg_pool2d(y * y, window_size, 1, window_size // 2) - mu_y * mu_y
        sigma_xy = F.avg_pool2d(x * y, window_size, 1, window_size // 2) - mu_x * mu_y
        ssim_map = ((2 * mu_x * mu_y + c1) * (2 * sigma_xy + c2)) / \
                   ((mu_x * mu_x + mu_y * mu_y + c1) * (sigma_x + sigma_y + c2))
        return ssim_map.mean()
