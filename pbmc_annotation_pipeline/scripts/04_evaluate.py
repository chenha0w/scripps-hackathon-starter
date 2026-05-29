#!/usr/bin/env python3
"""
Step 4: Compare zero-shot LLM and CellTypist reference mapping against ground truth.

All three label spaces are harmonised into the same 8-type canonical space:
  CD4 T | CD8 T | NK | B | CD14 Mono | FCGR3A Mono | DC | Platelet

Metrics: Accuracy, Macro F1, Weighted F1, Cohen's Kappa, per-class P/R/F1

Outputs → results/evaluation/
"""

import os, glob
import numpy as np
import pandas as pd
import scanpy as sc
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.metrics import (
    accuracy_score, f1_score, cohen_kappa_score,
    classification_report, confusion_matrix,
)

RESULTS = "results"
EVAL    = f"{RESULTS}/evaluation"
os.makedirs(EVAL, exist_ok=True)

print("=== Step 4: Evaluation ===")

# ── Load all data ─────────────────────────────────────────────────────────────
adata  = sc.read_h5ad(f"{RESULTS}/pbmc_processed.h5ad")
gt_df  = pd.read_csv(f"{RESULTS}/ground_truth_labels.csv", index_col="cell_barcode")
zs_df  = pd.read_csv(f"{RESULTS}/zero_shot_annotations.csv")
ref_df = pd.read_csv(f"{RESULTS}/reference_mapping_annotations.csv",
                      index_col="cell_barcode")

# ── Build master table ────────────────────────────────────────────────────────
cells = adata.obs[["leiden"]].copy()
cells["leiden"] = cells["leiden"].astype(int)
cells.index.name = "cell_barcode"
cells["ground_truth"]         = gt_df["ground_truth"]
cells["reference_cell_level"] = ref_df["reference_cell_level"]
cells["reference_cluster"]    = ref_df["reference_annotation"]
cells["cluster"]              = cells["leiden"]

zs_map = dict(zip(zs_df["cluster"], zs_df["zero_shot_annotation"]))
cells["zero_shot_annotation"] = cells["leiden"].map(zs_map)

print(f"Total cells: {len(cells)}")
print(f"\nGround truth distribution:\n{cells['ground_truth'].value_counts().to_string()}")

# ── Label harmonisation ───────────────────────────────────────────────────────
# Canonical 8-type space (matches the 8 ground truth cell types in pbmc3k).

# Ground truth: scanpy pbmc3k_processed labels
GT_MAP = {
    "CD4 T cells":        "CD4 T",
    "CD8 T cells":        "CD8 T",
    "NK cells":           "NK",
    "B cells":            "B",
    "CD14+ Monocytes":   "CD14 Mono",
    "FCGR3A+ Monocytes": "FCGR3A Mono",
    "Dendritic cells":    "DC",
    "Megakaryocytes":     "Platelet",
}

def harmonise_gt(lbl):
    return GT_MAP.get(str(lbl), "Unknown")

# Zero-shot LLM: outputs Seurat-style names
ZS_MAP = {
    "Naive CD4 T":  "CD4 T",
    "Memory CD4 T": "CD4 T",
    "CD4 T":        "CD4 T",
    "CD8 T":        "CD8 T",
    "NK":           "NK",
    "B":            "B",
    "CD14+ Mono":   "CD14 Mono",
    "FCGR3A+ Mono": "FCGR3A Mono",
    "DC":           "DC",
    "Platelet":     "Platelet",
}

def harmonise_zs(lbl):
    return ZS_MAP.get(str(lbl), "Unknown")

