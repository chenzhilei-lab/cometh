# COMETH: COmet MEasurement via Deep Learning and Hard-constraints
# Docker environment for exact reproducibility
#
# Build:  docker build -t cometh:latest .
# Run:    docker run --gpus all -it cometh:latest python run_comparison.py
#
# Requires: NVIDIA GPU with CUDA 12.1+ and nvidia-docker runtime.

FROM nvidia/cuda:12.1.0-runtime-ubuntu22.04

# System dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3.10 \
    python3-pip \
    git \
    wget \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Python dependencies (pinned versions for reproducibility)
RUN pip3 install --no-cache-dir \
    torch==2.1.0 \
    torchvision==0.16.0 \
    numpy==1.24.3 \
    scipy==1.11.3 \
    matplotlib==3.7.2 \
    astropy==5.3.1 \
    astroquery==0.4.6 \
    scikit-learn==1.3.1 \
    scikit-image==0.21.0 \
    tqdm==4.65.0 \
    pyyaml==6.0.1 \
    jupyter==1.0.0 \
    ipywidgets==8.1.0 \
    photutils==1.9.0

# Copy COMETH source code and configs
COPY src/ /app/src/
COPY configs/ /app/configs/
COPY notebooks/ /app/notebooks/
COPY data_generation/ /app/data_generation/
COPY requirements.txt /app/

WORKDIR /app

# Verify installation
RUN python3 -c "import torch; print(f'PyTorch {torch.__version__}, CUDA available: {torch.cuda.is_available()}')"

CMD ["python3", "-c", "print('COMETH Docker environment ready. See notebooks/demo_workflow.ipynb for quick start.')"]
