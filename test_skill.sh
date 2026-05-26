#!/usr/bin/env bash
# test_skill.sh — Hello-world exercise of the hackathon-aws Claude skill.
#
# Walks through the four workflows the skill documents:
#   1. SSO login
#   2. Create a personal S3 bucket
#   3. Read from S3 (own bucket + an Amazon Open Data bucket)
#   4. Launch and terminate a small EC2 instance
#
# Safe to re-run: bucket creation is idempotent, instance is always terminated.
#
# Usage:
#   ./test_skill.sh              # run the full test
#   ./test_skill.sh --no-ec2     # skip the EC2 launch (S3-only smoke test)
#   ./test_skill.sh --keep-bucket  # don't ask to clean up the test bucket

set -u  # don't set -e — we want to record per-step pass/fail and continue

# ---------- Config (edit these if your setup differs) ----------
PROFILE="bgood-scripps"
SSO_SESSION="scripps-hackathon"
SSO_START_URL="https://d-9267e96a16.awsapps.com/start"
SSO_REGION="us-west-2"
ACCOUNT_ID="127696279288"
REGION="us-west-2"
SSO_ROLE_NAME="Hackathon"   # adjust if yours differs (check the SSO portal)

BUCKET="scrippsresearch-bgood-hackathon"
OPEN_DATA_BUCKET="sea-ad-single-cell-profiling"
OPEN_DATA_PREFIX="PFC/RNAseq/"

# Instance launch params (from the skill)
AMI_ID="ami-00563078bca04e287"
INSTANCE_TYPE="t3.micro"           # smallest viable for hello-world
SUBNET_ID="subnet-0096ffc9c05bebab3"
SG_ID="sg-09d5ef7889a26f56a"
INSTANCE_PROFILE="hackathon-ec2-profile"
INSTANCE_NAME="bgood-hackathon-test"

# ---------- Flags ----------
RUN_EC2=1
KEEP_BUCKET=0
for arg in "$@"; do
  case "$arg" in
    --no-ec2) RUN_EC2=0 ;;
    --keep-bucket) KEEP_BUCKET=1 ;;
    -h|--help) sed -n '2,12p' "$0"; exit 0 ;;
    *) echo "unknown arg: $arg" >&2; exit 2 ;;
  esac
done

# ---------- Pretty output ----------
# Use a single CURRENT string + append-only RESULTS array so this works on
# macOS's stock bash 3.2 (no negative array subscripts).
CURRENT=""
RESULTS=()
record() { CURRENT="$1"; printf '\n==> %s\n' "$1"; }
pass()   { RESULTS+=("PASS  $CURRENT"); printf '    \xe2\x9c\x93 pass\n'; }
fail()   { RESULTS+=("FAIL  $CURRENT"); printf '    \xe2\x9c\x97 fail: %s\n' "${1:-}"; }
skip()   { RESULTS+=("SKIP  $CURRENT"); printf '    - skipped: %s\n' "${1:-}"; }

aws_p() { aws --profile "$PROFILE" --region "$REGION" "$@"; }

# ---------- Step 0: AWS CLI present? ----------
record "Step 0  Check AWS CLI is installed"
if ! command -v aws >/dev/null 2>&1; then
  fail "aws CLI not found on PATH"
  cat <<EOF

The AWS CLI v2 is not installed. Install it then re-run this script:

  # macOS (Homebrew)
  brew install awscli

  # or official installer
  curl "https://awscli.amazonaws.com/AWSCLIV2.pkg" -o /tmp/AWSCLIV2.pkg
  sudo installer -pkg /tmp/AWSCLIV2.pkg -target /

EOF
  exit 1
fi
printf '    aws version: %s\n' "$(aws --version 2>&1)"
pass

# ---------- Step 1: SSO profile + login ----------
record "Step 1  Configure SSO profile and login"

