# main.py  (Gemma-generated)
# Orchestrates the full pipeline and uploads results to S3.
# Gemma's structure: run each script via subprocess with timing.
# Fixes: use importlib instead of subprocess to share data in-process;
#        add psutil memory tracking Gemma mentioned but left out.

import time, glob, os
import pandas as pd
import boto3
from config import S3_BUCKET, AWS_PROFILE, AWS_REGION, RESULTS_DIR

s3 = boto3.Session(profile_name=AWS_PROFILE,
                   region_name=AWS_REGION).client("s3")

def run_step(name, fn):
    print(f"\n{'─'*55}")
    print(f"  {name}")
    print(f"{'─'*55}")
    t0 = time.time()
    result = fn()
    elapsed = time.time() - t0
    print(f"  ✓ Done in {elapsed:.1f}s")
    return result

if __name__ == "__main__":
    print("=" * 55)
    print("  Gemma-Generated PBMC Annotation Pipeline")
    print("=" * 55)

    # Import modules in-process (Gemma used subprocess; avoided here to share state)
    import sys
    sys.path.insert(0, os.path.dirname(__file__))

    from download_data       import download_data
    from zero_shot_annotation import preprocess, zero_shot_annotate, MARKER_GENES
    from reference_mapping   import reference_map
    from compare_annotations import compare_annotations
    import scanpy as sc
    import numpy as np

    # Step 1: Download / load data
    adata, ref_adata = run_step("Step 1: Load Data", download_data)

    # Step 2: Preprocess + zero-shot annotation
    import tracemalloc
    tracemalloc.start()
    t0 = time.time()
    adata = preprocess(adata)
    adata = zero_shot_annotate(adata)
    elapsed_zs = time.time() - t0
    cur, peak_zs = tracemalloc.get_traced_memory(); tracemalloc.stop()
    print(f"\nZero-shot: {elapsed_zs:.1f}s | peak {peak_zs/1024**2:.1f} MB")

    out = adata.obs[["leiden","zero_shot_annotation"]].copy()
    out.index.name = "cell_barcode"
    out.to_csv(f"{RESULTS_DIR}/zero_shot_annotations.csv")
    adata.write_h5ad(f"{RESULTS_DIR}/pbmc_preprocessed.h5ad")
    pd.DataFrame([{"step":"zero_shot_gemma",
                   "wall_time_sec":round(elapsed_zs,2),
                   "peak_mem_mb":round(peak_zs/1024**2,1)}]).to_csv(
        f"{RESULTS_DIR}/timing_zero_shot.csv", index=False)

    # Step 3: Reference mapping (Scanorama + KNN)
    tracemalloc.start()
    t0 = time.time()
    adata = reference_map(adata, ref_adata)
    elapsed_ref = time.time() - t0
    cur, peak_ref = tracemalloc.get_traced_memory(); tracemalloc.stop()
    print(f"\nReference mapping: {elapsed_ref:.1f}s | peak {peak_ref/1024**2:.1f} MB")

    out = adata.obs[["leiden","reference_annotation"]].copy()
    out.index.name = "cell_barcode"
    out.to_csv(f"{RESULTS_DIR}/reference_annotations.csv")
    adata.write_h5ad(f"{RESULTS_DIR}/pbmc_annotation_reference_mapping.h5ad")
    pd.DataFrame([{"step":"reference_mapping_gemma",
                   "wall_time_sec":round(elapsed_ref,2),
                   "peak_mem_mb":round(peak_ref/1024**2,1)}]).to_csv(
        f"{RESULTS_DIR}/timing_reference.csv", index=False)

    # Step 4: Compare annotations + metrics
    run_step("Step 4: Compare & Evaluate", compare_annotations)

    # Step 5: Upload to S3
    print(f"\n{'─'*55}")
    print(f"  Step 5: Upload to S3")
    print(f"{'─'*55}")
    for fpath in glob.glob(f"{RESULTS_DIR}/**/*", recursive=True):
        if os.path.isfile(fpath) and not fpath.endswith(".h5ad"):
            s3_key = fpath.replace(RESULTS_DIR, "results_gemma")
            s3.upload_file(fpath, S3_BUCKET, s3_key)
            print(f"  → s3://{S3_BUCKET}/{s3_key}")

    print(f"\n{'='*55}")
    print("  Pipeline complete.")
    print(f"  Results: {RESULTS_DIR}/  and  s3://{S3_BUCKET}/results_gemma/")
    print(f"{'='*55}")
