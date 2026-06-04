# COMETH Pre-trained Weights

Weights are excluded from version control due to size. Download from Zenodo.

## Files

| File | Size | Model | Training | Status |
|------|------|-------|----------|--------|
| `cnn_detector.pt` | 307 MB | DetectionCNN | DIRTY 30k, 113-epoch, RTX 3090, val=0.0000 | ✅ Available |
| `pinn_inversion.pt` | — | PINNInversion | — | ⏳ Pending |
| `ood_detector.pkl` | — | OODDetector | — | ⏳ Pending |

## Download

Zenodo: [DOI to be added upon acceptance]
GitHub Releases: https://github.com/chenzhilei-lab/cometh/releases

## Quick Usage

```python
import torch
from src.cnn_detection import DetectionCNN

model = DetectionCNN.from_pretrained('weights/cnn_detector.pt')
model.eval()
```

## License

Dual license (MIT academic / commercial). See root LICENSE file.
Contact: cometh@proton.me