# Ensure ~/.aws/config has our sso-session and profile (modern format).
mkdir -p "$HOME/.aws"
CONFIG_FILE="$HOME/.aws/config"
touch "$CONFIG_FILE"
if ! grep -q "^\[sso-session $SSO_SESSION\]" "$CONFIG_FILE"; then
  printf '    adding [sso-session %s] to %s\n' "$SSO_SESSION" "$CONFIG_FILE"
  cat >> "$CONFIG_FILE" <<EOF

[sso-session $SSO_SESSION]
sso_start_url = $SSO_START_URL
sso_region = $SSO_REGION
sso_registration_scopes = sso:account:access
EOF
fi
if ! grep -q "^\[profile $PROFILE\]" "$CONFIG_FILE"; then
  printf '    adding [profile %s] to %s\n' "$PROFILE" "$CONFIG_FILE"
  cat >> "$CONFIG_FILE" <<EOF

[profile $PROFILE]
sso_session = $SSO_SESSION
sso_account_id = $ACCOUNT_ID
sso_role_name = $SSO_ROLE_NAME
region = $REGION
output = json
EOF
fi

# Quick check: is the token already valid?
if aws_p sts get-caller-identity >/dev/null 2>&1; then
  printf '    existing SSO session is valid\n'
else
  printf '    no valid session — running: aws sso login --profile %s\n' "$PROFILE"
  printf '    (a browser window will open)\n'
  if ! aws sso login --profile "$PROFILE"; then
    fail "aws sso login failed"
    printf '%s\n' "${RESULTS[@]}"
    exit 1
  fi
fi

IDENTITY=$(aws_p sts get-caller-identity --output json 2>/dev/null)
if [[ -z "$IDENTITY" ]]; then
  fail "get-caller-identity returned nothing"
  printf '%s\n' "${RESULTS[@]}"
  exit 1
fi
printf '    identity: %s\n' "$IDENTITY"
pass

# ---------- Step 2: Create personal S3 bucket ----------
record "Step 2  Create personal S3 bucket s3://$BUCKET"

if aws_p s3api head-bucket --bucket "$BUCKET" 2>/dev/null; then
  printf '    bucket already exists — reusing\n'
  pass
else
  if aws_p s3 mb "s3://$BUCKET" 2>&1 | sed 's/^/    /'; then
    pass
  else
    fail "could not create bucket (name may be taken globally)"
  fi
fi

# ---------- Step 3a: Write/read hello-world to your bucket ----------
record "Step 3a Write and read hello-world.txt in your bucket"

HELLO_LOCAL="$(mktemp -t hackathon-hello.XXXXXX)"
HELLO_DOWN="$(mktemp -t hackathon-hello-down.XXXXXX)"
printf 'hello from %s at %s\n' "$(whoami)" "$(date -u +%FT%TZ)" > "$HELLO_LOCAL"

if aws_p s3 cp "$HELLO_LOCAL" "s3://$BUCKET/hello-world.txt" 2>&1 | sed 's/^/    /' \
   && aws_p s3 cp "s3://$BUCKET/hello-world.txt" "$HELLO_DOWN" 2>&1 | sed 's/^/    /' \
   && diff -q "$HELLO_LOCAL" "$HELLO_DOWN" >/dev/null; then
  printf '    round-trip contents match: %s\n' "$(cat "$HELLO_DOWN")"
  pass
else
  fail "upload/download/diff failed"
fi
rm -f "$HELLO_LOCAL" "$HELLO_DOWN"

# ---------- Step 3b: Read from Amazon Open Data (unsigned) ----------
record "Step 3b Read from Amazon Open Data bucket (unsigned)"

OD_OUT=$(aws s3 ls "s3://$OPEN_DATA_BUCKET/$OPEN_DATA_PREFIX" \
         --no-sign-request --region "$REGION" 2>&1 | head -5)
if [[ -n "$OD_OUT" && "$OD_OUT" != *error* && "$OD_OUT" != *Error* ]]; then
  printf '%s\n' "$OD_OUT" | sed 's/^/    /'
  pass
else
  printf '%s\n' "$OD_OUT" | sed 's/^/    /'
  fail "could not list open-data bucket"
