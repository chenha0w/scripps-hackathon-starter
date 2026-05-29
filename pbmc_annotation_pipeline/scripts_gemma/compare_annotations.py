# compare_annotations.py  (Gemma-generated)
# Gemma's metrics: Adjusted Rand Index + accuracy, precision, recall, F1, confusion matrix.
# Extended to match the canonical 8-type label space used by Claude and Llama pipelines.

import os, glob
import numpy as np
import pandas as pd
import scanpy as sc
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.metrics import (
    adjusted_rand_score, accuracy_score,
    classification_report, confusion_matrix,
    f1_score, cohen_kappa_score,
)
from config import RESULTS_DIR, OUTPUT_PREFIX

os.makedirs(f"{RESULTS_DIR}/evaluation", exist_ok=True)
os.makedirs(f"{RESULTS_DIR}/plots",      exist_ok=True)

# ── Label harmonisation → canonical 8-type space ─────────────────────────────
GT_MAP = {
    "CD4 T cells":        "CD4 T",  "CD8 T cells":        "CD8 T",
    "NK cells":           "NK",     "B cells":             "B",
    "CD14+ Monocytes":   "CD14 Mono", "FCGR3A+ Monocytes": "FCGR3A Mono",
    "Dendritic cells":   "DC",      "Megakaryocytes":      "Platelet",
}
# Gemma's zero-shot labels (coarse, no NK/FCGR3A distinction)
ZS_MAP = {
    "T cells":          "CD4 T",   # Gemma doesn't split CD4/CD8
    "B cells":          "B",
    "Monocytes":        "CD14 Mono",
    "NK cells":         "NK",
    "Dendritic cells":  "DC",
}
# Gemma reference labels (pbmc68k bulk_labels)
REF_MAP = {
    "CD4+/CD45RA+/CD25- Naive T":  "CD4 T",
    "CD4+/CD45RO+ Memory":          "CD4 T",
    "CD4+/CD25 T Reg":              "CD4 T",
    "CD8+ Cytotoxic T":             "CD8 T",
    "CD8+/CD45RA+ Naive Cytotoxic": "CD8 T",
    "CD56+ NK":                     "NK",
    "CD19+ B":                      "B",
    "CD14+ Monocyte":               "CD14 Mono",
    "Dendritic":                    "DC",
    "CD34+":                        "Unknown",
}

def safe_map(series, mapping):
    return pd.Series([mapping.get(str(v), "Unknown") for v in series],
                     index=series.index, dtype=str)

