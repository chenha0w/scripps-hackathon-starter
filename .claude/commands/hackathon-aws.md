You are helping the user work with the Scripps Research 2026 Hackathon AWS
account. You have full context on the account's infrastructure. The primary
mechanism for S3, documentation, and pricing is the awslabs MCP servers (see
*MCP Server Setup* below); raw `aws` CLI via Bash remains appropriate for EC2
launch, EICE SSH, and other ops not covered by those servers.

## Account & region

- **Account:** `127696279288`
- **Region:** `us-west-2`
- **SSO profile:** `inewman-wsl` (substitute the user's actual profile if different)
- **SSO start URL:** `https://d-9267e96a16.awsapps.com/start`

If any AWS command returns `Token has expired`, tell the user to run:
```
! aws sso login --profile inewman-wsl
```
then retry.

---

## MCP Server Setup — check this BEFORE anything else

**Detection.** Before doing anything for the user's task, check whether the
three awslabs MCP servers are connected. Look in the available-tools list
(including the deferred-tool list surfaced in system reminders) for tools
whose names contain any of:

- `aws-pricing`
- `aws-documentation` (or `aws-docs`)
- `s3-mcp-server` (or `s3` from an `awslabs` namespace)

**If any are missing — STOP.** Reply to the user with exactly this and
nothing else:

> The hackathon-aws MCP servers aren't installed yet. Please run these four
> commands, then restart Claude Code:
>
> ```bash
> curl -LsSf https://astral.sh/uv/install.sh | sh
> claude mcp add s3 -- uvx awslabs.s3-mcp-server@latest
> claude mcp add aws-docs -- uvx awslabs.aws-documentation-mcp-server@latest
> claude mcp add aws-pricing -- uvx awslabs.aws-pricing-mcp-server@latest
> ```
>
> These install globally; one-time setup for the whole hackathon.

Do **not** attempt the user's task with raw `aws` CLI / Bash fallbacks when
the MCP servers are missing. The MCP servers exist specifically to give
better, structured answers (live pricing, doc lookups, S3 browsing); falling
back defeats the point and produces worse results. Reply with the install
instructions and wait for the user to restart.

**If all three are connected**, proceed with the user's task using the MCP
tools as the primary mechanism. Bash `aws` CLI remains appropriate for EC2
launch, EICE SSH, IAM, and other ops not covered by these three servers.

What each server does:
- **s3** — browse buckets, read/write objects, access Open Data directly
- **aws-docs** — real-time AWS documentation lookup
- **aws-pricing** — live cost estimates ("how much does a g6e.xlarge cost per hour?")

4 commands, one time, and they're set for the whole hackathon.

---

## VPC & networking (permanent — set up 2026-05-26)

| Resource | ID | Notes |
|---|---|---|
| VPC | `vpc-0c7b131a02a1b3b85` | `172.31.0.0/16` — aws-controltower-VPC |
| PrivateSubnet1A | `subnet-0096ffc9c05bebab3` | `172.31.64.0/20` — us-west-2a |
| PrivateSubnet2A | `subnet-071d3dbca8e9b7209` | `172.31.32.0/20` — us-west-2b |
| PrivateSubnet3A | `subnet-0e8c4795d00d2f2c6` | `172.31.80.0/20` — us-west-2c |
| PublicSubnet1A | `subnet-0e1bdfbc00c6b98d6` | `172.31.0.0/20` — us-west-2a |
| Internet Gateway | `igw-04019d688ed9e7748` | `hackathon-igw` — attached to VPC |
| NAT Gateway | `nat-0561360099820e566` | `hackathon-nat` — EIP 54.186.216.143 |
| S3 gateway endpoint | `vpce-0ebf641ca3311f239` | Free S3 traffic from all subnets |
| EICE endpoint | `eice-0ecadad192e23f430` | SSH to private instances |
| EICE security group | `sg-09d5ef7889a26f56a` | `hackathon-eice-instance` |
| IAM instance profile | `hackathon-ec2-profile` | Provisioned; attach at launch for S3 + Bedrock access |

Private instances have **outbound internet** via NAT. EICE provides SSH.
S3 traffic is free via gateway endpoint.

---

## Launching an EC2 instance

```bash
# Choose instance type
INSTANCE_TYPE=t3.medium    # light work
INSTANCE_TYPE=t3.xlarge    # ML / large data

INSTANCE_ID=$(aws ec2 run-instances \
  --image-id ami-00563078bca04e287 \
  --instance-type $INSTANCE_TYPE \
  --subnet-id subnet-0096ffc9c05bebab3 \
  --security-group-ids sg-09d5ef7889a26f56a \
  --iam-instance-profile Name=hackathon-ec2-profile \
  --metadata-options HttpTokens=required \
  --tag-specifications \
    'ResourceType=instance,Tags=[{Key=Name,Value=<name>-hackathon}]' \
  --profile inewman-wsl --region us-west-2 \
  --query 'Instances[0].InstanceId' --output text)
echo "Instance: $INSTANCE_ID"
```

Wait for running state:
```bash
aws ec2 wait instance-running --instance-ids $INSTANCE_ID \
  --profile inewman-wsl --region us-west-2
```

Add extra storage (optional, for large datasets):
```bash
# Append to run-instances:
--block-device-mappings \
  '[{"DeviceName":"/dev/xvdf","Ebs":{"VolumeSize":100,"VolumeType":"gp3","DeleteOnTermination":true}}]'

# Then on the instance:
sudo mkfs.xfs /dev/xvdf && sudo mkdir /data
sudo mount /dev/xvdf /data && sudo chown ec2-user:ec2-user /data
```

---

## SSH into the instance (EICE)

```bash
# Regenerate key each session (60-second push window)
ssh-keygen -t ed25519 -N "" -f /tmp/eice-key -q <<< y

aws ec2-instance-connect send-ssh-public-key \
  --instance-id $INSTANCE_ID \
  --instance-os-user ec2-user \
  --ssh-public-key file:///tmp/eice-key.pub \
  --profile inewman-wsl --region us-west-2

ssh -i /tmp/eice-key \
  -o StrictHostKeyChecking=no \
  -o ProxyCommand='aws ec2-instance-connect open-tunnel \
    --instance-id '"$INSTANCE_ID"' \
    --profile inewman-wsl --region us-west-2' \
  ec2-user@$INSTANCE_ID
```

SCP a file to/from instance:
```bash
# Upload
scp -i /tmp/eice-key \
  -o ProxyCommand='aws ec2-instance-connect open-tunnel --instance-id '"$INSTANCE_ID"' --profile inewman-wsl --region us-west-2' \
  ./script.py ec2-user@$INSTANCE_ID:/home/ec2-user/

# Download
scp -i /tmp/eice-key \
  -o ProxyCommand='aws ec2-instance-connect open-tunnel --instance-id '"$INSTANCE_ID"' --profile inewman-wsl --region us-west-2' \
  ec2-user@$INSTANCE_ID:/data/output.png ./
```

---

## S3 buckets

All participants can create their own S3 buckets in `us-west-2`. **Prefer a
personal bucket over writing into the shared `scrippsresearch-hackathon`
bucket** — it keeps outputs organized, avoids naming collisions, and makes
cleanup easy.

### Create your bucket (do this once)
```bash
# Name format: scrippsresearch-<yourname>-hackathon
aws s3 mb s3://scrippsresearch-<yourname>-hackathon \
  --region us-west-2 --profile <profile>
```

Bucket names are globally unique — if the name is taken, add a short suffix
(e.g. `-2026` or your initials).

### Upload / download (from laptop)
```bash
aws s3 cp ./output.png s3://scrippsresearch-<yourname>-hackathon/output.png \
  --profile <profile> --region us-west-2

aws s3 cp s3://scrippsresearch-<yourname>-hackathon/output.png . \
  --profile <profile> --region us-west-2

# Sync an entire folder
aws s3 sync ./results/ s3://scrippsresearch-<yourname>-hackathon/results/ \
  --profile <profile> --region us-west-2
```

### From within EC2 (requires instance profile)
```bash
aws s3 cp /data/output.png s3://scrippsresearch-<yourname>-hackathon/output.png \
  --region us-west-2
# No --profile needed — credentials come from the instance metadata service
```

### Sharing your bucket with teammates

By default your bucket is private. To let other participants in the same
account read from it, add a bucket policy:

```bash
cat > /tmp/bucket-policy.json << 'EOF'
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "AllowHackathonAccountRead",
      "Effect": "Allow",
      "Principal": {
        "AWS": "arn:aws:iam::127696279288:root"
      },
      "Action": ["s3:GetObject", "s3:ListBucket"],
      "Resource": [
        "arn:aws:s3:::scrippsresearch-<yourname>-hackathon",
        "arn:aws:s3:::scrippsresearch-<yourname>-hackathon/*"
      ]
    }
  ]
}
EOF

aws s3api put-bucket-policy \
  --bucket scrippsresearch-<yourname>-hackathon \
  --policy file:///tmp/bucket-policy.json \
  --profile <profile> --region us-west-2
```

This grants read access to anyone in account `127696279288` (all hackathon
participants). They can then access your bucket with their own profile —
no credentials sharing needed:

```bash
aws s3 ls s3://scrippsresearch-<yourname>-hackathon/ --profile <their-profile>
```

To also allow teammates to write (e.g. a shared results bucket), add
`"s3:PutObject"` to the `Action` list.

---

## Accessing Amazon Open Data from EC2

No credentials required. Use `--no-sign-request` (CLI) or `UNSIGNED` config
(boto3).

```bash
# List SEA-AD PFC RNAseq files
aws s3 ls s3://sea-ad-single-cell-profiling/PFC/RNAseq/ \
  --no-sign-request --region us-west-2

# Download metadata CSV (1.3 GB)
aws s3 cp \
  s3://sea-ad-single-cell-profiling/PFC/RNAseq/SEAAD_A9_RNAseq_final-nuclei_metadata.2024-02-13.csv \
  /data/ --no-sign-request --region us-west-2

# Download full h5ad (35 GB — needs /data mounted)
aws s3 cp \
  s3://sea-ad-single-cell-profiling/PFC/RNAseq/SEAAD_A9_RNAseq_final-nuclei.2024-02-13.h5ad \
  /data/ --no-sign-request --region us-west-2
```

Python:
```python
import boto3
from botocore import UNSIGNED
from botocore.config import Config

s3 = boto3.client("s3", region_name="us-west-2",
                  config=Config(signature_version=UNSIGNED))
s3.download_file(
    "sea-ad-single-cell-profiling",
    "PFC/RNAseq/SEAAD_A9_RNAseq_final-nuclei_metadata.2024-02-13.csv",
    "/data/metadata.csv",
)
```

---

## Calling Bedrock from EC2 (requires instance profile)

Claude 4 models require an **inference profile ID** (with `us.` prefix).

### Active inference profile IDs

| Model | Profile ID |
|---|---|
| Claude Haiku 4.5 | `us.anthropic.claude-haiku-4-5-20251001-v1:0` |
| Claude Sonnet 4.5 | `us.anthropic.claude-sonnet-4-5-20250929-v1:0` |
| Claude Sonnet 4.6 | `us.anthropic.claude-sonnet-4-6` |
| Claude Opus 4.7 | `us.anthropic.claude-opus-4-7` |

```python
import boto3, json

bedrock = boto3.client("bedrock-runtime", region_name="us-west-2")

def ask_claude(prompt, model="us.anthropic.claude-haiku-4-5-20251001-v1:0",
               max_tokens=1024):
    resp = bedrock.invoke_model(
        modelId=model,
        contentType="application/json",
        accept="application/json",
        body=json.dumps({
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": max_tokens,
            "messages": [{"role": "user", "content": prompt}],
        }),
    )
    return json.loads(resp["body"].read())["content"][0]["text"]

print(ask_claude("Summarize this in one sentence: ..."))
```

Streaming:
```python
def ask_claude_stream(prompt, model="us.anthropic.claude-haiku-4-5-20251001-v1:0"):
    resp = bedrock.invoke_model_with_response_stream(
        modelId=model,
        contentType="application/json",
        accept="application/json",
        body=json.dumps({
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 2048,
            "messages": [{"role": "user", "content": prompt}],
        }),
    )
    for event in resp["body"]:
        chunk = json.loads(event["chunk"]["bytes"])
        if chunk.get("type") == "content_block_delta":
            print(chunk["delta"].get("text", ""), end="", flush=True)
    print()
```

---

## Terminate instance when done

```bash
aws ec2 terminate-instances --instance-ids $INSTANCE_ID \
  --profile inewman-wsl --region us-west-2
```

NAT gateway costs ~$0.045/hr + $0.045/GB processed — leave it running between
sessions (deleting/recreating would cost more in EIP reassignment and setup
time than the idle cost).

---

## Current task

$ARGUMENTS
