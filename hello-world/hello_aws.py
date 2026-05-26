"""hello_aws.py — round-trip smoke test against the hackathon AWS account.

Verifies that:

  1. Your AWS SSO profile is configured and the token is valid.
  2. You can list buckets in `us-west-2`.
  3. You can read from the public SEA-AD Open Data bucket (no creds).
  4. You can call Claude on Bedrock through the hackathon's inference
     profile.

Run from the repo root, after `aws sso login`:

    python hello-world/hello_aws.py --profile <your-profile>

If a step fails, the script tells you which one and what to try next.
This is intentionally chatty — it's a teaching exercise, not production
code.
"""

from __future__ import annotations

import argparse
import json
import sys

# On Windows, Python's default stdout encoding (cp1252) mangles common
# characters like em-dashes and smart quotes. Force UTF-8 so Claude's
# greeting renders correctly. No-op on macOS/Linux.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

try:
    import boto3
    from botocore import UNSIGNED
    from botocore.config import Config
    from botocore.exceptions import (
        BotoCoreError,
        ClientError,
        NoCredentialsError,
        ProfileNotFound,
    )
except ImportError:
    print("This script needs boto3. Install it with:")
    print("    pip install boto3")
    sys.exit(1)


REGION = "us-west-2"
ACCOUNT_ID = "127696279288"
OPEN_DATA_BUCKET = "sea-ad-single-cell-profiling"
OPEN_DATA_PREFIX = "PFC/RNAseq/"
BEDROCK_MODEL = "us.anthropic.claude-haiku-4-5-20251001-v1:0"


def step(num: int, title: str) -> None:
    print(f"\n==> Step {num}  {title}")


def ok(msg: str) -> None:
    print(f"    [PASS] {msg}")


def bad(msg: str, hint: str | None = None) -> None:
    print(f"    [FAIL] {msg}")
    if hint:
        print(f"           hint: {hint}")


def main(profile: str) -> int:
    failures = 0

    # ---------- Step 1: SSO session is valid ----------
    step(1, "Verify SSO session and identity")
    try:
        session = boto3.Session(profile_name=profile, region_name=REGION)
        sts = session.client("sts")
        ident = sts.get_caller_identity()
    except ProfileNotFound:
        bad(
            f"profile '{profile}' is not configured",
            "run `aws configure sso` (see AWS_SETUP.md step 2)",
        )
        return 1
    except (ClientError, NoCredentialsError) as e:
        bad(
            f"could not get caller identity: {e}",
            f"run `aws sso login --profile {profile}`",
        )
        return 1

    if ident.get("Account") != ACCOUNT_ID:
        bad(
            f"unexpected account: {ident.get('Account')} (expected {ACCOUNT_ID})",
            "double-check that your profile points at the hackathon account",
        )
        failures += 1
    else:
        ok(f"identity: {ident.get('Arn', '?')}")

    # ---------- Step 2: List your buckets ----------
    step(2, "List S3 buckets you own in this account")
    try:
        s3 = session.client("s3")
        resp = s3.list_buckets()
        names = [b["Name"] for b in resp.get("Buckets", [])]
        if names:
            shown = names[:5]
            extra = f" (+{len(names) - 5} more)" if len(names) > 5 else ""
            ok(f"found {len(names)} bucket(s): {', '.join(shown)}{extra}")
        else:
            ok("no buckets yet — that's fine, you can create one later")
    except (ClientError, BotoCoreError) as e:
        bad(f"list-buckets failed: {e}")
        failures += 1

    # ---------- Step 3: Read from Amazon Open Data (no creds) ----------
    step(3, "Read from Amazon Open Data (unsigned)")
    try:
        anon = boto3.client("s3", region_name=REGION,
                            config=Config(signature_version=UNSIGNED))
        listing = anon.list_objects_v2(
            Bucket=OPEN_DATA_BUCKET, Prefix=OPEN_DATA_PREFIX, MaxKeys=3
        )
        keys = [obj["Key"] for obj in listing.get("Contents", [])]
        if keys:
            ok(f"sample SEA-AD keys: {keys[0]}")
        else:
            bad("listing returned no objects", "the prefix may have changed")
            failures += 1
    except (ClientError, BotoCoreError) as e:
        bad(f"open-data list failed: {e}")
        failures += 1

    # ---------- Step 4: Ask Claude via Bedrock ----------
    step(4, "Ask Claude (Bedrock) to say hello")
    try:
        bedrock = session.client("bedrock-runtime")
        body = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 120,
            "messages": [
                {
                    "role": "user",
                    "content": (
                        "Greet a new participant of the Scripps Research "
                        "CBB Hackathon in one sentence. Be warm but brief."
                    ),
                }
            ],
        }
        resp = bedrock.invoke_model(
            modelId=BEDROCK_MODEL,
            contentType="application/json",
            accept="application/json",
            body=json.dumps(body),
        )
        payload = json.loads(resp["body"].read())
        text = payload["content"][0]["text"].strip()
        ok("Claude says:")
        for line in text.splitlines():
            print(f"           {line}")
    except (ClientError, BotoCoreError) as e:
        bad(
            f"Bedrock invoke failed: {e}",
            "your role may not have Bedrock access yet — ask the hackathon admin",
        )
        failures += 1

    # ---------- Summary ----------
    print()
    if failures:
        print(f"Done — {failures} step(s) failed. See messages above.")
        return 1
    print("Done — all steps passed. Your AWS setup is hackathon-ready.")
    return 0


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "--profile",
        default="bgood-scripps",
        help="AWS SSO profile name (matches the one in test_skill.sh).",
    )
    args = p.parse_args()
    sys.exit(main(args.profile))
