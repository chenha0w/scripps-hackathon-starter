#!/usr/bin/env python3
"""
Step 1: PBMC3k preprocessing with scanpy.
- Loads pbmc3k raw counts + pbmc3k_processed ground-truth labels
- Standard QC → normalise → log → HVG → PCA → UMAP → Leiden clustering
- Finds marker genes (rank_genes_groups) for zero-shot input
Outputs
-------
results/pbmc_processed.h5ad          – AnnData with clusters + ground truth
results/ground_truth_labels.csv      – per-cell barcode → ground truth label
results/top_markers_per_cluster.csv  – top 25 markers per cluster
results/timing_01_preprocessing.csv  – wall time + peak memory
"""

import os, time, tracemalloc
import numpy as np
import pandas as pd
import scanpy as sc
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

tracemalloc.start()
t0 = time.time()

RESULTS = "results"
os.makedirs(f"{RESULTS}/plots", exist_ok=True)

sc.settings.verbosity = 1
sc.settings.figdir    = f"{RESULTS}/plots"

print("=== Step 1: Preprocessing ===")
print(f"scanpy version: {sc.__version__}")

# ── Load data ─────────────────────────────────────────────────────────────────
print("\nLoading pbmc3k (raw)...")
adata = sc.datasets.pbmc3k()                 # 2700 cells × 32738 genes, raw counts

print("Loading pbmc3k_processed (ground truth)...")
adata_ref = sc.datasets.pbmc3k_processed()   # louvain = curated cell-type labels

# Save ground truth labels (barcode → label mapping)
gt = adata_ref.obs[["louvain"]].copy()
gt.index.name = "cell_barcode"
gt = gt.rename(columns={"louvain": "ground_truth"})
gt.to_csv(f"{RESULTS}/ground_truth_labels.csv")
print(f"Ground truth cell types: {sorted(gt['ground_truth'].unique())}")
print(f"Ground truth cells: {len(gt)}")

# ── QC ────────────────────────────────────────────────────────────────────────
sc.pp.filter_cells(adata, min_genes=200)
sc.pp.filter_genes(adata, min_cells=3)
adata.var["mt"] = adata.var_names.str.startswith("MT-")
sc.pp.calculate_qc_metrics(adata, qc_vars=["mt"], percent_top=None,
                            log1p=False, inplace=True)
adata = adata[adata.obs.n_genes_by_counts < 2500].copy()
adata = adata[adata.obs.pct_counts_mt < 5].copy()
print(f"\nCells after QC: {adata.n_obs}")

# Attach ground truth to the cells we kept (for reference only – not used for annotation)
shared = adata.obs_names.intersection(gt.index)
adata.obs["ground_truth"] = "Unknown"
adata.obs.loc[shared, "ground_truth"] = gt.loc[shared, "ground_truth"]
print(f"Cells matched to ground truth: {(adata.obs['ground_truth'] != 'Unknown').sum()}")

# ── Normalise & log ───────────────────────────────────────────────────────────
sc.pp.normalize_total(adata, target_sum=1e4)
sc.pp.log1p(adata)
adata.raw = adata           # store log-normalised for DE & CellTypist

sc.pp.highly_variable_genes(adata, min_mean=0.0125, max_mean=3,
                              min_disp=0.5)
adata = adata[:, adata.var.highly_variable].copy()
sc.pp.scale(adata, max_value=10)

# ── Dimensionality reduction & clustering ─────────────────────────────────────
sc.tl.pca(adata, svd_solver="arpack", n_comps=50)
sc.pp.neighbors(adata, n_neighbors=10, n_pcs=40)
sc.tl.umap(adata)
sc.tl.leiden(adata, resolution=0.5, key_added="leiden")

n_clusters = adata.obs["leiden"].nunique()
print(f"Leiden clusters: {n_clusters}")
print(adata.obs["leiden"].value_counts().sort_index().to_string())

# ── UMAP plots ────────────────────────────────────────────────────────────────
fig, axes = plt.subplots(1, 2, figsize=(14, 5))
sc.pl.umap(adata, color="leiden",        legend_loc="on data",
           title="Leiden Clusters",      ax=axes[0], show=False)
sc.pl.umap(adata, color="ground_truth",  legend_loc="right margin",
           title="Ground Truth Labels",  ax=axes[1], show=False)
fig.tight_layout()
fig.savefig(f"{RESULTS}/plots/umap_clusters_gt.png", dpi=150)
plt.close()

# ── Marker genes ──────────────────────────────────────────────────────────────
print("\nFinding marker genes (Wilcoxon)...")
sc.tl.rank_genes_groups(adata, "leiden", method="wilcoxon", key_added="rank_genes")

rows = []
for cluster in sorted(adata.obs["leiden"].unique(), key=int):
    group_result = sc.get.rank_genes_groups_df(adata, group=cluster,
                                                key="rank_genes",
                                                pval_cutoff=0.05,
                                                log2fc_min=0.25)
    group_result = group_result.head(25).copy()
    group_result["cluster"] = int(cluster)
    rows.append(group_result)

markers_df = pd.concat(rows, ignore_index=True)
markers_df = markers_df.rename(columns={"names": "gene", "logfoldchanges": "avg_log2FC"})
markers_df.to_csv(f"{RESULTS}/top_markers_per_cluster.csv", index=False)

top5 = (markers_df.sort_values("avg_log2FC", ascending=False)
        .groupby("cluster")
        .head(5)
        .groupby("cluster")["gene"]
        .apply(lambda g: ", ".join(g)))
print("Top 5 markers per cluster:")
print(top5.to_string())

# ── Save ──────────────────────────────────────────────────────────────────────
adata.write_h5ad(f"{RESULTS}/pbmc_processed.h5ad")
print(f"\nSaved: {RESULTS}/pbmc_processed.h5ad")

# ── Timing ────────────────────────────────────────────────────────────────────
elapsed = time.time() - t0
cur, peak = tracemalloc.get_traced_memory(); tracemalloc.stop()
pd.DataFrame([{
    "step": "01_preprocessing",
    "wall_time_sec": round(elapsed, 2),
    "peak_mem_mb":   round(peak / 1024**2, 1),
}]).to_csv(f"{RESULTS}/timing_01_preprocessing.csv", index=False)
print(f"\nDone. Wall time: {elapsed:.1f} s | Peak mem: {peak/1024**2:.1f} MB")
