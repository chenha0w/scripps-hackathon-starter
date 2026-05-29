#!/usr/bin/env python3
"""
Step 2: Zero-shot cell-type annotation via Claude Sonnet 4 on AWS Bedrock.

No reference dataset is used — Claude annotates purely from its pre-trained
knowledge of PBMC marker genes.

Input : results/top_markers_per_cluster.csv
Output: results/zero_shot_annotations.csv      – cluster → cell type
        results/zero_shot_llm_response.txt     – raw LLM response (for review)
        results/timing_02_zero_shot.csv
"""

import boto3, json, os, re, time, tracemalloc
import pandas as pd
from botocore.exceptions import ClientError

tracemalloc.start()
t0 = time.time()

REGION   = "us-west-2"
MODEL_ID = "us.anthropic.claude-haiku-4-5-20251001-v1:0"
RESULTS  = "results"
PROFILE  = os.environ.get("AWS_PROFILE", "chewu-scripps")

print("=== Step 2: Zero-Shot LLM Annotation ===")
print(f"Model  : {MODEL_ID}")
print(f"Region : {REGION}")

# ── Bedrock client ────────────────────────────────────────────────────────────
# On EC2 with hackathon-ec2-profile → uses instance role automatically.
# Locally → falls back to SSO profile.
try:
    session = boto3.Session(profile_name=PROFILE, region_name=REGION)
    session.client("sts").get_caller_identity()   # validate profile
    print(f"Auth   : AWS SSO profile '{PROFILE}'")
except Exception:
    session = boto3.Session(region_name=REGION)
    print("Auth   : EC2 instance role")

bedrock = session.client("bedrock-runtime")

# ── Load marker genes ─────────────────────────────────────────────────────────
df = pd.read_csv(f"{RESULTS}/top_markers_per_cluster.csv")
clusters = sorted(df["cluster"].unique())
print(f"\nClusters: {clusters}")

cluster_genes: dict[str, list[str]] = {}
for c in clusters:
    sub = (df[df["cluster"] == c]
           .sort_values("avg_log2FC", ascending=False)
           .head(20))
    cluster_genes[str(c)] = sub["gene"].tolist()

print("\nMarker genes sent to LLM:")
for cid, genes in cluster_genes.items():
    print(f"  Cluster {cid}: {', '.join(genes[:8])} ...")

# ── Prompt ────────────────────────────────────────────────────────────────────
SYSTEM = (
    "You are an expert single-cell biologist specialising in PBMC (peripheral "
    "blood mononuclear cell) transcriptomics. You will receive top marker genes "
    "for each Leiden cluster from a PBMC scRNA-seq experiment and must assign "
    "the most likely cell type using standard PBMC nomenclature.\n\n"
    "Use ONLY these canonical PBMC label names (pick exactly one per cluster):\n"
    "  Naive CD4 T | Memory CD4 T | CD8 T | NK | B | "
    "CD14+ Mono | FCGR3A+ Mono | DC | Platelet\n\n"
    "Respond with ONLY a valid JSON object mapping cluster IDs (strings) to "
    "cell type labels. No explanation, no markdown — pure JSON."
)

lines = [
    f"Cluster {cid}: {', '.join(genes[:15])}"
    for cid, genes in cluster_genes.items()
]
USER = (
    f"Annotate these {len(clusters)} PBMC clusters based on their marker genes:\n\n"
    + "\n".join(lines)
    + "\n\nReturn JSON only."
)

# ── Invoke Bedrock ────────────────────────────────────────────────────────────
body = {
    "anthropic_version": "bedrock-2023-05-31",
    "max_tokens": 512,
    "temperature": 0.0,
    "system": SYSTEM,
    "messages": [{"role": "user", "content": USER}],
}

print("\nCalling Claude via Bedrock...")
for attempt in range(3):
    try:
        resp   = bedrock.invoke_model(
            modelId=MODEL_ID, body=json.dumps(body),
            contentType="application/json", accept="application/json",
        )
        raw    = json.loads(resp["body"].read())["content"][0]["text"].strip()
        print(f"  Attempt {attempt+1}: success")
        break
    except ClientError as e:
        code = e.response["Error"]["Code"]
        print(f"  Attempt {attempt+1} failed ({code}). Retrying in 5 s...")
        if attempt == 2:
            raise
        time.sleep(5)

# ── Save raw response ─────────────────────────────────────────────────────────
with open(f"{RESULTS}/zero_shot_llm_response.txt", "w") as fh:
    fh.write("=== SYSTEM PROMPT ===\n")
    fh.write(SYSTEM + "\n\n")
    fh.write("=== USER PROMPT ===\n")
    fh.write(USER + "\n\n")
    fh.write("=== RAW LLM RESPONSE ===\n")
    fh.write(raw + "\n")

print(f"\nRaw response:\n{raw}")

# ── Parse JSON ────────────────────────────────────────────────────────────────
m = re.search(r"\{[^{}]+\}", raw, re.DOTALL)
annotations: dict[str, str] = json.loads(m.group() if m else raw)

print("\nParsed annotations:")
for cid, label in sorted(annotations.items(), key=lambda x: int(x[0])):
    genes_preview = ", ".join(cluster_genes.get(cid, [])[:5])
    print(f"  Cluster {cid}: {label:<20}  (markers: {genes_preview})")

# ── Save ──────────────────────────────────────────────────────────────────────
out = pd.DataFrame([
    {"cluster": int(k), "zero_shot_annotation": v}
    for k, v in annotations.items()
]).sort_values("cluster").reset_index(drop=True)

out.to_csv(f"{RESULTS}/zero_shot_annotations.csv", index=False)
print(f"\nSaved: {RESULTS}/zero_shot_annotations.csv")

# ── Timing ────────────────────────────────────────────────────────────────────
elapsed = time.time() - t0
cur, peak = tracemalloc.get_traced_memory(); tracemalloc.stop()
pd.DataFrame([{
    "step": "02_zero_shot_llm",
    "wall_time_sec": round(elapsed, 2),
    "peak_mem_mb":   round(peak / 1024**2, 1),
}]).to_csv(f"{RESULTS}/timing_02_zero_shot.csv", index=False)
print(f"\nDone. Wall time: {elapsed:.1f} s | Peak mem: {peak/1024**2:.1f} MB")