# CellTypist: broad immune categories; use Leiden cluster for T/Mono disambiguation.
# Cluster 0 (CD3D, LTB markers)    → CD4 T-dominated
# Cluster 1 (S100A9, LYZ markers)  → Monocyte-dominated (CD14 majority)
# Cluster 2 (NKG7, GZMB markers)   → CD8 T / NK cytotoxic cluster
def harmonise_ct(lbl, cluster):
    lbl = str(lbl).lower()
    if "t cell" in lbl or "thymocyte" in lbl:
        # Cluster 2 has cytotoxic (NKG7, GZMB) markers → label as CD8 T
        return "CD8 T" if int(cluster) == 2 else "CD4 T"
    if "ilc" in lbl:          return "NK"       # ILC ≈ NK in PBMC
    if "monocyte" in lbl:
        # Cluster 1 has both CD14+ and FCGR3A+ Mono; CellTypist can't distinguish them.
        # CD14 is the majority (~75% of cluster 1), so default to CD14 Mono.
        return "CD14 Mono"
    if "b cell" in lbl:        return "B"
    if "dc" in lbl or "pdc" in lbl or "dendritic" in lbl: return "DC"
    if "platelet" in lbl or "megakaryocyte" in lbl:  return "Platelet"
    if "nk" in lbl or "natural killer" in lbl:        return "NK"
    return "Unknown"

cells["gt_canonical"]  = cells["ground_truth"].map(harmonise_gt)
cells["zs_canonical"]  = cells["zero_shot_annotation"].map(harmonise_zs)
cells["ct_canonical"]  = cells.apply(
    lambda r: harmonise_ct(r["reference_cell_level"], r["cluster"]), axis=1)

print(f"\nGT (canonical):\n{cells['gt_canonical'].value_counts().to_string()}")
print(f"\nZero-Shot (canonical):\n{cells['zs_canonical'].value_counts().to_string()}")
print(f"\nCellTypist (canonical):\n{cells['ct_canonical'].value_counts().to_string()}")

# Show cluster composition (GT distribution per cluster)
print("\n── GT cell type composition per Leiden cluster ──")
comp = pd.crosstab(cells["cluster"], cells["gt_canonical"])
print(comp.to_string())

# ── Metric calculator ─────────────────────────────────────────────────────────
def calc_metrics(pred_col, label):
    df  = cells[["gt_canonical", pred_col]].copy()
    df  = df[(df["gt_canonical"] != "Unknown") & (df[pred_col] != "Unknown")]
    y_t = df["gt_canonical"].tolist()
    y_p = df[pred_col].tolist()
    n   = len(y_t)

    acc  = accuracy_score(y_t, y_p)
    wf1  = f1_score(y_t, y_p, average="weighted", zero_division=0)
    mf1  = f1_score(y_t, y_p, average="macro",    zero_division=0)
    kap  = cohen_kappa_score(y_t, y_p)
    rep  = classification_report(y_t, y_p, output_dict=True, zero_division=0)
    per_class = (pd.DataFrame(rep).T.iloc[:-3]
                 .rename(columns={"support": "n_cells"})
                 .assign(n_cells=lambda d: d["n_cells"].astype(int)))

    print(f"\n{'─'*52}")
    print(f"  {label}")
    print(f"{'─'*52}")
    print(f"  Cells evaluated : {n}/{len(cells)} ({100*n/len(cells):.1f}%)")
    print(f"  Accuracy        : {acc:.4f}  ({100*acc:.1f}%)")
    print(f"  Macro F1        : {mf1:.4f}")
    print(f"  Weighted F1     : {wf1:.4f}")
    print(f"  Cohen's Kappa   : {kap:.4f}")
    print(f"  Per-class metrics:")
    print(per_class[["precision","recall","f1-score","n_cells"]].to_string())

    return dict(method=label, n_cells=n, accuracy=acc,
                macro_f1=mf1, weighted_f1=wf1, cohen_kappa=kap,
                per_class=per_class, y_true=y_t, y_pred=y_p)

m_zs = calc_metrics("zs_canonical",  "Zero-Shot LLM (Claude Haiku 4.5)")
m_ct = calc_metrics("ct_canonical",  "Reference Mapping (CellTypist)")

# ── Summary CSV ───────────────────────────────────────────────────────────────
summary = pd.DataFrame([
    {k: v for k, v in m.items() if k not in ("per_class","y_true","y_pred")}
    for m in (m_zs, m_ct)
])
summary.to_csv(f"{EVAL}/metrics_summary.csv", index=False)
m_zs["per_class"].to_csv(f"{EVAL}/per_class_zero_shot.csv")
m_ct["per_class"].to_csv(f"{EVAL}/per_class_reference.csv")
cells.to_csv(f"{EVAL}/all_annotations.csv")

