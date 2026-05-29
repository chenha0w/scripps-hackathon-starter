#!/bin/bash
# Master orchestrator — runs all four pipeline steps in sequence,
# captures /usr/bin/time -v output for each, then syncs results to S3.
set -euo pipefail

S3_BUCKET="${S3_BUCKET:-scrippsresearch-chewu-hackathon}"
AWS_REGION="${AWS_REGION:-us-west-2}"
WORKDIR="${WORKDIR:-/home/ec2-user/pipeline}"
LOG="${WORKDIR}/results/pipeline.log"

mkdir -p "${WORKDIR}/results"
cd "${WORKDIR}"
exec > >(tee -a "${LOG}") 2>&1

echo "======================================================"
echo "  PBMC Annotation Pipeline"
echo "  Start: $(date)"
echo "  S3 bucket: s3://${S3_BUCKET}"
echo "======================================================"

run_step() {
    local name="$1"
    local cmd="$2"
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "  ${name}"
    echo "  $(date)"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    /usr/bin/time -v bash -c "${cmd}" 2>&1
    echo "  ✓ ${name} complete"
}

run_step "Step 1: Preprocessing" \
    "python3 scripts/01_preprocessing.py"

run_step "Step 2: Zero-Shot LLM Annotation (Claude via Bedrock)" \
    "AWS_PROFILE='' python3 scripts/02_zero_shot_llm.py"

run_step "Step 3: Reference Mapping (CellTypist)" \
    "python3 scripts/03_reference_mapping.py"

run_step "Step 4: Evaluation & Comparison" \
    "python3 scripts/04_evaluate.py"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Uploading results to S3"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
aws s3 sync "${WORKDIR}/results/" "s3://${S3_BUCKET}/results/" \
    --region "${AWS_REGION}"
aws s3 sync "${WORKDIR}/scripts/"  "s3://${S3_BUCKET}/scripts/"  \
    --region "${AWS_REGION}"

echo ""
echo "======================================================"
echo "  Pipeline COMPLETE"
echo "  End: $(date)"
echo "  Results: s3://${S3_BUCKET}/results/"
echo "======================================================"
