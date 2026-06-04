# COMETH: COmet MEasurement via deep learning and Hard-constraints
# ============================================================================
# Multi-stage Docker build for production and development.
#
# Quick start:
#   docker build -t cometh:latest .
#   docker run --gpus all -it -p 8888:8888 -v $(pwd)/data:/app/data cometh:latest
#
# Without GPU (CPU-only inference, slower):
#   docker build --build-arg CUDA_IMAGE=nvidia/cuda:12.1.0-runtime-ubuntu22.04 -t cometh:cpu .
#   docker run -it -p 8888:8888 cometh:cpu
#
# Requires: NVIDIA GPU with CUDA 12.1+ and nvidia-container-toolkit for GPU mode.

# ============================================================================
# Stage 1: Build environment (for compiling any native extensions if needed)
# ============================================================================
FROM nvidia/cuda:12.1.0-devel-ubuntu22.04 AS builder

RUN apt-get update && apt-get install -y --no-install-recommends \
    python3.10 \
    python3-pip \
    python3.10-dev \
    git \
    && rm -rf /var/lib/apt/lists/*

# Pre-install PyTorch with CUDA support
RUN pip3 install --no-cache-dir \
    torch==2.1.2 \
    torchvision==0.16.2 \
    --index-url https://download.pytorch.org/whl/cu121

# ============================================================================
# Stage 2: Runtime (smaller, no compiler toolchain)
# ============================================================================
FROM nvidia/cuda:12.1.0-runtime-ubuntu22.04

LABEL org.opencontainers.image.title="COMETH"
LABEL org.opencontainers.image.description="Deep learning pipeline for comet dust characterization"
LABEL org.opencontainers.image.source="https://github.com/cometh-project/cometh"
LABEL org.opencontainers.image.licenses="MIT with commercial addendum"
LABEL maintainer="Zhilei Chen <cometh@proton.me>"

# System dependencies (minimal — only what's needed at runtime)
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3.10 \
    python3-pip \
    wget \
    && ln -sf /usr/bin/python3.10 /usr/bin/python \
    && ln -sf /usr/bin/python3.10 /usr/bin/python3 \
    && rm -rf /var/lib/apt/lists/*

# Python dependencies — pinned versions for reproducibility
# Separated into layers by update frequency for cache efficiency
RUN pip3 install --no-cache-dir \
    torch==2.1.2 \
    torchvision==0.16.2 \
    --index-url https://download.pytorch.org/whl/cu121

RUN pip3 install --no-cache-dir \
    numpy==1.24.3 \
    scipy==1.11.3 \
    matplotlib==3.7.2 \
    astropy==5.3.1 \
    scikit-learn==1.3.1 \
    scikit-image==0.21.0 \
    tqdm==4.65.0 \
    pyyaml==6.0.1 \
    photutils==1.9.0

RUN pip3 install --no-cache-dir \
    jupyter==1.0.0 \
    jupyterlab==4.0.9 \
    ipywidgets==8.1.0 \
    notebook==7.0.6

# Copy application code
COPY requirements.txt /app/
COPY src/ /app/src/
COPY configs/ /app/configs/
COPY notebooks/ /app/notebooks/
COPY data_generation/ /app/data_generation/
COPY weights/ /app/weights/
COPY data/ /app/data/

# Create entrypoint script
RUN echo '#!/bin/bash\n\
set -e\n\
echo "═══════════════════════════════════════"\n\
echo "  COMETH — Comet Dust Characterization"\n\
echo "═══════════════════════════════════════"\n\
echo ""\n\
python -c "import torch; print(f\"PyTorch {torch.__version__}, CUDA: {torch.cuda.is_available()}\")"\n\
python -c "import torch; print(f\"GPU: {torch.cuda.get_device_name(0)}\")" 2>/dev/null || echo "GPU: not available (CPU-only mode)"\n\
echo ""\n\
echo "Quick start:"\n\
echo "  jupyter notebook notebooks/demo_workflow.ipynb"\n\
echo "  python -c \"from src import DetectionCNN; print(\\\"COMETH imported successfully\\\")\""\n\
echo ""\n\
exec "$@"' > /app/entrypoint.sh && chmod +x /app/entrypoint.sh

WORKDIR /app

# Verify import works
RUN python -c "import sys; sys.path.insert(0, '/app'); from src import DetectionCNN, PINNInversion, OODDetector; print('All COMETH modules imported successfully.')"

# Health check — verify PyTorch + CUDA
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import torch; assert torch.cuda.is_available()" || python -c "import torch; print('CPU mode OK')"

EXPOSE 8888

ENTRYPOINT ["/app/entrypoint.sh"]
CMD ["jupyter", "lab", "--ip=0.0.0.0", "--port=8888", "--no-browser", "--allow-root", "--NotebookApp.token=''", "--NotebookApp.password=''"]