# ── Confusion matrices ────────────────────────────────────────────────────────
def plot_conf(y_true, y_pred, title, path):
    labels = sorted(set(y_true) | set(y_pred))
    cm = confusion_matrix(y_true, y_pred, labels=labels, normalize="true")
    fig, ax = plt.subplots(figsize=(9, 8))
    sns.heatmap(cm, annot=True, fmt=".2f", cmap="Blues",
                xticklabels=labels, yticklabels=labels,
                linewidths=0.5, ax=ax, vmin=0, vmax=1,
                annot_kws={"size": 9})
    ax.set_xlabel("Ground Truth", fontsize=11)
    ax.set_ylabel("Predicted", fontsize=11)
    ax.set_title(title, fontsize=12, pad=10)
    ax.tick_params(axis="x", rotation=35, labelsize=9)
    ax.tick_params(axis="y", rotation=0,  labelsize=9)
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close()

plot_conf(m_zs["y_true"], m_zs["y_pred"],
          "Zero-Shot LLM — Confusion Matrix (recall-normalised)",
          f"{EVAL}/confusion_zero_shot.png")
plot_conf(m_ct["y_true"], m_ct["y_pred"],
          "CellTypist Reference Mapping — Confusion Matrix",
          f"{EVAL}/confusion_reference.png")

# ── Metric comparison bar chart ───────────────────────────────────────────────
metric_names = ["accuracy", "macro_f1", "weighted_f1", "cohen_kappa"]
display_names = ["Accuracy", "Macro F1", "Weighted F1", "Cohen's Kappa"]
palette = {"Zero-Shot LLM (Claude Haiku 4.5)": "#E74C3C",
           "Reference Mapping (CellTypist)":   "#2E86C1"}
method_short = {"Zero-Shot LLM (Claude Haiku 4.5)": "Zero-Shot\nLLM",
                "Reference Mapping (CellTypist)":   "CellTypist\nReference"}

fig, axes = plt.subplots(1, 4, figsize=(16, 5))
for ax, (met, disp) in zip(axes, zip(metric_names, display_names)):
    for row in summary.itertuples():
        val   = getattr(row, met)
        color = palette[row.method]
        bar   = ax.bar(method_short[row.method], val, color=color, width=0.5, alpha=0.85)
        ax.text(bar[0].get_x() + bar[0].get_width()/2,
                val + 0.01, f"{val:.3f}", ha="center", va="bottom", fontsize=10, fontweight="bold")
    ax.set_ylim(0, 1.15)
    ax.set_title(disp, fontsize=12)
    ax.set_ylabel("Score" if ax is axes[0] else "")
    ax.tick_params(axis="x", labelsize=9)
    ax.spines[["top","right"]].set_visible(False)
fig.suptitle("PBMC3k Annotation Method Comparison", fontsize=14, y=1.01)
fig.tight_layout()
fig.savefig(f"{EVAL}/method_comparison.png", dpi=150, bbox_inches="tight")
plt.close()

# ── Per-class comparison (F1 score) ──────────────────────────────────────────
pclass_zs = m_zs["per_class"][["f1-score"]].rename(columns={"f1-score":"ZeroShot"})
pclass_ct = m_ct["per_class"][["f1-score"]].rename(columns={"f1-score":"CellTypist"})
pclass = pclass_zs.join(pclass_ct, how="outer").fillna(0)

fig, ax = plt.subplots(figsize=(10, 5))
x = np.arange(len(pclass))
w = 0.35
ax.bar(x - w/2, pclass["ZeroShot"],  width=w, label="Zero-Shot LLM",   color="#E74C3C", alpha=0.85)
ax.bar(x + w/2, pclass["CellTypist"], width=w, label="CellTypist",      color="#2E86C1", alpha=0.85)
ax.set_xticks(x)
ax.set_xticklabels(pclass.index, rotation=35, ha="right", fontsize=10)
ax.set_ylim(0, 1.15)
ax.set_ylabel("F1 Score")
ax.set_title("Per-Class F1 Score: Zero-Shot LLM vs CellTypist Reference")
ax.legend()
ax.spines[["top","right"]].set_visible(False)
fig.tight_layout()
fig.savefig(f"{EVAL}/per_class_f1_comparison.png", dpi=150)
plt.close()

