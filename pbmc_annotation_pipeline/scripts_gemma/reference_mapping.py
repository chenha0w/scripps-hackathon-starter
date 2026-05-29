# reference_mapping.py  (Gemma-generated)
# Gemma's approach: Scanorama integration + k-nearest-neighbour label transfer.
#
# Fixes applied:
#   - scanorama.integrate() API takes list-of-matrices + list-of-gene-lists, not keyword 'framework'
#   - Label transfer: Gemma's distance formula broadcast incorrectly; fixed with proper KNN
#   - Reference label key: pbmc68k uses 'bulk_labels', not 'cell_type'
#   - Added memory + time tracking

import time, tracemalloc
import numpy as np
import pandas as pd
import scanpy as sc
import scanorama
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy.sparse import issparse
from sklearn.neighbors import KNeighborsClassifier
from config import RESULTS_DIR, OUTPUT_PREFIX
from download_data import download_data

def reference_map(adata, ref_adata):
    """Gemma's Scanorama integration + KNN label transfer."""

    # Find common genes
    common = list(adata.var_names.intersection(ref_adata.var_names))
    print(f"Common genes: {len(common)}")
    adata_c   = adata[:, common].copy()
    ref_c     = ref_adata[:, common].copy()

    # Normalise reference to same scale as test data
    sc.pp.normalize_total(ref_c, target_sum=1e4)
    sc.pp.log1p(ref_c)

    X_test = adata_c.X.toarray() if issparse(adata_c.X) else np.array(adata_c.X)
    X_ref  = ref_c.X.toarray()  if issparse(ref_c.X)  else np.array(ref_c.X)
    # Replace NaN/Inf that arise from log1p on cells with zero counts
    X_test = np.nan_to_num(X_test, nan=0.0, posinf=0.0)
    X_ref  = np.nan_to_num(X_ref,  nan=0.0, posinf=0.0)

    # Gemma: integrate data using Scanorama
    print("Running Scanorama integration...")
    integrated, genes = scanorama.integrate(
        [X_test, X_ref],
        [common, common],
    )
    adata.obsm["X_scanorama"]   = integrated[0]
    ref_adata.obsm["X_scanorama"] = integrated[1]

    # Label transfer via KNN (Gemma's nearest-neighbour approach)
    print("Transferring labels via KNN (k=5)...")
    knn = KNeighborsClassifier(n_neighbors=5, metric="euclidean")
    knn.fit(ref_adata.obsm["X_scanorama"], ref_adata.obs["bulk_labels"])
    predicted = knn.predict(adata.obsm["X_scanorama"])
    adata.obs["reference_annotation"] = predicted
    return adata

if __name__ == "__main__":
    tracemalloc.start()
    t0 = time.time()

    adata     = sc.read_h5ad(f"{RESULTS_DIR}/pbmc_preprocessed.h5ad")
    _, ref_adata = download_data()
    adata     = reference_map(adata, ref_adata)

    elapsed  = time.time() - t0
    cur, peak = tracemalloc.get_traced_memory(); tracemalloc.stop()

    print("\nReference annotation distribution:")
    print(adata.obs["reference_annotation"].value_counts().to_string())
    print(f"\nTime: {elapsed:.1f}s  |  Peak mem: {peak/1024**2:.1f} MB")

    out = adata.obs[["leiden", "reference_annotation"]].copy()
    out.index.name = "cell_barcode"
    out.to_csv(f"{RESULTS_DIR}/reference_annotations.csv")
    adata.write_h5ad(f"{OUTPUT_PREFIX}_reference_mapping.h5ad")

    pd.DataFrame([{"step": "reference_mapping_gemma", "wall_time_sec": round(elapsed, 2),
                   "peak_mem_mb": round(peak/1024**2, 1)}]).to_csv(
        f"{RESULTS_DIR}/timing_reference.csv", index=False)
    print("Reference mapping completed.")
