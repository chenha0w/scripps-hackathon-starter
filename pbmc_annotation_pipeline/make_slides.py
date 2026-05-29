#!/usr/bin/env python3
"""
Generate a presentation PDF comparing Claude, Llama, and Gemma PBMC annotation pipelines.
Saved as: pbmc_llm_pipeline_comparison.pdf
"""

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.patches import FancyBboxPatch, Rectangle
import matplotlib.image as mpimg
from pathlib import Path

# ── Colour palette ────────────────────────────────────────────────────────────
C_CLAUDE = "#2E86C1"   # blue
C_LLAMA  = "#E67E22"   # orange
C_GEMMA  = "#27AE60"   # green
C_ZS     = "#8E44AD"   # purple  (zero-shot accent)
C_REF    = "#C0392B"   # red     (reference accent)
BG       = "#F8F9FA"
DARK     = "#1A252F"
MID      = "#5D6D7E"

W, H = 16, 9   # slide dimensions (inches)

def new_slide(title, subtitle=None, bg=BG):
    fig = plt.figure(figsize=(W, H))
    fig.patch.set_facecolor(bg)
    # header bar
    fig.add_axes([0, 0.88, 1, 0.12]).set_visible(False)
    bar = fig.add_axes([0, 0.88, 1, 0.12])
    bar.set_facecolor(DARK); bar.set_xticks([]); bar.set_yticks([])
    for sp in bar.spines.values(): sp.set_visible(False)
    bar.text(0.03, 0.55, title, transform=bar.transAxes,
             fontsize=20, fontweight="bold", color="white", va="center")
    if subtitle:
        bar.text(0.03, 0.1, subtitle, transform=bar.transAxes,
                 fontsize=11, color="#AED6F1", va="center")
    return fig

def footer(fig, page_n, total=8):
    ax = fig.add_axes([0, 0, 1, 0.04])
    ax.set_facecolor(DARK); ax.set_xticks([]); ax.set_yticks([])
    for sp in ax.spines.values(): sp.set_visible(False)
    ax.text(0.5, 0.5, f"PBMC Cell-Type Annotation: LLM Pipeline Comparison  |  Scripps Research Hackathon 2026  |  {page_n}/{total}",
            transform=ax.transAxes, fontsize=8, color="#AED6F1",
            ha="center", va="center")

# ── Data ──────────────────────────────────────────────────────────────────────
metrics = {
    "Zero-Shot": {
        "Claude\n(Haiku 4.5)": dict(acc=0.851, mf1=0.673, wf1=0.804, kap=0.794, time=2.0,  mem=10),
        "Llama\n(3.1 70B)":    dict(acc=0.851, mf1=0.673, wf1=0.804, kap=0.794, time=1.1,  mem=80),
        "Gemma\n(3 27B)":      dict(acc=0.764, mf1=0.482, wf1=0.692, kap=0.674, time=23.5, mem=216),
    },
    "Reference Mapping": {
        "Claude\n(CellTypist)":     dict(acc=0.889, mf1=0.776, wf1=0.863, kap=0.847, time=1.5,  mem=255),
        "Llama\n(dot-product)":     dict(acc=0.732, mf1=0.502, wf1=0.710, kap=0.650, time=0.3,  mem=35),
        "Gemma\n(Scanorama+KNN)":   dict(acc=0.770, mf1=0.564, wf1=0.760, kap=0.697, time=1.4,  mem=77),
    },
}

per_class = {
    "Zero-Shot": {
        "Claude":  pd.read_csv("results/evaluation/per_class_zero_shot.csv",     index_col=0),
        "Llama":   pd.read_csv("results_llama/evaluation/per_class_zero_shot.csv", index_col=0),
        "Gemma":   pd.read_csv("results_gemma/evaluation/per_class_zero_shot.csv", index_col=0),
    },
    "Reference": {
        "Claude":  pd.read_csv("results/evaluation/per_class_reference.csv",     index_col=0),
        "Llama":   pd.read_csv("results_llama/evaluation/per_class_reference.csv", index_col=0),
        "Gemma":   pd.read_csv("results_gemma/evaluation/per_class_reference.csv", index_col=0),
    },
}

COLORS = [C_CLAUDE, C_LLAMA, C_GEMMA]
CELL_TYPES = ["B", "CD4 T", "CD8 T", "CD14 Mono", "DC", "FCGR3A Mono", "NK", "Platelet"]

