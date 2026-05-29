# zero_shot_annotation.py  (Gemma-generated)
# Gemma's approach: per-cell marker gene scoring — sum expression of each cell
# type's marker genes, assign the cell type with the highest cumulative score.
#
# Fixes applied:
#   - Gemma used mouse gene names (Cd79a, Cd3e); fixed to human (CD79A, CD3E)
#   - Gemma's loop `for cell_type_scores in cell_type_scores.values()` shadowed
#     the outer dict, making every cell get the same label; fixed to per-cell argmax
#   - Added standard preprocessing (Gemma omitted it but it's required before scoring)
#   - Added memory + time tracking (Gemma said 'use psutil' but left it out)

import time, tracemalloc
import numpy as np
import pandas as pd
import scanpy as sc
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy.sparse import issparse
from config import RESULTS_DIR, OUTPUT_PREFIX
from download_data import download_data

# Gemma's marker gene dictionary (human gene names)
MARKER_GENES = {
    "B cells":           ["CD79A", "CD19", "MS4A1", "CD79B"],
    "T cells":           ["CD3E", "CD8A", "CD4", "CD3D"],
    "Monocytes":         ["CD14", "LYZ", "S100A9", "S100A8"],
    "NK cells":          ["NKG7", "KLRC1", "GNLY", "KLRD1"],
    "Dendritic cells":   ["FCER1A", "CST3", "CLEC10A", "HLA-DQA1"],
}

def preprocess(adata):
    sc.pp.filter_cells(adata, min_genes=200)
    sc.pp.filter_genes(adata, min_cells=3)
    adata.var["mt"] = adata.var_names.str.startswith("MT-")
    sc.pp.calculate_qc_metrics(adata, qc_vars=["mt"], percent_top=None,
                                log1p=False, inplace=True)
    adata = adata[adata.obs.n_genes_by_counts < 2500].copy()
    adata = adata[adata.obs.pct_counts_mt < 5].copy()
    sc.pp.normalize_total(adata, target_sum=1e4)
    sc.pp.log1p(adata)
    adata.raw = adata
    sc.pp.highly_variable_genes(adata, min_mean=0.0125, max_mean=3, min_disp=0.5)
    adata_hvg = adata[:, adata.var.highly_variable].copy()
    sc.pp.scale(adata_hvg, max_value=10)
    sc.tl.pca(adata_hvg, svd_solver="arpack")
    sc.pp.neighbors(adata_hvg, n_neighbors=10, n_pcs=40)
    sc.tl.umap(adata_hvg)
    sc.tl.leiden(adata_hvg, resolution=0.5, key_added="leiden")
    adata.obs["leiden"] = adata_hvg.obs["leiden"]
    adata.obsm["X_umap"] = adata_hvg.obsm["X_umap"]
    return adata

def zero_shot_annotate(adata):
    """Gemma's per-cell marker scoring approach."""
    scores = {}
    for cell_type, markers in MARKER_GENES.items():
        valid = [g for g in markers if g in adata.var_names]
        if valid:
            X = adata[:, valid].X
            arr = X.toarray() if issparse(X) else np.array(X)
            # Gemma: sum expression of marker genes per cell
            scores[cell_type] = arr.sum(axis=1)
        else:
            scores[cell_type] = np.zeros(adata.n_obs)

    score_matrix = np.column_stack(list(scores.values()))
    cell_types    = list(scores.keys())
    # Assign each cell to the cell type with the highest cumulative marker score
    predicted = [cell_types[i] for i in np.argmax(score_matrix, axis=1)]
    adata.obs["zero_shot_annotation"] = predicted
    return adata

if __name__ == "__main__":
    tracemalloc.start()
    t0 = time.time()

    adata, _ = download_data()
    adata     = preprocess(adata)
    adata     = zero_shot_annotate(adata)

    elapsed  = time.time() - t0
    cur, peak = tracemalloc.get_traced_memory(); tracemalloc.stop()

    print("\nZero-shot annotation distribution:")
    print(adata.obs["zero_shot_annotation"].value_counts().to_string())
    print(f"\nTime: {elapsed:.1f}s  |  Peak mem: {peak/1024**2:.1f} MB")

    # Save
    out = adata.obs[["leiden", "zero_shot_annotation"]].copy()
    out.index.name = "cell_barcode"
    out.to_csv(f"{RESULTS_DIR}/zero_shot_annotations.csv")
    adata.write_h5ad(f"{OUTPUT_PREFIX}_zero_shot.h5ad")

    pd.DataFrame([{"step": "zero_shot_gemma", "wall_time_sec": round(elapsed, 2),
                   "peak_mem_mb": round(peak/1024**2, 1)}]).to_csv(
        f"{RESULTS_DIR}/timing_zero_shot.csv", index=False)

    # Save the preprocessed adata for next steps
    adata.write_h5ad(f"{RESULTS_DIR}/pbmc_preprocessed.h5ad")
    print("Zero-shot annotation completed.")
