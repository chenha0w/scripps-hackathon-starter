# config.py  (Gemma-generated)
# Fixes applied:
#   - DATA_SOURCE: Gemma assumed an S3 file; using scanpy.datasets.pbmc3k() instead
#   - REFERENCE_DATA_SOURCE: Gemma suggested Mouse Brain Cell Atlas (wrong for PBMC);
#     replaced with pbmc68k_reduced (a different, well-characterised PBMC dataset)
#   - Marker genes: Gemma used mouse gene names (Cd79a); fixed to human (CD79A)

DATA_SOURCE           = "scanpy"                      # load via sc.datasets.pbmc3k()
REFERENCE_DATA_SOURCE = "scanpy_pbmc68k"              # load via sc.datasets.pbmc68k_reduced()
S3_BUCKET             = "scrippsresearch-chewu-hackathon"
OUTPUT_PREFIX         = "results_gemma/pbmc_annotation"
EXISTING_ANNOTATION_KEY = "louvain"                   # key in pbmc3k_processed.obs
RESULTS_DIR           = "results_gemma"
AWS_PROFILE           = "chewu-scripps"
AWS_REGION            = "us-west-2"
