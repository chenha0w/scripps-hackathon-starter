#!/bin/bash
# Local runner: runs the full pipeline on this machine.
# Uses AWS Bedrock (chewu-scripps profile) for LLM annotation.
# Uploads all results to s3://scrippsresearch-chewu-hackathon when done.
#
# Note: EC2 quota is currently maxed out by other hackathon participants.
# PBMC3k has only ~2700 cells, so local Python is fast enough (~15-20 min total).
set -euo pipefail

PROFILE="chewu-scripps"
REGION="us-west-2"
S3_BUCKET="scrippsresearch-chewu-hackathon"
SCRIPT_DIR="$(cd "$(dirname "$0")/scripts" && pwd)"
WORKDIR="$(cd "$(dirname "$0")" && pwd)"

echo "======================================================"
echo "  PBMC Annotation Pipeline (Local + AWS Bedrock/S3)"
echo "  Profile : ${PROFILE}"
echo "  Results : s3://${S3_BUCKET}/results/"
echo "======================================================"

cd "${WORKDIR}"
mkdir -p results/plots results/evaluation
LOG="results/pipeline.log"
exec > >(tee -a "${LOG}") 2>&1

export AWS_PROFILE="${PROFILE}"
export AWS_DEFAULT_REGION="${REGION}"
export MPLBACKEND="Agg"

# ── Check Python packages ─────────────────────────────────────────────────────
echo ""
echo "[0/5] Checking / installing Python packages..."
bash "${SCRIPT_DIR}/install_packages.sh"

# ── Run pipeline steps ────────────────────────────────────────────────────────
run_step() {
    local name="$1"; local script="$2"
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "  ${name}  —  $(date '+%H:%M:%S')"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    /usr/bin/time -v python3 "${SCRIPT_DIR}/${script}" 2>&1
}

run_step "[1/5] Preprocessing (scanpy)"    "01_preprocessing.py"
run_step "[2/5] Zero-Shot LLM (Bedrock)"   "02_zero_shot_llm.py"
run_step "[3/5] Reference Mapping (CellTypist)" "03_reference_mapping.py"
run_step "[4/5] Evaluation & Comparison"   "04_evaluate.py"

# ── Upload to S3 ──────────────────────────────────────────────────────────────
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  [5/5] Uploading results to S3"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
aws s3 sync "${WORKDIR}/results/"  "s3://${S3_BUCKET}/results/"  \
    --profile "${PROFILE}" --region "${REGION}"
aws s3 sync "${SCRIPT_DIR}/"       "s3://${S3_BUCKET}/scripts/"  \
    --profile "${PROFILE}" --region "${REGION}" --exclude "*.pyc"

echo ""
echo "======================================================"
echo "  DONE — $(date)"
echo "  Results: s3://${S3_BUCKET}/results/"
echo ""
echo "  Key outputs:"
echo "    results/evaluation/metrics_summary.csv    — accuracy table"
echo "    results/evaluation/method_comparison.png  — bar chart"
echo "    results/evaluation/umap_three_way.png     — side-by-side UMAP"
echo "    results/evaluation/confusion_*.png        — confusion matrices"
echo "    results/evaluation/resource_summary.png   — time + memory"
echo "======================================================"
