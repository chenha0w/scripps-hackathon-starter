#!/usr/bin/env python3
"""
Step 3: Reference-based annotation using CellTypist.

Reference: CellTypist 'Immune_All_High' model — trained on >700 k cells from
20+ curated human immune datasets (NOT the PBMC3k dataset).
Source: Domínguez-Conde et al., Science 2022.

majority_voting=True aggregates per-cell scores to the cluster (Leiden) level,
which mirrors how the zero-shot method works and makes the comparison fair.

Input : results/pbmc_processed.h5ad
Output: results/reference_mapping_annotations.csv   – per-cell annotations
        results/timing_03_reference_mapping.csv
"""

import os, time, tracemalloc
import numpy as np
import pandas as pd
import scanpy as sc
import celltypist
from celltypist import models
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

tracemalloc.start()
t0 = time.time()

RESULTS = "results"
MODEL   = "Immune_All_High.pkl"   # 31-label high-res pan-immune model

print("=== Step 3: Reference Mapping (CellTypist) ===")
print(f"Reference model : {MODEL}")
print(f"celltypist v    : {celltypist.__version__}")

# ── Load processed data ───────────────────────────────────────────────────────
print("\nLoading pbmc_processed.h5ad...")
adata = sc.read_h5ad(f"{RESULTS}/pbmc_processed.h5ad")
print(f"Cells: {adata.n_obs}  |  Leiden clusters: {adata.obs['leiden'].nunique()}")

# CellTypist expects log-normalised counts; use adata.raw which was stored before HVG
adata_full = adata.raw.to_adata()
adata_full.obs["leiden"] = adata.obs["leiden"]

# ── Download model ────────────────────────────────────────────────────────────
print(f"\nDownloading/checking CellTypist model: {MODEL}")
models.download_models(force_update=False, model=[MODEL])

# ── Run CellTypist ────────────────────────────────────────────────────────────
print("Running CellTypist annotation (majority voting over Leiden clusters)...")
t_ct = time.time()
predictions = celltypist.annotate(
    adata_full,
    model            = MODEL,
    majority_voting  = True,
    over_clustering  = "leiden",   # use our Leiden clusters for majority vote
)
print(f"CellTypist finished in {time.time()-t_ct:.1f} s")

# ── Extract results ───────────────────────────────────────────────────────────
pred_df = predictions.predicted_labels   # columns: predicted_labels, over_clustering, majority_voting
adata_full.obs["celltypist_cell"]    = pred_df["predicted_labels"].values
adata_full.obs["celltypist_cluster"] = pred_df["majority_voting"].values

# Use majority-voted cluster label as the reference annotation (cluster-level,
# same granularity as zero-shot LLM output)
adata.obs["reference_annotation"] = adata_full.obs["celltypist_cluster"]
adata.obs["reference_cell_level"] = adata_full.obs["celltypist_cell"]
adata.obs["reference_conf"]       = predictions.probability_matrix.max(axis=1).values

print("\nAnnotation distribution (majority voting per cluster):")
print(adata.obs["reference_annotation"].value_counts().to_string())
print("\nAnnotation distribution (per cell):")
print(adata.obs["reference_cell_level"].value_counts().to_string())

# ── Cluster-level summary ─────────────────────────────────────────────────────
cluster_summary = (
    adata.obs.groupby("leiden")
    .agg(
        reference_annotation = ("reference_annotation", "first"),
        reference_cell_level = ("reference_cell_level", lambda x: x.mode()[0]),
        mean_conf            = ("reference_conf", "mean"),
        n_cells              = ("reference_annotation", "count"),
    )
    .reset_index()
    .sort_values("leiden", key=lambda s: s.astype(int))
)
cluster_summary.to_csv(f"{RESULTS}/cluster_reference_annotations.csv", index=False)
print("\nCluster-level annotations:")
print(cluster_summary[["leiden","reference_annotation","n_cells"]].to_string(index=False))

# ── Save per-cell results ─────────────────────────────────────────────────────
out = adata.obs[["leiden", "ground_truth",
                 "reference_annotation", "reference_cell_level",
                 "reference_conf"]].copy()
out.index.name = "cell_barcode"
out.to_csv(f"{RESULTS}/reference_mapping_annotations.csv")
print(f"\nSaved: {RESULTS}/reference_mapping_annotations.csv")

# ── UMAP plots ────────────────────────────────────────────────────────────────
fig, axes = plt.subplots(1, 2, figsize=(16, 5))
sc.pl.umap(adata, color="reference_annotation",
           title="CellTypist — Majority Vote (cluster)",
           legend_loc="right margin", ax=axes[0], show=False)
sc.pl.umap(adata, color="reference_cell_level",
           title="CellTypist — Per Cell",
           legend_loc="right margin", ax=axes[1], show=False)
fig.tight_layout()
fig.savefig(f"{RESULTS}/plots/umap_celltypist.png", dpi=150)
plt.close()

# ── Timing ────────────────────────────────────────────────────────────────────
elapsed = time.time() - t0
cur, peak = tracemalloc.get_traced_memory(); tracemalloc.stop()
pd.DataFrame([{
    "step": "03_reference_mapping",
    "wall_time_sec": round(elapsed, 2),
    "peak_mem_mb":   round(peak / 1024**2, 1),
}]).to_csv(f"{RESULTS}/timing_03_reference_mapping.csv", index=False)
print(f"\nDone. Wall time: {elapsed:.1f} s | Peak mem: {peak/1024**2:.1f} MB")
