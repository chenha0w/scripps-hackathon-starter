#!/bin/bash
# Local launcher: creates the S3 bucket, uploads all scripts, launches EC2.
# Prerequisites: aws CLI configured with profile chewu-scripps.
set -euo pipefail

PROFILE="chewu-scripps"
REGION="us-west-2"
S3_BUCKET="scrippsresearch-chewu-hackathon"
INSTANCE_TYPE="r5.xlarge"          # 4 vCPU, 32 GB — sufficient for scanpy + celltypist
INSTANCE_PROFILE="hackathon-ec2-profile"
KEY_NAME="scripps_hackathon"
SECURITY_GROUP="sg-0b6494f1dff90ff45"   # default VPC SG (allows all outbound)
SUBNET="subnet-0e1bdfbc00c6b98d6"       # public subnet, us-west-2a
SCRIPT_DIR="$(cd "$(dirname "$0")/scripts" && pwd)"

echo "======================================================"
echo "  PBMC Annotation Pipeline Launcher"
echo "  Profile : ${PROFILE}"
echo "  Region  : ${REGION}"
echo "  Bucket  : ${S3_BUCKET}"
echo "======================================================"

# ── Step 1: Create S3 bucket ──────────────────────────────────────────────────
echo ""
echo "[1/4] Creating S3 bucket: ${S3_BUCKET}"
if aws s3api head-bucket --bucket "${S3_BUCKET}" \
   --profile "${PROFILE}" 2>/dev/null; then
    echo "  Bucket already exists — skipping."
else
    aws s3api create-bucket \
        --bucket "${S3_BUCKET}" \
        --region "${REGION}" \
        --create-bucket-configuration LocationConstraint="${REGION}" \
        --profile "${PROFILE}"
    # Block all public access
    aws s3api put-public-access-block \
        --bucket "${S3_BUCKET}" \
        --public-access-block-configuration \
          BlockPublicAcls=true,IgnorePublicAcls=true,\
BlockPublicPolicy=true,RestrictPublicBuckets=true \
        --profile "${PROFILE}"
    echo "  Bucket created and locked down."
fi

# ── Step 2: Upload scripts ────────────────────────────────────────────────────
echo ""
echo "[2/4] Uploading scripts to s3://${S3_BUCKET}/scripts/"
aws s3 sync "${SCRIPT_DIR}/" "s3://${S3_BUCKET}/scripts/" \
    --profile "${PROFILE}" \
    --region  "${REGION}"  \
    --exclude "*.pyc"
echo "  Scripts uploaded:"
aws s3 ls "s3://${S3_BUCKET}/scripts/" --profile "${PROFILE}"

# ── Step 3: Find latest Amazon Linux 2023 AMI ─────────────────────────────────
echo ""
echo "[3/4] Finding latest Amazon Linux 2023 AMI..."
AMI_ID=$(aws ec2 describe-images \
    --owners amazon \
    --filters \
        "Name=name,Values=al2023-ami-2023*-x86_64" \
        "Name=state,Values=available" \
    --query "sort_by(Images, &CreationDate)[-1].ImageId" \
    --output text \
    --profile "${PROFILE}" \
    --region  "${REGION}")
echo "  AMI: ${AMI_ID}"

# ── Step 4: Launch EC2 ────────────────────────────────────────────────────────
echo ""
echo "[4/4] Launching EC2 instance (${INSTANCE_TYPE})..."

USER_DATA_B64=$(base64 -w 0 "${SCRIPT_DIR}/user_data.sh")

INSTANCE_ID=$(aws ec2 run-instances \
    --image-id           "${AMI_ID}" \
    --instance-type      "${INSTANCE_TYPE}" \
    --subnet-id          "${SUBNET}" \
    --security-group-ids "${SECURITY_GROUP}" \
    --key-name           "${KEY_NAME}" \
    --iam-instance-profile Name="${INSTANCE_PROFILE}" \
    --user-data          "${USER_DATA_B64}" \
    --instance-initiated-shutdown-behavior terminate \
    --block-device-mappings \
        "DeviceName=/dev/xvda,Ebs={VolumeSize=30,VolumeType=gp3,DeleteOnTermination=true}" \
    --tag-specifications \
        "ResourceType=instance,Tags=[
          {Key=Name,Value=pbmc-annotation-pipeline},
          {Key=Project,Value=scripps-hackathon},
          {Key=Owner,Value=chewu}
        ]" \
    --query "Instances[0].InstanceId" \
    --output text \
    --profile "${PROFILE}" \
    --region  "${REGION}")

echo ""
echo "======================================================"
echo "  Instance launched: ${INSTANCE_ID}"
echo "  Type            : ${INSTANCE_TYPE} (4 vCPU / 32 GB)"
echo "  IAM profile     : ${INSTANCE_PROFILE}"
echo "  Auto-terminates : yes (on pipeline completion)"
echo ""
echo "  Monitor status:"
echo "    aws ec2 describe-instance-status \\"
echo "      --instance-ids ${INSTANCE_ID} \\"
echo "      --profile ${PROFILE} --region ${REGION}"
echo ""
echo "  Check logs (via SSM or after completion on S3):"
echo "    aws s3 ls s3://${S3_BUCKET}/results/ --profile ${PROFILE}"
echo ""
echo "  Retrieve results when done:"
echo "    aws s3 sync s3://${S3_BUCKET}/results/ ./pipeline_results/ \\"
echo "      --profile ${PROFILE} --region ${REGION}"
echo ""
echo "  Expected runtime: ~25-40 min"
echo "  (pip install ~10 min + preprocessing ~5 min +"
echo "   zero-shot LLM ~1 min + CellTypist ~8 min + eval ~2 min)"
echo "======================================================"