def compare_annotations():
    adata = sc.read_h5ad(f"{OUTPUT_PREFIX}_reference_mapping.h5ad")
    gt    = pd.read_csv(f"{RESULTS_DIR}/ground_truth_labels.csv", index_col="cell_barcode")

    shared = adata.obs_names.intersection(gt.index)
    adata.obs["ground_truth"] = "Unknown"
    adata.obs.loc[shared, "ground_truth"] = gt.loc[shared, "ground_truth"].values

    adata.obs["gt_canonical"]  = safe_map(adata.obs["ground_truth"],         GT_MAP)
    adata.obs["zs_canonical"]  = safe_map(adata.obs["zero_shot_annotation"],  ZS_MAP)
    adata.obs["ref_canonical"] = safe_map(adata.obs["reference_annotation"],  REF_MAP)

    # ── Gemma's primary metric: ARI ───────────────────────────────────────────
    valid_gt = adata.obs["gt_canonical"] != "Unknown"
    gt_labels = adata.obs.loc[valid_gt, "gt_canonical"]
    zs_labels = adata.obs.loc[valid_gt, "zs_canonical"]
    rf_labels = adata.obs.loc[valid_gt, "ref_canonical"]

    ari_zs  = adjusted_rand_score(gt_labels, zs_labels)
    ari_ref = adjusted_rand_score(gt_labels, rf_labels)
    print(f"\nAdjusted Rand Index (Zero-Shot) : {ari_zs:.4f}")
    print(f"Adjusted Rand Index (Reference)  : {ari_ref:.4f}")

    # ── Full metrics ──────────────────────────────────────────────────────────
    def calc(pred_col, label):
        df = adata.obs[["gt_canonical", pred_col]]
        df = df[(df["gt_canonical"] != "Unknown") & (df[pred_col] != "Unknown")]
        yt, yp = df["gt_canonical"].tolist(), df[pred_col].tolist()
        acc = accuracy_score(yt, yp)
        wf1 = f1_score(yt, yp, average="weighted", zero_division=0)
        mf1 = f1_score(yt, yp, average="macro",    zero_division=0)
        kap = cohen_kappa_score(yt, yp)
        ari = adjusted_rand_score(yt, yp)
        rep = classification_report(yt, yp, output_dict=True, zero_division=0)
        per = (pd.DataFrame(rep).T.iloc[:-3]
               .rename(columns={"support":"n_cells"})
               .assign(n_cells=lambda d: d["n_cells"].astype(int)))
        print(f"\n── {label} ──")
        print(f"  Cells       : {len(yt)}/{len(adata)} ({100*len(yt)/len(adata):.1f}%)")
        print(f"  Accuracy    : {acc:.4f}  ({100*acc:.1f}%)")
        print(f"  ARI         : {ari:.4f}")
        print(f"  Macro F1    : {mf1:.4f}")
        print(f"  Weighted F1 : {wf1:.4f}")
        print(f"  Kappa       : {kap:.4f}")
        print(per[["precision","recall","f1-score","n_cells"]].to_string())
        return dict(method=label, n_cells=len(yt), accuracy=acc, ari=ari,
                    macro_f1=mf1, weighted_f1=wf1, cohen_kappa=kap,
                    per_class=per, y_true=yt, y_pred=yp)

    m_zs  = calc("zs_canonical",  "Zero-Shot (Gemma marker scoring)")
    m_ref = calc("ref_canonical", "Reference Mapping (Gemma Scanorama+KNN)")

    # ── Confusion matrices ────────────────────────────────────────────────────
    def plot_conf(yt, yp, title, path):
        labels = sorted(set(yt) | set(yp))
        cm = confusion_matrix(yt, yp, labels=labels, normalize="true")
        fig, ax = plt.subplots(figsize=(9, 8))
        sns.heatmap(cm, annot=True, fmt=".2f", cmap="Greens",
                    xticklabels=labels, yticklabels=labels,
                    linewidths=0.5, ax=ax, vmin=0, vmax=1, annot_kws={"size": 9})
        ax.set_xlabel("Ground Truth"); ax.set_ylabel("Predicted")
        ax.set_title(title, fontsize=12)
        ax.tick_params(axis="x", rotation=35, labelsize=9)
        ax.tick_params(axis="y", rotation=0,  labelsize=9)
        fig.tight_layout(); fig.savefig(path, dpi=150); plt.close()

    plot_conf(m_zs["y_true"],  m_zs["y_pred"],
              "Gemma Zero-Shot — Confusion Matrix",
              f"{RESULTS_DIR}/evaluation/confusion_zero_shot.png")
    plot_conf(m_ref["y_true"], m_ref["y_pred"],
              "Gemma Reference Mapping (Scanorama+KNN) — Confusion Matrix",
              f"{RESULTS_DIR}/evaluation/confusion_reference.png")

    # ── Summary ───────────────────────────────────────────────────────────────
    summary = pd.DataFrame([
        {k: v for k, v in m.items() if k not in ("per_class","y_true","y_pred")}
        for m in (m_zs, m_ref)
    ])
    summary.to_csv(f"{RESULTS_DIR}/evaluation/metrics_summary.csv", index=False)
    m_zs["per_class"].to_csv(f"{RESULTS_DIR}/evaluation/per_class_zero_shot.csv")
    m_ref["per_class"].to_csv(f"{RESULTS_DIR}/evaluation/per_class_reference.csv")

    # ── UMAP three-way ────────────────────────────────────────────────────────
    fig, axes = plt.subplots(1, 3, figsize=(19, 5))
    for ax, col, title in zip(axes,
        ["gt_canonical", "zs_canonical", "ref_canonical"],
        ["Ground Truth", "Zero-Shot (Gemma)", "Scanorama+KNN (Gemma)"]):
        sc.pl.umap(adata, color=col, title=title, ax=ax, show=False,
                   legend_loc="right margin" if ax is axes[2] else "on data",
                   legend_fontsize=7)
    fig.tight_layout()
    fig.savefig(f"{RESULTS_DIR}/plots/umap_three_way.png", dpi=150)
    plt.close()

    # ── Timing ────────────────────────────────────────────────────────────────
    tfiles = glob.glob(f"{RESULTS_DIR}/timing_*.csv")
    timing = pd.concat([pd.read_csv(f) for f in tfiles]).sort_values("step")
    timing.to_csv(f"{RESULTS_DIR}/evaluation/timing_summary.csv", index=False)
    print(f"\n── Resource Usage ──\n{timing[['step','wall_time_sec','peak_mem_mb']].to_string(index=False)}")

    return summary

if __name__ == "__main__":
    summary = compare_annotations()
    print(f"\n{'='*60}")
    print("  FINAL RESULTS (Gemma-generated pipeline)")
    print(f"{'='*60}")
    print(summary[["method","n_cells","accuracy","ari",
                   "macro_f1","weighted_f1","cohen_kappa"]].to_string(index=False))