OUT = "pbmc_llm_pipeline_comparison.pdf"

with PdfPages(OUT) as pdf:

    # ══════════════════════════════════════════════════════════════════════════
    # SLIDE 1 — Title
    # ══════════════════════════════════════════════════════════════════════════
    fig = plt.figure(figsize=(W, H))
    fig.patch.set_facecolor(DARK)

    # gradient-like band
    ax_band = fig.add_axes([0, 0.35, 1, 0.35])
    ax_band.set_facecolor("#1B4F72"); ax_band.set_xticks([]); ax_band.set_yticks([])
    for sp in ax_band.spines.values(): sp.set_visible(False)

    fig.text(0.5, 0.72, "PBMC Cell-Type Annotation", ha="center", va="center",
             fontsize=38, fontweight="bold", color="white")
    fig.text(0.5, 0.60, "LLM Pipeline Comparison: Claude vs Llama vs Gemma",
             ha="center", va="center", fontsize=22, color="#AED6F1")

    # Method chips
    for i, (label, color) in enumerate([
        ("Zero-Shot  (Marker Genes + LLM)", C_ZS),
        ("Reference Mapping  (Pre-trained Atlas)", C_REF),
    ]):
        x = 0.28 + i * 0.44
        ax_chip = fig.add_axes([x - 0.18, 0.43, 0.36, 0.06])
        ax_chip.set_facecolor(color); ax_chip.set_xticks([]); ax_chip.set_yticks([])
        for sp in ax_chip.spines.values(): sp.set_visible(False)
        ax_chip.text(0.5, 0.5, label, transform=ax_chip.transAxes,
                     ha="center", va="center", fontsize=13, color="white", fontweight="bold")

    fig.text(0.5, 0.25, "Dataset: PBMC 3k  |  AWS Bedrock  |  scanpy · CellTypist · Scanorama",
             ha="center", fontsize=13, color="#5D6D7E")
    fig.text(0.5, 0.18, "Scripps Research Hackathon 2026",
             ha="center", fontsize=12, color="#5D6D7E")

    # Model badges
    for i, (name, color) in enumerate([
        ("Claude Haiku 4.5", C_CLAUDE),
        ("Llama 3.1 70B", C_LLAMA),
        ("Gemma 3 27B", C_GEMMA),
    ]):
        ax_b = fig.add_axes([0.22 + i * 0.19, 0.05, 0.16, 0.08])
        ax_b.set_facecolor(color); ax_b.set_xticks([]); ax_b.set_yticks([])
        for sp in ax_b.spines.values(): sp.set_visible(False)
        ax_b.text(0.5, 0.5, name, transform=ax_b.transAxes,
                  ha="center", va="center", fontsize=12, color="white", fontweight="bold")

    footer(fig, 1)
    pdf.savefig(fig, bbox_inches="tight"); plt.close()

    # ══════════════════════════════════════════════════════════════════════════
    # SLIDE 2 — Pipeline Design Comparison Table
    # ══════════════════════════════════════════════════════════════════════════
    fig = new_slide("Pipeline Design Comparison",
                    "What did each LLM choose for each method?")

    ax = fig.add_axes([0.03, 0.08, 0.94, 0.78])
    ax.set_facecolor(BG); ax.set_xticks([]); ax.set_yticks([])
    for sp in ax.spines.values(): sp.set_visible(False)

    rows = [
        ["", "Claude (Haiku 4.5)", "Llama (3.1 70B)", "Gemma (3 27B)"],
        ["Zero-Shot\nApproach",
         "LLM API call via Bedrock\n(biological reasoning)",
         "Average marker gene\nexpression per cluster",
         "Sum marker gene\nexpression per cell"],
        ["Zero-Shot\nGranularity", "Cluster-level", "Cluster-level", "Per-cell"],
        ["Reference\nMethod",
         "CellTypist\n(logistic regression)",
         "Centroid dot-product\nsimilarity",
         "Scanorama integration\n+ KNN label transfer"],
        ["Reference\nDataset",
         "Immune_All_High\n(700k cells, 20+ studies)",
         "pbmc68k_reduced\n(700 cells, 10x Genomics)",
         "pbmc68k_reduced\n(700 cells, 10x Genomics)"],
        ["Code Structure", "4 scripts (pipeline)", "1 monolithic script", "6 modular scripts"],
        ["AWS Compute\nSuggested", "EC2 (r5.xlarge)", "EC2 + Batch", "EC2 (m5.2xlarge)"],
        ["Requires\nBedrock API", "✓ Yes (LLM call)", "✗ No", "✗ No"],
    ]

    col_colors  = ["#D5D8DC", "#D6EAF8", "#FDEBD0", "#D5F5E3"]
    col_widths  = [0.16, 0.28, 0.28, 0.28]
    row_height  = 0.097
    y_start     = 0.92

    for r_idx, row in enumerate(rows):
        y = y_start - r_idx * row_height
        x = 0.0
        for c_idx, (cell, cw) in enumerate(zip(row, col_widths)):
            bg = col_colors[c_idx]
            if r_idx == 0:
                bg = DARK
                fc = "white"; fs = 12; fw = "bold"
            elif r_idx % 2 == 0:
                bg = "#EAECEE" if c_idx == 0 else "#F2F3F4"
                fc = DARK; fs = 10; fw = "normal"
            else:
                bg = "#D5D8DC" if c_idx == 0 else col_colors[c_idx]
                fc = DARK; fs = 10; fw = "normal"

            rect = FancyBboxPatch((x, y - row_height), cw, row_height,
                                   boxstyle="square,pad=0", linewidth=0.5,
                                   edgecolor="white", facecolor=bg,
                                   transform=ax.transAxes, clip_on=False)
            ax.add_patch(rect)
            ax.text(x + cw/2, y - row_height/2, cell,
                    transform=ax.transAxes, ha="center", va="center",
                    fontsize=fs, fontweight=fw, color=fc,
                    multialignment="center")
            x += cw

    footer(fig, 2)
    pdf.savefig(fig, bbox_inches="tight"); plt.close()

    # ══════════════════════════════════════════════════════════════════════════
    # SLIDE 3 — Zero-Shot Results
    # ══════════════════════════════════════════════════════════════════════════
    fig = new_slide("Zero-Shot Annotation Results",
                    "Cluster marker genes → cell type label (no reference data)")
    gs  = gridspec.GridSpec(1, 2, left=0.05, right=0.97, top=0.85, bottom=0.1,
                             wspace=0.35, figure=fig)

    # Bar chart
    ax1 = fig.add_subplot(gs[0])
    ax1.set_facecolor(BG)
    metric_keys  = ["acc", "mf1", "wf1", "kap"]
    metric_names = ["Accuracy", "Macro F1", "Weighted F1", "Cohen's κ"]
    models_zs    = list(metrics["Zero-Shot"].keys())
    x = np.arange(len(metric_names))
    w = 0.25
    for i, (model, color) in enumerate(zip(models_zs, COLORS)):
        vals = [metrics["Zero-Shot"][model][k] for k in metric_keys]
        bars = ax1.bar(x + (i-1)*w, vals, w, label=model.replace("\n"," "),
                       color=color, alpha=0.88, edgecolor="white", linewidth=0.5)
        for bar, val in zip(bars, vals):
            ax1.text(bar.get_x()+bar.get_width()/2, bar.get_height()+0.01,
                     f"{val:.2f}", ha="center", va="bottom", fontsize=7, fontweight="bold")
    ax1.set_xticks(x); ax1.set_xticklabels(metric_names, fontsize=10)
    ax1.set_ylim(0, 1.15); ax1.set_ylabel("Score", fontsize=10)
    ax1.set_title("Metric Comparison", fontsize=12, fontweight="bold")
    ax1.legend(fontsize=9); ax1.spines[["top","right"]].set_visible(False)

    # Summary table
    ax2 = fig.add_subplot(gs[1])
    ax2.set_facecolor(BG); ax2.axis("off")
    rows_t = [["Model", "Accuracy", "Macro F1", "Wtd F1", "Kappa", "Time", "Mem"]]
    for (model, color), c in zip(
        [("Claude\n(Haiku 4.5)", C_CLAUDE), ("Llama\n(3.1 70B)", C_LLAMA),
         ("Gemma\n(3 27B)",      C_GEMMA)], COLORS):
        d = metrics["Zero-Shot"][model]
        rows_t.append([model.replace("\n"," "),
                        f"{d['acc']:.3f}", f"{d['mf1']:.3f}",
                        f"{d['wf1']:.3f}", f"{d['kap']:.3f}",
                        f"{d['time']:.1f}s", f"{d['mem']}MB"])

    tbl = ax2.table(cellText=rows_t[1:], colLabels=rows_t[0],
                    cellLoc="center", loc="center",
                    bbox=[0, 0.1, 1, 0.85])
    tbl.auto_set_font_size(False); tbl.set_fontsize(10)
    for (r, c), cell in tbl.get_celld().items():
        cell.set_edgecolor("white")
        if r == 0:
            cell.set_facecolor(DARK); cell.set_text_props(color="white", fontweight="bold")
        elif r == 1:
            cell.set_facecolor("#D6EAF8")
        elif r == 2:
            cell.set_facecolor("#FDEBD0")
        else:
            cell.set_facecolor("#D5F5E3")
    ax2.set_title("Performance Summary", fontsize=12, fontweight="bold", pad=10)

    # Winner annotation
    fig.text(0.5, 0.03, "★ Claude & Llama tie on accuracy (85.1%) — identical cluster assignments despite different mechanisms",
             ha="center", fontsize=10, color=DARK, style="italic")

    footer(fig, 3)
    pdf.savefig(fig, bbox_inches="tight"); plt.close()

    # ══════════════════════════════════════════════════════════════════════════
    # SLIDE 4 — Reference Mapping Results
    # ══════════════════════════════════════════════════════════════════════════
    fig = new_slide("Reference Mapping Results",
                    "Annotate cells using a well-characterised external reference atlas")
    gs  = gridspec.GridSpec(1, 2, left=0.05, right=0.97, top=0.85, bottom=0.1,
                             wspace=0.35, figure=fig)

    ax1 = fig.add_subplot(gs[0])
    ax1.set_facecolor(BG)
    models_ref = list(metrics["Reference Mapping"].keys())
    x = np.arange(len(metric_names))
    for i, (model, color) in enumerate(zip(models_ref, COLORS)):
        vals = [metrics["Reference Mapping"][model][k] for k in metric_keys]
        bars = ax1.bar(x + (i-1)*w, vals, w, label=model.replace("\n"," "),
                       color=color, alpha=0.88, edgecolor="white", linewidth=0.5)
        for bar, val in zip(bars, vals):
            ax1.text(bar.get_x()+bar.get_width()/2, bar.get_height()+0.01,
                     f"{val:.2f}", ha="center", va="bottom", fontsize=7, fontweight="bold")
    ax1.set_xticks(x); ax1.set_xticklabels(metric_names, fontsize=10)
    ax1.set_ylim(0, 1.15); ax1.set_ylabel("Score", fontsize=10)
    ax1.set_title("Metric Comparison", fontsize=12, fontweight="bold")
    ax1.legend(fontsize=9); ax1.spines[["top","right"]].set_visible(False)

    ax2 = fig.add_subplot(gs[1])
    ax2.set_facecolor(BG); ax2.axis("off")
    rows_t = [["Model", "Accuracy", "Macro F1", "Wtd F1", "Kappa", "Time", "Mem"]]
    for model, c in zip(models_ref, COLORS):
        d = metrics["Reference Mapping"][model]
        rows_t.append([model.replace("\n"," "),
                        f"{d['acc']:.3f}", f"{d['mf1']:.3f}",
                        f"{d['wf1']:.3f}", f"{d['kap']:.3f}",
                        f"{d['time']:.1f}s", f"{d['mem']}MB"])
    tbl = ax2.table(cellText=rows_t[1:], colLabels=rows_t[0],
                    cellLoc="center", loc="center",
                    bbox=[0, 0.1, 1, 0.85])
    tbl.auto_set_font_size(False); tbl.set_fontsize(10)
    for (r, c), cell in tbl.get_celld().items():
        cell.set_edgecolor("white")
        if r == 0:
            cell.set_facecolor(DARK); cell.set_text_props(color="white", fontweight="bold")
        elif r == 1: cell.set_facecolor("#D6EAF8")
        elif r == 2: cell.set_facecolor("#FDEBD0")
        else:        cell.set_facecolor("#D5F5E3")
    ax2.set_title("Performance Summary", fontsize=12, fontweight="bold", pad=10)

    fig.text(0.5, 0.03,
             "★ Claude's CellTypist wins (+12–16 pp over Llama/Gemma) by choosing a pre-trained 700k-cell model",
             ha="center", fontsize=10, color=DARK, style="italic")

    footer(fig, 4)
    pdf.savefig(fig, bbox_inches="tight"); plt.close()

    # ══════════════════════════════════════════════════════════════════════════
    # SLIDE 5 — Per-Class F1 Scores
    # ══════════════════════════════════════════════════════════════════════════
    fig = new_slide("Per-Class F1 Score Breakdown",
                    "Which cell types are each method good / bad at?")
    gs  = gridspec.GridSpec(1, 2, left=0.05, right=0.97, top=0.85, bottom=0.12,
                             wspace=0.35, figure=fig)

    for ax_idx, (method_key, method_label) in enumerate([
        ("Zero-Shot", "Zero-Shot Annotation"),
        ("Reference", "Reference Mapping"),
    ]):
        ax = fig.add_subplot(gs[ax_idx])
        ax.set_facecolor(BG)
        pcd   = per_class[method_key]
        n_ct  = len(CELL_TYPES)
        x     = np.arange(n_ct)
        bw    = 0.26
        for i, (model_name, color) in enumerate(zip(["Claude","Llama","Gemma"], COLORS)):
            df = pcd[model_name]
            vals = [float(df.loc[ct, "f1-score"]) if ct in df.index else 0.0
                    for ct in CELL_TYPES]
            ax.bar(x + (i-1)*bw, vals, bw, label=model_name,
                   color=color, alpha=0.85, edgecolor="white", linewidth=0.4)
        ax.set_xticks(x)
        ax.set_xticklabels(CELL_TYPES, rotation=35, ha="right", fontsize=9)
        ax.set_ylim(0, 1.15); ax.set_ylabel("F1 Score", fontsize=10)
        ax.set_title(method_label, fontsize=12, fontweight="bold")
        ax.legend(fontsize=9); ax.spines[["top","right"]].set_visible(False)
        # Zero line
        ax.axhline(0, color="gray", linewidth=0.5)
        # Blind spot band
        ax.axhspan(0, 0.05, alpha=0.08, color="red")

    fig.text(0.5, 0.03,
             "Red zone (F1≈0): FCGR3A Mono undetected by all methods — merged with CD14 Mono in the same Leiden cluster",
             ha="center", fontsize=10, color="#C0392B", style="italic")
    footer(fig, 5)
    pdf.savefig(fig, bbox_inches="tight"); plt.close()

    # ══════════════════════════════════════════════════════════════════════════
    # SLIDE 6 — UMAP Visualisations
    # ══════════════════════════════════════════════════════════════════════════
    fig = new_slide("UMAP Visualisations",
                    "Claude pipeline — Ground Truth vs Zero-Shot vs Reference Mapping")
    umap_path = "results/evaluation/umap_three_way.png"
    if Path(umap_path).exists():
        ax_img = fig.add_axes([0.02, 0.08, 0.96, 0.78])
        img = mpimg.imread(umap_path)
        ax_img.imshow(img, aspect="auto")
        ax_img.axis("off")
    else:
        fig.text(0.5, 0.5, "UMAP image not found", ha="center", fontsize=14, color=MID)

    footer(fig, 6)
    pdf.savefig(fig, bbox_inches="tight"); plt.close()

    # ══════════════════════════════════════════════════════════════════════════
    # SLIDE 7 — Resource Usage
    # ══════════════════════════════════════════════════════════════════════════
    fig = new_slide("Resource Usage: Time & Memory",
                    "Wall-clock time and peak memory per annotation method")
    gs  = gridspec.GridSpec(1, 2, left=0.07, right=0.97, top=0.85, bottom=0.14,
                             wspace=0.4, figure=fig)

    step_labels = [
        "ZS — Claude", "ZS — Llama", "ZS — Gemma",
        "Ref — Claude", "Ref — Llama", "Ref — Gemma",
    ]
    times = [2.0, 1.1, 23.5, 1.5, 0.3, 1.4]
    mems  = [10, 80, 216, 255, 35, 77]
    bar_colors = [C_CLAUDE, C_LLAMA, C_GEMMA, C_CLAUDE, C_LLAMA, C_GEMMA]
    bar_alpha  = [0.6, 0.6, 0.6, 1.0, 1.0, 1.0]   # lighter for ZS, full for Ref

    ax1 = fig.add_subplot(gs[0])
    ax1.set_facecolor(BG)
    bars = ax1.barh(step_labels, times,
                    color=[c for c in bar_colors],
                    alpha=0.85, edgecolor="white")
    for bar, val in zip(bars, times):
        ax1.text(val + 0.3, bar.get_y()+bar.get_height()/2,
                 f"{val:.1f}s", va="center", fontsize=10, fontweight="bold")
    ax1.set_xlabel("Wall Time (seconds)", fontsize=10)
    ax1.set_title("Runtime per Method", fontsize=12, fontweight="bold")
    ax1.set_xlim(0, 30); ax1.spines[["top","right"]].set_visible(False)
    ax1.axvline(5, color="gray", linestyle="--", linewidth=0.7, alpha=0.5)
    ax1.text(5.2, 5.5, "Gemma ZS\n(23.5s — slowest)", fontsize=8, color="#C0392B")

    ax2 = fig.add_subplot(gs[1])
    ax2.set_facecolor(BG)
    bars = ax2.barh(step_labels, mems,
                    color=[c for c in bar_colors],
                    alpha=0.85, edgecolor="white")
    for bar, val in zip(bars, mems):
        ax2.text(val + 2, bar.get_y()+bar.get_height()/2,
                 f"{val} MB", va="center", fontsize=10, fontweight="bold")
    ax2.set_xlabel("Peak Memory (MB)", fontsize=10)
    ax2.set_title("Peak Memory per Method", fontsize=12, fontweight="bold")
    ax2.set_xlim(0, 320); ax2.spines[["top","right"]].set_visible(False)

    # Legend: ZS vs Ref
    fig.text(0.5, 0.05, "Lighter bars = Zero-Shot   |   Solid bars = Reference Mapping",
             ha="center", fontsize=10, color=MID, style="italic")
    footer(fig, 7)
    pdf.savefig(fig, bbox_inches="tight"); plt.close()

    # ══════════════════════════════════════════════════════════════════════════
    # SLIDE 8 — Key Differences & Limitations
    # ══════════════════════════════════════════════════════════════════════════
    fig = new_slide("Key Differences & Limitations")
    fig.patch.set_facecolor(BG)

    sections = [
        ("[1] METHOD DIFFERENCES", C_CLAUDE, [
            "Claude: Only LLM that called the Bedrock API — used biological reasoning to annotate from marker genes",
            "Llama: Simplified cluster-level scoring — no API call, faster, identical zero-shot accuracy to Claude",
            "Gemma: Suggested Scanorama (a proper batch-correction tool) — most sophisticated integration approach",
            "Reference tool choice drove the largest accuracy gap: CellTypist (700k cells) vs dot-product/KNN (700 cells)",
        ]),
        ("[2] SHARED LIMITATIONS", C_REF, [
            "Leiden resolution 0.5 → 6 clusters, but 8 ground-truth cell types → FCGR3A Mono & NK merged with neighbors",
            "FCGR3A+ Monocytes: F1 = 0.00 for ALL methods — requires higher clustering resolution to rescue",
            "pbmc68k reference (Llama/Gemma) too small (700 cells) for reliable centroid estimation",
            "Ground truth labels from scanpy (coarse: 'CD4 T cells') vs Seurat (fine: 'Naive/Memory CD4 T')",
        ]),
        ("[3] LLM CODE QUALITY", C_LLAMA, [
            "Claude: Produced complete, runnable pipeline — chose CellTypist without being told about it",
            "Llama: Skeleton with bugs (wrong argmax logic, wrong boto3 syntax) — required ~10 fixes to run",
            "Gemma: Most structured (6 modular files) but wrong reference (Mouse Brain Atlas for a PBMC task!)",
            "All 3 omitted memory tracking — Claude noted 'use psutil', Gemma/Llama left it as an exercise",
        ]),
    ]

    y = 0.84
    for title, color, bullets in sections:
        # Section header
        ax_h = fig.add_axes([0.03, y - 0.04, 0.94, 0.045])
        ax_h.set_facecolor(color); ax_h.set_xticks([]); ax_h.set_yticks([])
        for sp in ax_h.spines.values(): sp.set_visible(False)
        ax_h.text(0.015, 0.5, title, transform=ax_h.transAxes,
                  fontsize=12, fontweight="bold", color="white", va="center")
        y -= 0.055
        for bullet in bullets:
            fig.text(0.055, y, f"•  {bullet}", fontsize=10, color=DARK,
                     va="top", wrap=True,
                     bbox=dict(facecolor="white", alpha=0, pad=0))
            y -= 0.058
        y -= 0.01

    footer(fig, 8)
    pdf.savefig(fig, bbox_inches="tight"); plt.close()

print(f"✓ Saved: {OUT}  ({Path(OUT).stat().st_size//1024} KB)")
