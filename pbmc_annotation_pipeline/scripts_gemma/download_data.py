# download_data.py  (Gemma-generated)
# Fixes: Gemma assumed S3 URLs for both datasets; using scanpy.datasets instead.
import scanpy as sc
import pandas as pd
import os
from config import RESULTS_DIR, EXISTING_ANNOTATION_KEY

def download_data():
    print("Loading PBMC dataset (pbmc3k raw)...")
    adata = sc.datasets.pbmc3k()

    print("Loading reference dataset (pbmc68k_reduced)...")
    # Gemma said 'Mouse Brain Cell Atlas' — wrong for PBMC.
    # Using pbmc68k_reduced: a different 10x PBMC dataset with 9 characterised cell types.
    ref_adata = sc.datasets.pbmc68k_reduced()

    # Save ground truth from pbmc3k_processed (for comparison at the end)
    print("Loading ground truth annotations from pbmc3k_processed...")
    adata_gt = sc.datasets.pbmc3k_processed()
    gt = adata_gt.obs[[EXISTING_ANNOTATION_KEY]].copy()
    gt.index.name = "cell_barcode"
    gt = gt.rename(columns={EXISTING_ANNOTATION_KEY: "ground_truth"})
    gt.to_csv(f"{RESULTS_DIR}/ground_truth_labels.csv")
    print(f"Ground truth cell types: {sorted(gt['ground_truth'].unique())}")

    print(f"PBMC dataset: {adata.shape}")
    print(f"Reference dataset: {ref_adata.shape}")
    print(f"Reference cell types: {sorted(ref_adata.obs['bulk_labels'].unique())}")
    return adata, ref_adata

if __name__ == "__main__":
    adata, ref_adata = download_data()
    print("Data downloaded successfully.")
