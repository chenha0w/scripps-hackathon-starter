#!/bin/bash
# Install all Python dependencies for the PBMC annotation pipeline.
# Runs on Amazon Linux 2023 (EC2) or any Python 3.9+ environment.
set -euo pipefail

echo "=== Installing Python packages ==="
python3 -m pip install --upgrade pip --quiet

pip3 install \
  "scanpy>=1.9"          \
  "anndata>=0.9"         \
  "celltypist>=1.6"      \
  "boto3>=1.34"          \
  "botocore>=1.34"       \
  "pandas>=2.0"          \
  "numpy>=1.24"          \
  "scikit-learn>=1.3"    \
  "matplotlib>=3.7"      \
  "seaborn>=0.12"        \
  "leidenalg>=0.10"      \
  "igraph>=0.10"         \
  "python-igraph>=0.10"  \
  "umap-learn>=0.5"      \
  "scipy>=1.11"          \
  "h5py>=3.9"            \
  "numba>=0.57"          \
  --quiet

echo "Package versions:"
python3 -c "
import scanpy, celltypist, sklearn, boto3, pandas, numpy
print(f'  scanpy      {scanpy.__version__}')
print(f'  celltypist  {celltypist.__version__}')
print(f'  scikit-learn {sklearn.__version__}')
print(f'  boto3       {boto3.__version__}')
print(f'  pandas      {pandas.__version__}')
print(f'  numpy       {numpy.__version__}')
"
echo "All packages installed successfully."