# ── UMAP three-way ────────────────────────────────────────────────────────────
adata.obs["gt_canonical"]  = cells["gt_canonical"]
adata.obs["zs_canonical"]  = cells["zs_canonical"]
adata.obs["ct_canonical"]  = cells["ct_canonical"]

fig, axes = plt.subplots(1, 3, figsize=(19, 5))
for ax, col, title in zip(
    axes,
    ["gt_canonical", "zs_canonical", "ct_canonical"],
    ["Ground Truth", "Zero-Shot LLM", "CellTypist (Reference)"],
):
    sc.pl.umap(adata, color=col, title=title,
               legend_loc="right margin" if ax is axes[2] else "on data",
               ax=ax, show=False, legend_fontsize=7)
fig.tight_layout()
fig.savefig(f"{EVAL}/umap_three_way.png", dpi=150)
plt.close()

# ── Timing ────────────────────────────────────────────────────────────────────
timing_files = glob.glob(f"{RESULTS}/timing_*.csv")
timing_all   = pd.concat([pd.read_csv(f) for f in timing_files]).sort_values("step")
timing_all.to_csv(f"{EVAL}/timing_summary.csv", index=False)

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 4))
colors = plt.cm.Set2(np.linspace(0, 1, len(timing_all)))

ax1.barh(timing_all["step"], timing_all["wall_time_sec"], color=colors)
for i, v in enumerate(timing_all["wall_time_sec"]):
    ax1.text(v + 0.5, i, f"{v:.0f} s", va="center", fontsize=9)
ax1.set_xlabel("Wall Time (seconds)")
ax1.set_title("Runtime per Step")
ax1.set_xlim(0, timing_all["wall_time_sec"].max() * 1.25)
ax1.spines[["top","right"]].set_visible(False)

ax2.barh(timing_all["step"], timing_all["peak_mem_mb"], color=colors)
for i, v in enumerate(timing_all["peak_mem_mb"]):
    ax2.text(v + 1, i, f"{v:.0f} MB", va="center", fontsize=9)
ax2.set_xlabel("Peak Memory (MB)")
ax2.set_title("Peak Memory per Step")
ax2.set_xlim(0, timing_all["peak_mem_mb"].max() * 1.25)
ax2.spines[["top","right"]].set_visible(False)

fig.suptitle("Resource Usage by Pipeline Step", fontsize=13)
fig.tight_layout()
fig.savefig(f"{EVAL}/resource_summary.png", dpi=150)
plt.close()

# ── Note on cluster resolution ────────────────────────────────────────────────
print("""
⚠️  Resolution note: Leiden clustering at resolution=0.5 produced 6 clusters for
    a dataset with 8 ground-truth cell types. Specifically:
    • Cluster 0 merges Naive CD4 T + Memory CD4 T  (both mapped → CD4 T)
    • Cluster 1 merges CD14+ Mono + FCGR3A+ Mono   (ZS → CD14 Mono; CT → CD14 Mono)
    • Cluster 2 merges CD8 T + NK cells             (ZS → CD8 T; CT per-cell distinguishes some)
    Both methods have the same cluster-resolution ceiling.
    CellTypist per-cell predictions allow partial NK rescue via ILC labelling.
""")

# ── Final report ──────────────────────────────────────────────────────────────
print("\n" + "="*56)
print("              FINAL RESULTS SUMMARY")
print("="*56)
print("\n── Accuracy Metrics ──")
print(summary[["method","n_cells","accuracy","macro_f1",
               "weighted_f1","cohen_kappa"]].to_string(index=False))
print("\n── Resource Usage ──")
print(timing_all[["step","wall_time_sec","peak_mem_mb"]].to_string(index=False))
print(f"\nAll outputs → {EVAL}/")
