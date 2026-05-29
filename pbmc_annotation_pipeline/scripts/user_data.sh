#!/bin/bash
# EC2 user-data bootstrap script.
# Runs as root at instance launch via cloud-init.
# Uses the hackathon-ec2-profile IAM instance role for S3 + Bedrock access.
set -euo pipefail

LOGFILE="/var/log/pbmc_pipeline_bootstrap.log"
exec > >(tee -a "${LOGFILE}") 2>&1

S3_BUCKET="scrippsresearch-chewu-hackathon"
AWS_REGION="us-west-2"
WORKDIR="/home/ec2-user/pipeline"

echo "======================================================"
echo "  PBMC Pipeline Bootstrap"
echo "  $(date)"
echo "======================================================"

# ── System updates & Python ───────────────────────────────────────────────────
dnf update -y --quiet
dnf install -y python3 python3-pip python3-devel \
               gcc gcc-c++ make git htop --quiet

echo "Python: $(python3 --version)"

# ── Python packages ───────────────────────────────────────────────────────────
python3 -m pip install --upgrade pip --quiet
pip3 install \
  "scanpy>=1.9" "anndata>=0.9" "celltypist>=1.6" \
  "boto3>=1.34" "botocore>=1.34" \
  "pandas>=2.0" "numpy>=1.24" "scikit-learn>=1.3" \
  "matplotlib>=3.7" "seaborn>=0.12" \
  "leidenalg>=0.10" "igraph>=0.10" "python-igraph>=0.10" \
  "umap-learn>=0.5" "scipy>=1.11" "h5py>=3.9" "numba>=0.57" \
  --quiet

echo "Python packages installed."

# ── Set up working directory ──────────────────────────────────────────────────
mkdir -p "${WORKDIR}/scripts" "${WORKDIR}/results"
chown -R ec2-user:ec2-user "${WORKDIR}"

# ── Download scripts from S3 ──────────────────────────────────────────────────
echo "Downloading scripts from S3..."
aws s3 sync "s3://${S3_BUCKET}/scripts/" "${WORKDIR}/scripts/" \
    --region "${AWS_REGION}"
chmod +x "${WORKDIR}/scripts/"*.sh

echo "Scripts downloaded:"
ls -la "${WORKDIR}/scripts/"

# ── Run pipeline as ec2-user ──────────────────────────────────────────────────
echo "Starting pipeline..."
cd "${WORKDIR}"

sudo -u ec2-user bash -c "
  export S3_BUCKET='${S3_BUCKET}'
  export AWS_REGION='${AWS_REGION}'
  export WORKDIR='${WORKDIR}'
  export MPLBACKEND='Agg'
  cd '${WORKDIR}'
  bash scripts/run_pipeline.sh
"

echo "======================================================"
echo "  Bootstrap complete: $(date)"
echo "======================================================"

# Self-terminate so billing stops automatically
INSTANCE_ID=$(curl -s http://169.254.169.254/latest/meta-data/instance-id)
aws ec2 terminate-instances \
    --instance-ids "${INSTANCE_ID}" \
    --region "${AWS_REGION}" || true