fi

# ---------- Step 4: Launch (and terminate) an EC2 instance ----------
if [[ "$RUN_EC2" -eq 0 ]]; then
  record "Step 4  Launch EC2 instance"
  skip "--no-ec2 flag set"
else
  record "Step 4a Launch $INSTANCE_TYPE instance"

  # Try with the instance profile first; if it doesn't exist yet, retry without.
  LAUNCH_OUT=$(aws_p ec2 run-instances \
    --image-id "$AMI_ID" \
    --instance-type "$INSTANCE_TYPE" \
    --subnet-id "$SUBNET_ID" \
    --security-group-ids "$SG_ID" \
    --iam-instance-profile "Name=$INSTANCE_PROFILE" \
    --metadata-options HttpTokens=required \
    --tag-specifications \
      "ResourceType=instance,Tags=[{Key=Name,Value=$INSTANCE_NAME}]" \
    --query 'Instances[0].InstanceId' --output text 2>&1)

  if [[ "$LAUNCH_OUT" == i-* ]]; then
    INSTANCE_ID="$LAUNCH_OUT"
    printf '    launched (with instance profile): %s\n' "$INSTANCE_ID"
  else
    printf '    launch with instance profile failed: %s\n' "$LAUNCH_OUT" | sed 's/^/    /'
    printf '    retrying without --iam-instance-profile...\n'
    LAUNCH_OUT=$(aws_p ec2 run-instances \
      --image-id "$AMI_ID" \
      --instance-type "$INSTANCE_TYPE" \
      --subnet-id "$SUBNET_ID" \
      --security-group-ids "$SG_ID" \
      --metadata-options HttpTokens=required \
      --tag-specifications \
        "ResourceType=instance,Tags=[{Key=Name,Value=$INSTANCE_NAME}]" \
      --query 'Instances[0].InstanceId' --output text 2>&1)
    if [[ "$LAUNCH_OUT" == i-* ]]; then
      INSTANCE_ID="$LAUNCH_OUT"
      printf '    launched (no instance profile): %s\n' "$INSTANCE_ID"
    else
      INSTANCE_ID=""
      printf '%s\n' "$LAUNCH_OUT" | sed 's/^/    /'
      fail "run-instances failed"
    fi
  fi

  if [[ -n "${INSTANCE_ID:-}" ]]; then
    pass

    record "Step 4b Wait for instance to reach running state"
    if aws_p ec2 wait instance-running --instance-ids "$INSTANCE_ID" 2>&1 | sed 's/^/    /'; then
      STATE=$(aws_p ec2 describe-instances --instance-ids "$INSTANCE_ID" \
        --query 'Reservations[0].Instances[0].State.Name' --output text)
      printf '    state: %s\n' "$STATE"
      [[ "$STATE" == "running" ]] && pass || fail "unexpected state: $STATE"
    else
      fail "wait instance-running timed out"
    fi

    record "Step 4c Terminate instance $INSTANCE_ID"
    if aws_p ec2 terminate-instances --instance-ids "$INSTANCE_ID" \
         --query 'TerminatingInstances[0].CurrentState.Name' --output text \
         2>&1 | sed 's/^/    /'; then
      pass
    else
      fail "terminate-instances failed — TERMINATE MANUALLY: $INSTANCE_ID"
    fi
  fi
fi

# ---------- Optional cleanup ----------
if [[ "$KEEP_BUCKET" -eq 0 ]]; then
  record "Cleanup Remove hello-world.txt from your bucket"
  if aws_p s3 rm "s3://$BUCKET/hello-world.txt" 2>&1 | sed 's/^/    /'; then
    pass
  else
    fail "could not remove test object"
  fi
fi

# ---------- Summary ----------
printf '\n========== Summary ==========\n'
printf '%s\n' "${RESULTS[@]}"

# Exit non-zero if anything failed
if printf '%s\n' "${RESULTS[@]}" | grep -q '^FAIL'; then
  exit 1
fi
exit 0
