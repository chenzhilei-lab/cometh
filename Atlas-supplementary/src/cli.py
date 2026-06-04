"""CLI entry points for COMETH."""

import argparse
import sys


def demo() -> None:
    """Run the COMETH demo pipeline on sample data."""
    parser = argparse.ArgumentParser(
        description="COMETH — run demo detection + inversion pipeline"
    )
    parser.add_argument(
        "--device", default="auto",
        choices=["auto", "cpu", "cuda"],
        help="Device to run on (default: auto-detect)"
    )
    parser.add_argument(
        "--output-dir", default="./cometh_output",
        help="Directory for output figures and results"
    )
    args = parser.parse_args()

    import torch
    import os

    if args.device == "auto":
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    else:
        device = torch.device(args.device)

    print(f"COMETH v0.1.0")
    print(f"Device: {device}")
    if device.type == "cuda":
        print(f"GPU:   {torch.cuda.get_device_name(0)}")
    print()

    os.makedirs(args.output_dir, exist_ok=True)

    try:
        from cometh import DetectionCNN, PINNInversion, OODDetector
        print("[✓] All modules imported successfully.")
        print()
        print("    To run the full interactive demo:")
        print("    $ jupyter notebook notebooks/demo_workflow.ipynb")
        print()
        print("    Or in Python:")
        print("    >>> from cometh import DetectionCNN")
        print("    >>> cnn = DetectionCNN.from_pretrained('weights/cnn_detector.pt')")
    except ImportError as e:
        print(f"[✗] Import failed: {e}")
        print("    Did you 'pip install cometh'?")
        sys.exit(1)


if __name__ == "__main__":
    demo()
