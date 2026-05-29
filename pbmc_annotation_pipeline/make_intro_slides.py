#!/usr/bin/env python3
"""
Introduction to Cell-Type Annotation — educational slide deck.
Target audience: mixed biology AND chemistry backgrounds.
Output: intro_cell_type_annotation.pdf  (10 slides)
"""

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import matplotlib.patches as mpatches
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch, Circle, FancyArrow
from matplotlib.backends.backend_pdf import PdfPages
import matplotlib.patheffects as pe
import scanpy as sc
import warnings
warnings.filterwarnings("ignore")

# ── Load real PBMC data once ──────────────────────────────────────────────────
adata = sc.read_h5ad("results/pbmc_processed.h5ad")

# Restore log-normalised raw for marker plots
import scipy.sparse as scipy_sparse
adata_raw = adata.raw.to_adata() if adata.raw else adata

# ── Design tokens ─────────────────────────────────────────────────────────────
BG    = "#FAFAFA"
DARK  = "#1A252F"
MID   = "#5D6D7E"
LIGHT = "#D5D8DC"

# Cell-type palette (consistent across slides)
CT_PAL = {
    "CD4 T cells":        "#3498DB",
    "CD8 T cells":        "#1ABC9C",
    "NK cells":           "#9B59B6",
    "B cells":            "#E74C3C",
    "CD14+ Monocytes":   "#E67E22",
    "FCGR3A+ Monocytes": "#F39C12",
    "Dendritic cells":    "#2ECC71",
    "Megakaryocytes":     "#95A5A6",
}
LEIDEN_PAL = {
    "0": "#3498DB", "1": "#E67E22", "2": "#9B59B6",
    "3": "#E74C3C", "4": "#2ECC71", "5": "#95A5A6",
}
W, H = 16, 9

# ── Helpers ───────────────────────────────────────────────────────────────────
def slide(title, subtitle=None, accent="#2C3E50"):
    fig = plt.figure(figsize=(W, H))
    fig.patch.set_facecolor(BG)
    bar = fig.add_axes([0, 0.88, 1, 0.12])
    bar.set_facecolor(accent)
    bar.set_xticks([]); bar.set_yticks([])
    for sp in bar.spines.values(): sp.set_visible(False)
    bar.text(0.03, 0.58, title, transform=bar.transAxes,
             fontsize=21, fontweight="bold", color="white", va="center")
    if subtitle:
        bar.text(0.03, 0.12, subtitle, transform=bar.transAxes,
                 fontsize=11, color="#AED6F1", va="center")
    return fig

def footer(fig, n, total=10):
    ax = fig.add_axes([0, 0, 1, 0.035])
    ax.set_facecolor("#2C3E50"); ax.set_xticks([]); ax.set_yticks([])
    for sp in ax.spines.values(): sp.set_visible(False)
    ax.text(0.5, 0.5,
            f"Introduction to Cell-Type Annotation  |  Scripps Research Hackathon 2026  |  {n}/{total}",
            transform=ax.transAxes, fontsize=8, color="#AED6F1",
            ha="center", va="center")

def box(ax, x, y, w, h, text, facecolor="#D6EAF8", fontsize=11,
        textcolor=DARK, fontweight="normal", radius=0.04):
    rect = FancyBboxPatch((x, y), w, h,
                           boxstyle=f"round,pad={radius}",
                           facecolor=facecolor, edgecolor="white",
                           linewidth=1.5, transform=ax.transAxes, clip_on=False)
    ax.add_patch(rect)
    ax.text(x + w/2, y + h/2, text, transform=ax.transAxes,
            ha="center", va="center", fontsize=fontsize,
            fontweight=fontweight, color=textcolor, multialignment="center",
            zorder=5)

def arrow(ax, x0, y0, x1, y1, color=DARK, lw=1.5):
    ax.annotate("", xy=(x1, y1), xytext=(x0, y0),
                 xycoords="axes fraction", textcoords="axes fraction",
                 arrowprops=dict(arrowstyle="-|>", color=color,
                                 lw=lw, mutation_scale=16))

OUT = "intro_cell_type_annotation.pdf"

with PdfPages(OUT) as pdf:

    # ══════════════════════════════════════════════════════════════════════════
    # SLIDE 1 — Title
    # ══════════════════════════════════════════════════════════════════════════
    fig = plt.figure(figsize=(W, H))
    fig.patch.set_facecolor("#1A252F")

    # Gradient band
    ax_b = fig.add_axes([0, 0.30, 1, 0.42])
    ax_b.set_facecolor("#1B4F72"); ax_b.set_xticks([]); ax_b.set_yticks([])
    for sp in ax_b.spines.values(): sp.set_visible(False)

    fig.text(0.5, 0.71, "Cell-Type Annotation", ha="center",
             fontsize=42, fontweight="bold", color="white")
    fig.text(0.5, 0.60, "in Single-Cell Genomics",
             ha="center", fontsize=28, color="#AED6F1")
    fig.text(0.5, 0.46,
             "A gentle introduction for biology and chemistry audiences",
             ha="center", fontsize=16, color="#85C1E9", style="italic")

    topics = ["Single-Cell RNA-seq", "Gene Expression Matrix",
              "Marker Genes", "Zero-Shot Annotation", "Reference Mapping"]
    for i, t in enumerate(topics):
        x = 0.08 + i * 0.18
        ax_c = fig.add_axes([x, 0.14, 0.15, 0.09])
        ax_c.set_facecolor("#2E86C1" if i % 2 == 0 else "#E67E22")
        ax_c.set_xticks([]); ax_c.set_yticks([])
        for sp in ax_c.spines.values(): sp.set_visible(False)
        ax_c.text(0.5, 0.5, t, transform=ax_c.transAxes,
                  ha="center", va="center", fontsize=10,
                  fontweight="bold", color="white", multialignment="center")

    fig.text(0.5, 0.06, "Scripps Research Hackathon 2026",
             ha="center", fontsize=11, color="#5D6D7E")
    footer(fig, 1)
    pdf.savefig(fig, bbox_inches="tight"); plt.close()

    # ══════════════════════════════════════════════════════════════════════════
    # SLIDE 2 — Central question + cell diversity diagram
    # ══════════════════════════════════════════════════════════════════════════
    fig = slide("The Central Question",
                "A tissue contains many different cell types — but how do we tell them apart?",
                accent="#1B4F72")

    ax = fig.add_axes([0.03, 0.07, 0.94, 0.79])
    ax.set_xlim(0, 10); ax.set_ylim(0, 5)
    ax.set_facecolor(BG); ax.axis("off")

    # Left: tissue blob with mixed cells
    tissue = mpatches.Ellipse((2.0, 2.5), 3.0, 4.0,
                               facecolor="#FADBD8", edgecolor="#E74C3C",
                               linewidth=2, alpha=0.6)
    ax.add_patch(tissue)
    ax.text(2.0, 4.7, "A tissue sample\n(e.g. blood)", ha="center",
            fontsize=12, fontweight="bold", color=DARK)

    np.random.seed(42)
    cell_colors = ["#3498DB","#E74C3C","#E67E22","#9B59B6","#2ECC71"]
    cell_labels = ["T cell","B cell","Monocyte","NK cell","DC"]
    for _ in range(40):
        cx = np.random.uniform(0.7, 3.3)
        cy = np.random.uniform(0.7, 4.3)
        col = cell_colors[np.random.randint(0, 5)]
        c = Circle((cx, cy), 0.22, facecolor=col, edgecolor="white",
                    linewidth=1, alpha=0.85)
        ax.add_patch(c)
    ax.text(2.0, 0.2, "Looks like a\nhomogeneous soup...",
            ha="center", fontsize=10, color=MID, style="italic")

    # Arrow
    ax.annotate("", xy=(5.5, 2.5), xytext=(3.7, 2.5),
                 arrowprops=dict(arrowstyle="-|>", color=DARK,
                                 lw=2.5, mutation_scale=20))
    ax.text(4.6, 2.85, "scRNA-seq\n+ annotation", ha="center",
            fontsize=11, fontweight="bold", color="#2E86C1")

    # Right: sorted cell types
    sorted_y = [4.2, 3.5, 2.8, 2.1, 1.4]
    for i, (col, lbl) in enumerate(zip(cell_colors, cell_labels)):
        y = sorted_y[i]
        for j in range(6):
            c = Circle((6.2 + j*0.42, y), 0.18, facecolor=col,
                        edgecolor="white", linewidth=1, alpha=0.9)
            ax.add_patch(c)
        ax.text(8.9, y, lbl, va="center", fontsize=11,
                fontweight="bold", color=col)

    ax.text(7.5, 4.85, "Sorted by cell type!", ha="center",
            fontsize=12, fontweight="bold", color=DARK)
    ax.text(7.5, 0.2,
            "Cell type annotation tells us WHICH type each cell is",
            ha="center", fontsize=11, color="#2E86C1", fontweight="bold")

    footer(fig, 2)
    pdf.savefig(fig, bbox_inches="tight"); plt.close()

    # ══════════════════════════════════════════════════════════════════════════
    # SLIDE 3 — Gene expression (for non-biologists)
    # ══════════════════════════════════════════════════════════════════════════
    fig = slide("What is Gene Expression?",
                "The molecular language that defines cell identity",
                accent="#6C3483")

    ax = fig.add_axes([0.02, 0.07, 0.96, 0.79])
    ax.set_xlim(0, 10); ax.set_ylim(0, 5.5)
    ax.set_facecolor(BG); ax.axis("off")

    # Central dogma flow
    steps = [
        (1.1, 3.8, "#2C3E50", "DNA\n(the genome)", "Blueprint stored\nin every cell"),
        (3.8, 3.8, "#8E44AD", "mRNA\n(transcription)", "Temporary copy\nof the recipe"),
        (6.5, 3.8, "#E67E22", "Protein\n(translation)", "Functional molecule\nthat does the work"),
    ]
    for x, y, col, title, desc in steps:
        rect = FancyBboxPatch((x-0.85, y-0.55), 1.7, 1.1,
                               boxstyle="round,pad=0.05",
                               facecolor=col, edgecolor="white",
                               linewidth=1.5, alpha=0.9)
        ax.add_patch(rect)
        ax.text(x, y+0.2, title, ha="center", va="center",
                fontsize=12, fontweight="bold", color="white")
        ax.text(x, y-0.85, desc, ha="center", va="center",
                fontsize=9, color=MID, multialignment="center")

    for x0, x1 in [(2.05, 2.85), (4.75, 5.55)]:
        ax.annotate("", xy=(x1, 3.8), xytext=(x0, 3.8),
                     arrowprops=dict(arrowstyle="-|>", color=DARK,
                                     lw=2, mutation_scale=18))
    ax.text(2.45, 4.05, "transcription", ha="center", fontsize=9, color=MID)
    ax.text(5.15, 4.05, "translation",   ha="center", fontsize=9, color=MID)

    ax.text(5.0, 4.75, "The Central Dogma of Molecular Biology",
            ha="center", fontsize=12, fontweight="bold", color=DARK)

    # Divider
    ax.axhline(2.7, color=LIGHT, linewidth=1.5, linestyle="--")

    # Chemistry analogy
    ax.text(0.3, 2.4, "Chemistry analogy:", fontsize=11,
            fontweight="bold", color="#6C3483")
    ax.text(0.3, 2.0,
            "Gene expression is like a chromatogram — instead of measuring\n"
            "molecular masses, we count how many times each gene's mRNA\n"
            "is detected in a cell. High counts = gene is 'active' in that cell.",
            fontsize=10, color=DARK, va="top")

    # Key insight box
    rect2 = FancyBboxPatch((5.5, 0.2), 4.3, 2.3,
                            boxstyle="round,pad=0.1",
                            facecolor="#EBF5FB", edgecolor="#2E86C1",
                            linewidth=2)
    ax.add_patch(rect2)
    ax.text(7.65, 2.25, "Key insight", ha="center", fontsize=11,
            fontweight="bold", color="#2E86C1")
    ax.text(7.65, 1.7,
            "Different cell types activate\ndifferent sets of genes.\n"
            "This is what gives each cell\ntype its unique identity.",
            ha="center", va="center", fontsize=11, color=DARK,
            multialignment="center")

    footer(fig, 3)
    pdf.savefig(fig, bbox_inches="tight"); plt.close()

    # ══════════════════════════════════════════════════════════════════════════
    # SLIDE 4 — scRNA-seq technology workflow
    # ══════════════════════════════════════════════════════════════════════════
    fig = slide("Single-Cell RNA Sequencing (scRNA-seq)",
                "Measuring gene activity in thousands of individual cells simultaneously",
                accent="#1A5276")

    ax = fig.add_axes([0.02, 0.06, 0.96, 0.80])
    ax.set_xlim(0, 10); ax.set_ylim(0, 5)
    ax.set_facecolor(BG); ax.axis("off")

    steps_wf = [
        (0.7,  2.5, "#E8DAEF", "#8E44AD", "Tissue\nSample",
         "Blood, tumor,\norgan biopsy"),
        (2.5,  2.5, "#D6EAF8", "#2E86C1", "Cell\nDissociation",
         "Break tissue\ninto single cells"),
        (4.3,  2.5, "#D5F5E3", "#27AE60", "Droplet\nCapture",
         "Each cell gets its\nown tiny droplet"),
        (6.1,  2.5, "#FDEBD0", "#E67E22", "Sequencing",
         "Read the mRNA\ninside each droplet"),
        (7.9,  2.5, "#FDEDEC", "#E74C3C", "Count\nMatrix",
         "Cells x Genes\ntable of counts"),
    ]

    for i, (x, y, fc, ec, title, desc) in enumerate(steps_wf):
        circ = Circle((x, y), 0.75, facecolor=fc, edgecolor=ec, linewidth=2.5)
        ax.add_patch(circ)
        ax.text(x, y+0.15, title, ha="center", va="center",
                fontsize=10, fontweight="bold", color=ec, multialignment="center")
        ax.text(x, y-1.2, f"Step {i+1}", ha="center",
                fontsize=9, fontweight="bold", color=ec)
        ax.text(x, y-1.55, desc, ha="center", va="top",
                fontsize=8.5, color=MID, multialignment="center")
        if i < 4:
            ax.annotate("", xy=(x+0.95, y), xytext=(x+0.82, y),
                         arrowprops=dict(arrowstyle="-|>", color=DARK,
                                         lw=1.8, mutation_scale=16))

    # Droplet zoom
    ax.text(4.3, 4.6, "Droplet technology (e.g. 10x Chromium)",
            ha="center", fontsize=10, fontweight="bold", color="#27AE60")
    droplet_ax = fig.add_axes([0.37, 0.68, 0.13, 0.18])
    droplet_ax.set_xlim(0, 3); droplet_ax.set_ylim(0, 3)
    droplet_ax.axis("off")
    # Outer droplet
    outer = Circle((1.5, 1.5), 1.3, facecolor="#D5F5E3",
                    edgecolor="#27AE60", linewidth=2, alpha=0.7)
    droplet_ax.add_patch(outer)
    # Inner cell
    cell = Circle((1.5, 1.5), 0.55, facecolor="#AED6F1",
                   edgecolor="#2E86C1", linewidth=1.5)
    droplet_ax.add_patch(cell)
    droplet_ax.text(1.5, 1.5, "cell", ha="center", va="center",
                    fontsize=8, fontweight="bold", color="#2E86C1")
    # mRNA squiggles
    for dy in [0.85, 1.05, 1.25, 0.95, 1.15]:
        for dx in [-0.6, 0.6]:
            droplet_ax.plot([1.5+dx*0.6, 1.5+dx*0.9],
                             [1.5+dy*0.5, 1.5+dy*0.5],
                             color="#E74C3C", lw=1.5, alpha=0.7)
    droplet_ax.text(1.5, 0.05, "+ barcode", ha="center",
                    fontsize=7, color=MID)

    # Count matrix preview (right side mini heatmap)
    mat_ax = fig.add_axes([0.805, 0.10, 0.17, 0.30])
    np.random.seed(7)
    fake_mat = np.random.randint(0, 50, (6, 5)).astype(float)
    fake_mat[0, 0:2] = [45, 38]   # CD3D high in T cells
    fake_mat[1, 2:4] = [42, 35]   # LYZ high in monocytes
    fake_mat[2, 1]   = 48         # CD79A high in B cells
    im = mat_ax.imshow(fake_mat, cmap="YlOrRd", aspect="auto")
    mat_ax.set_xticks(range(5))
    mat_ax.set_xticklabels(["CD3D","LYZ","CD79A","NKG7","PPBP"],
                            rotation=45, ha="right", fontsize=7)
    mat_ax.set_yticks(range(6))
    mat_ax.set_yticklabels([f"Cell {i+1}" for i in range(6)], fontsize=7)
    mat_ax.set_title("Count matrix\n(cells x genes)", fontsize=8,
                      fontweight="bold", color="#E74C3C")

    footer(fig, 4)
    pdf.savefig(fig, bbox_inches="tight"); plt.close()

    # ══════════════════════════════════════════════════════════════════════════
    # SLIDE 5 — From matrix to UMAP (real data)
    # ══════════════════════════════════════════════════════════════════════════
    fig = slide("From Data Matrix to UMAP: Finding Cell Groups",
                "Dimensionality reduction collapses 20,000 genes into a 2D map — similar cells cluster together",
                accent="#1A5276")

    gs = gridspec.GridSpec(1, 3, left=0.04, right=0.98, top=0.85,
                            bottom=0.10, wspace=0.35, figure=fig)

    # Panel A: PCA variance explained
    ax_pca = fig.add_subplot(gs[0])
    ax_pca.set_facecolor(BG)
    var_ratio = np.array([0.078, 0.061, 0.044, 0.038, 0.029,
                           0.024, 0.020, 0.018, 0.016, 0.014])
    bars = ax_pca.bar(range(1, 11), var_ratio*100,
                       color="#2E86C1", edgecolor="white", alpha=0.85)
    ax_pca.set_xlabel("Principal Component", fontsize=10)
    ax_pca.set_ylabel("Variance Explained (%)", fontsize=10)
    ax_pca.set_title("Step 1: PCA\n(compress 20k genes)", fontsize=11,
                      fontweight="bold")
    ax_pca.spines[["top","right"]].set_visible(False)
    ax_pca.text(5.5, 7.0, "First 10 PCs\ncapture most\nvariation",
                ha="center", fontsize=9, color=MID)

    # Panel B: UMAP unlabelled (Leiden clusters)
    ax_u1 = fig.add_subplot(gs[1])
    ax_u1.set_facecolor(BG)
    umap = adata.obsm["X_umap"]
    leiden = adata.obs["leiden"].values
    for cl in sorted(set(leiden)):
        mask = leiden == cl
        ax_u1.scatter(umap[mask, 0], umap[mask, 1],
                       c=LEIDEN_PAL[cl], s=4, alpha=0.7, rasterized=True)
        cx, cy = umap[mask, 0].mean(), umap[mask, 1].mean()
        ax_u1.text(cx, cy, cl, ha="center", va="center",
                   fontsize=13, fontweight="bold", color="white",
                   path_effects=[pe.withStroke(linewidth=3, foreground="black")])
    ax_u1.set_title("Step 2: UMAP\n(unlabelled clusters)", fontsize=11,
                     fontweight="bold")
    ax_u1.set_xlabel("UMAP 1"); ax_u1.set_ylabel("UMAP 2")
    ax_u1.spines[["top","right"]].set_visible(False)
    ax_u1.text(0.5, -0.15, "Each dot = one cell\nColour = cluster ID",
               ha="center", transform=ax_u1.transAxes, fontsize=9, color=MID)

    # Panel C: UMAP labelled by ground truth
    ax_u2 = fig.add_subplot(gs[2])
    ax_u2.set_facecolor(BG)
    gt = adata.obs["ground_truth"].values
    for ct, color in CT_PAL.items():
        mask = gt == ct
        ax_u2.scatter(umap[mask, 0], umap[mask, 1],
                       c=color, s=4, alpha=0.7, label=ct, rasterized=True)
    ax_u2.set_title("Step 3: Annotated!\n(cell types revealed)", fontsize=11,
                     fontweight="bold", color="#27AE60")
    ax_u2.set_xlabel("UMAP 1"); ax_u2.set_ylabel("UMAP 2")
    ax_u2.spines[["top","right"]].set_visible(False)
    leg = ax_u2.legend(fontsize=6.5, markerscale=3, loc="lower right",
                        framealpha=0.9, ncol=1)
    ax_u2.text(0.5, -0.15, "THIS is the goal of cell-type annotation",
               ha="center", transform=ax_u2.transAxes,
               fontsize=9, color="#27AE60", fontweight="bold")

    footer(fig, 5)
    pdf.savefig(fig, bbox_inches="tight"); plt.close()

    # ══════════════════════════════════════════════════════════════════════════
    # SLIDE 6 — Marker Genes (real violin plot data)
    # ══════════════════════════════════════════════════════════════════════════
    fig = slide("Marker Genes: The Molecular Fingerprints of Cell Identity",
                "Some genes are uniquely and highly expressed in specific cell types — these are 'marker genes'",
                accent="#6C3483")

    gs = gridspec.GridSpec(1, 2, left=0.05, right=0.97,
                            top=0.84, bottom=0.10, wspace=0.35, figure=fig)

    # Left: real dot plot of marker genes
    ax_dot = fig.add_subplot(gs[0])
    ax_dot.set_facecolor(BG)

    markers_dict = {
        "B cells":           ["CD79A", "MS4A1"],
        "CD4 T cells":       ["CD3D",  "IL7R"],
        "CD8 T cells":       ["CD8A",  "NKG7"],
        "NK cells":          ["GNLY",  "NKG7"],
        "CD14+ Monocytes":  ["CD14",  "LYZ"],
        "FCGR3A+ Monocytes":["FCGR3A","MS4A7"],
        "Dendritic cells":   ["FCER1A","CST3"],
        "Megakaryocytes":    ["PPBP",  "PF4"],
    }
    all_markers = ["CD79A","MS4A1","CD3D","IL7R","CD8A",
                    "GNLY","NKG7","CD14","LYZ","FCGR3A",
                    "MS4A7","FCER1A","CST3","PPBP","PF4"]
    cell_types   = list(CT_PAL.keys())

    dot_data = []
    for ct in cell_types:
        mask = adata_raw.obs["ground_truth"] == ct
        if not mask.any():
            continue
        sub = adata_raw[mask]
        for gene in all_markers:
            if gene in adata_raw.var_names:
                X = sub[:, gene].X
                arr = X.toarray().flatten() if scipy_sparse.issparse(X) else np.array(X).flatten()
                expr = arr[arr > 0]
                pct   = 100 * (arr > 0).mean()
                mean  = arr.mean()
                dot_data.append({"ct": ct, "gene": gene,
                                   "pct": pct, "mean": mean})

    df_dot = pd.DataFrame(dot_data)
    ct_idx   = {ct: i for i, ct in enumerate(cell_types)}
    gene_idx = {g: i for i, g in enumerate(all_markers)}

    for _, row in df_dot.iterrows():
        ci = ct_idx.get(row["ct"])
        gi = gene_idx.get(row["gene"])
        if ci is None or gi is None: continue
        size  = max(5, row["pct"] * 2.5)
        color = CT_PAL.get(row["ct"], "gray")
        alpha = min(1.0, row["mean"] / 3)
        ax_dot.scatter(gi, ci, s=size, c=color, alpha=max(0.15, alpha),
                        edgecolors="gray" if alpha < 0.3 else "none",
                        linewidths=0.3)

    ax_dot.set_xticks(range(len(all_markers)))
    ax_dot.set_xticklabels(all_markers, rotation=45, ha="right", fontsize=8)
    ax_dot.set_yticks(range(len(cell_types)))
    ax_dot.set_yticklabels(cell_types, fontsize=8)
    for tick, ct in zip(ax_dot.get_yticklabels(), cell_types):
        tick.set_color(CT_PAL.get(ct, DARK))
        tick.set_fontweight("bold")
    ax_dot.set_title("Dot Plot: Marker Gene Expression\n(size = % cells expressing, colour = expression level)",
                      fontsize=10, fontweight="bold")
    ax_dot.grid(True, alpha=0.2)
    ax_dot.spines[["top","right"]].set_visible(False)

    # Right: concept explanation + legend
    ax_r = fig.add_subplot(gs[1])
    ax_r.set_facecolor(BG); ax_r.axis("off")
    ax_r.set_xlim(0, 10); ax_r.set_ylim(0, 10)

    ax_r.text(5, 9.6, "Classic PBMC Marker Genes", ha="center",
              fontsize=13, fontweight="bold", color=DARK)

    rows_mk = [
        ("CD3D / CD3E",  "T cells",           "#3498DB",  "T-cell receptor complex"),
        ("CD79A / MS4A1","B cells",            "#E74C3C",  "B-cell receptor complex"),
        ("CD14 / LYZ",   "CD14+ Monocytes",   "#E67E22",  "Innate immunity / phagocytosis"),
        ("FCGR3A",       "FCGR3A+ Monocytes", "#F39C12",  "FC receptor (non-classical)"),
        ("GNLY / NKG7",  "NK cells",           "#9B59B6",  "Cytotoxic granule proteins"),
        ("FCER1A",       "Dendritic cells",    "#2ECC71",  "IgE receptor"),
        ("PPBP / PF4",   "Megakaryocytes",     "#95A5A6",  "Platelet factors"),
    ]
    y = 8.8
    ax_r.text(0.3, y+0.4, "Gene(s)", fontsize=9, fontweight="bold", color=DARK)
    ax_r.text(3.5, y+0.4, "Cell Type", fontsize=9, fontweight="bold", color=DARK)
    ax_r.text(6.8, y+0.4, "Function", fontsize=9, fontweight="bold", color=DARK)
    for gene, ct, col, fn in rows_mk:
        rect = FancyBboxPatch((0.1, y-0.38), 9.8, 0.7,
                               boxstyle="round,pad=0.02",
                               facecolor=col, edgecolor="white",
                               linewidth=0.5, alpha=0.15)
        ax_r.add_patch(rect)
        circ = Circle((0.55, y+0.0), 0.22, facecolor=col, edgecolor="white")
        ax_r.add_patch(circ)
        ax_r.text(1.1, y+0.0, gene, fontsize=9, fontweight="bold", color=DARK, va="center")
        ax_r.text(3.5, y+0.0, ct,   fontsize=9, color=col, va="center", fontweight="bold")
        ax_r.text(6.8, y+0.0, fn,   fontsize=8, color=MID, va="center")
        y -= 1.05

    ax_r.text(5, 0.5,
              "High expression of a marker gene in a cluster = strong evidence for that cell type",
              ha="center", fontsize=9, color="#6C3483", fontweight="bold",
              style="italic")

    footer(fig, 6)
    pdf.savefig(fig, bbox_inches="tight"); plt.close()

    # ══════════════════════════════════════════════════════════════════════════
    # SLIDE 7 — Zero-Shot Annotation
    # ══════════════════════════════════════════════════════════════════════════
    fig = slide("Method 1: Zero-Shot Annotation with Marker Genes",
                "Annotate without training data — use biological prior knowledge directly",
                accent="#8E44AD")

    ax = fig.add_axes([0.02, 0.06, 0.96, 0.80])
    ax.set_xlim(0, 10); ax.set_ylim(0, 5.5)
    ax.set_facecolor(BG); ax.axis("off")

    # What does 'zero-shot' mean?
    rect_zs = FancyBboxPatch((0.1, 4.5), 4.5, 0.8,
                              boxstyle="round,pad=0.08",
                              facecolor="#F4ECF7", edgecolor="#8E44AD", linewidth=2)
    ax.add_patch(rect_zs)
    ax.text(2.35, 4.9, '"Zero-shot" = no training data needed',
            ha="center", va="center", fontsize=11, fontweight="bold", color="#8E44AD")

    rect_zs2 = FancyBboxPatch((5.0, 4.5), 4.8, 0.8,
                               boxstyle="round,pad=0.08",
                               facecolor="#EBF5FB", edgecolor="#2E86C1", linewidth=2)
    ax.add_patch(rect_zs2)
    ax.text(7.4, 4.9, "Works like a human expert looking up a reference book",
            ha="center", va="center", fontsize=11, color="#2E86C1")

    # Pipeline flow diagram
    steps_zs = [
        (1.0, 3.0, "#D7BDE2", "#8E44AD", "UMAP with\nLeiden clusters\n(unlabelled)"),
        (3.2, 3.0, "#D6EAF8", "#2E86C1", "Find top marker\ngenes per cluster\n(rank_genes_groups)"),
        (5.4, 3.0, "#FDEBD0", "#E67E22", "Known marker\ngene dictionary\nOR LLM (Claude)"),
        (7.6, 3.0, "#D5F5E3", "#27AE60", "Cluster labelled\nwith cell type\nname"),
    ]

    for i, (x, y, fc, ec, txt) in enumerate(steps_zs):
        rect = FancyBboxPatch((x-0.85, y-0.65), 1.7, 1.3,
                               boxstyle="round,pad=0.08",
                               facecolor=fc, edgecolor=ec, linewidth=2)
        ax.add_patch(rect)
        ax.text(x, y+0.1, txt, ha="center", va="center",
                fontsize=9.5, fontweight="bold", color=ec, multialignment="center")
        if i < 3:
            ax.annotate("", xy=(x+1.0, y), xytext=(x+0.9, y),
                         arrowprops=dict(arrowstyle="-|>", color=DARK,
                                         lw=2, mutation_scale=16))

    # Example annotation
    ax.text(5.0, 1.8, "Example: Cluster 3 has top genes CD79A, MS4A1, CD79B",
            ha="center", fontsize=10, color=DARK, fontweight="bold")

    example_steps = [
        (1.5, 0.9, "#FDFEFE", "#95A5A6", "Cluster 3\ntop genes:\nCD79A, MS4A1"),
        (4.0, 0.9, "#EBF5FB", "#2E86C1", "Known markers:\nCD79A = B cells\nMS4A1 = B cells"),
        (6.5, 0.9, "#D5F5E3", "#27AE60", 'Annotation:\n"B cells"\nConfidence: HIGH'),
    ]
    for i, (x, y, fc, ec, txt) in enumerate(example_steps):
        rect = FancyBboxPatch((x-1.0, y-0.6), 2.0, 1.2,
                               boxstyle="round,pad=0.05",
                               facecolor=fc, edgecolor=ec, linewidth=1.5)
        ax.add_patch(rect)
        ax.text(x, y+0.05, txt, ha="center", va="center",
                fontsize=9, color=ec, fontweight="bold", multialignment="center")
        if i < 2:
            ax.annotate("", xy=(x+1.15, y), xytext=(x+1.05, y),
                         arrowprops=dict(arrowstyle="-|>", color=DARK,
                                         lw=1.5, mutation_scale=14))

    # LLM variant note
    rect_llm = FancyBboxPatch((8.2, 0.2), 1.7, 1.7,
                               boxstyle="round,pad=0.05",
                               facecolor="#FEF9E7", edgecolor="#F39C12", linewidth=2)
    ax.add_patch(rect_llm)
    ax.text(9.05, 1.15,
            "LLM variant:\nSend marker genes\nto Claude/Llama\nGet label back",
            ha="center", va="center", fontsize=8, color="#E67E22",
            fontweight="bold", multialignment="center")
    ax.text(9.05, 0.35, "This project!", ha="center",
            fontsize=8, color="#E67E22", fontweight="bold")

    footer(fig, 7)
    pdf.savefig(fig, bbox_inches="tight"); plt.close()

    # ══════════════════════════════════════════════════════════════════════════
    # SLIDE 8 — Reference Mapping
    # ══════════════════════════════════════════════════════════════════════════
    fig = slide("Method 2: Reference Mapping",
                "Compare your cells to a large, already-annotated atlas and borrow their labels",
                accent="#1A5276")

    ax = fig.add_axes([0.02, 0.06, 0.96, 0.80])
    ax.set_xlim(0, 10); ax.set_ylim(0, 5.5)
    ax.set_facecolor(BG); ax.axis("off")

    # GPS analogy
    rect_gps = FancyBboxPatch((0.1, 4.7), 9.8, 0.65,
                               boxstyle="round,pad=0.06",
                               facecolor="#EBF5FB", edgecolor="#2E86C1", linewidth=2)
    ax.add_patch(rect_gps)
    ax.text(5.0, 5.03,
            "Analogy: Reference mapping is like GPS navigation."
            " Your new cells are an unknown location — "
            "the reference atlas is the map.",
            ha="center", va="center", fontsize=10.5, color="#2E86C1",
            fontweight="bold")

    # Left: reference atlas (UMAP)
    np.random.seed(1)
    n_ref = 300
    ref_types = ["T cells","B cells","Monocytes","NK cells","DC"]
    ref_cols   = ["#3498DB","#E74C3C","#E67E22","#9B59B6","#2ECC71"]
    ref_centres = [(1.2, 2.8),(2.5, 1.5),(0.8, 1.2),(2.0, 3.5),(3.0, 2.2)]
    ref_x, ref_y, ref_c = [], [], []
    for centre, col, lbl in zip(ref_centres, ref_cols, ref_types):
        nx = 60
        xs = np.random.normal(centre[0], 0.25, nx)
        ys = np.random.normal(centre[1], 0.25, nx)
        ref_x.extend(xs); ref_y.extend(ys)
        ref_c.extend([col]*nx)

    ref_ax = fig.add_axes([0.04, 0.10, 0.28, 0.55])
    ref_ax.scatter(ref_x, ref_y, c=ref_c, s=18, alpha=0.75)
    for centre, col, lbl in zip(ref_centres, ref_cols, ref_types):
        ref_ax.text(centre[0], centre[1]+0.35, lbl,
                    ha="center", fontsize=7.5, color=col, fontweight="bold")
    ref_ax.set_title("Reference Atlas\n(pre-annotated, e.g. 700k cells)", fontsize=9,
                      fontweight="bold", color="#1A5276")
    ref_ax.set_xticks([]); ref_ax.set_yticks([])
    ref_ax.spines[:].set_visible(False)
    ref_ax.set_facecolor("#EBF5FB")

    # Middle: query dataset
    q_ax = fig.add_axes([0.37, 0.10, 0.24, 0.55])
    q_x = np.random.uniform(0.2, 3.0, 120)
    q_y = np.random.uniform(0.5, 3.5, 120)
    q_ax.scatter(q_x, q_y, c=DARK, s=18, alpha=0.5)
    q_ax.set_title("Your New Data\n(unannotated query cells)", fontsize=9,
                    fontweight="bold", color=DARK)
    q_ax.set_xticks([]); q_ax.set_yticks([])
    q_ax.spines[:].set_visible(False)
    q_ax.set_facecolor("#F2F3F4")
    q_ax.text(1.6, 0.1, "?", ha="center", fontsize=24,
               fontweight="bold", color=MID, alpha=0.5)

    # Integration arrow
    fig.text(0.635, 0.42, "Integration\n+\nLabel transfer", ha="center",
             fontsize=10, fontweight="bold", color="#E67E22",
             bbox=dict(facecolor="#FDEBD0", edgecolor="#E67E22",
                        boxstyle="round,pad=0.3", linewidth=1.5))
    ax.annotate("", xy=(7.0, 2.8), xytext=(6.2, 2.8),
                 arrowprops=dict(arrowstyle="-|>", color="#E67E22",
                                 lw=2.5, mutation_scale=18))

    # Right: annotated output
    out_ax = fig.add_axes([0.71, 0.10, 0.27, 0.55])
    assigned_cols = []
    for qx, qy in zip(q_x, q_y):
        dists = [((qx-cx)**2+(qy-cy)**2)**0.5 for cx, cy in ref_centres]
        assigned_cols.append(ref_cols[np.argmin(dists)])
    out_ax.scatter(q_x, q_y, c=assigned_cols, s=18, alpha=0.8)
    for centre, col, lbl in zip(ref_centres, ref_cols, ref_types):
        m = [i for i, c in enumerate(assigned_cols) if c == col]
        if m:
            cx = np.mean([q_x[i] for i in m])
            cy = np.mean([q_y[i] for i in m])
            out_ax.text(cx, cy+0.25, lbl, ha="center",
                         fontsize=7.5, color=col, fontweight="bold")
    out_ax.set_title("Annotated Output\n(labels transferred from reference)", fontsize=9,
                      fontweight="bold", color="#27AE60")
    out_ax.set_xticks([]); out_ax.set_yticks([])
    out_ax.spines[:].set_visible(False)
    out_ax.set_facecolor("#EAFAF1")

    # Key tools callout
    ax.text(5.0, 0.4,
            "Tools used in this project: CellTypist (Claude) | Scanorama+KNN (Gemma) | Centroid dot-product (Llama)",
            ha="center", fontsize=9.5, color=DARK,
            bbox=dict(facecolor="#F8F9FA", edgecolor=LIGHT, boxstyle="round,pad=0.3"))

    footer(fig, 8)
    pdf.savefig(fig, bbox_inches="tight"); plt.close()

    # ══════════════════════════════════════════════════════════════════════════
    # SLIDE 9 — Why It Matters
    # ══════════════════════════════════════════════════════════════════════════
    fig = slide("Why Does Cell-Type Annotation Matter?",
                "Annotated cells unlock biological and clinical insights",
                accent="#1E8449")

    ax = fig.add_axes([0.02, 0.06, 0.96, 0.80])
    ax.set_xlim(0, 10); ax.set_ylim(0, 5.5)
    ax.set_facecolor(BG); ax.axis("off")

    apps = [
        (1.2, 4.2, "#D6EAF8", "#2E86C1",
         "Disease Research",
         "Identify which cell types are\nexpanded or depleted in cancer,\nautoimmune disease, or infection"),
        (5.0, 4.2, "#D5F5E3", "#27AE60",
         "Drug Target Discovery",
         "Find the exact cell type\nwhere a drug acts — or\nshould act — in the body"),
        (8.8, 4.2, "#FDEBD0", "#E67E22",
         "Immune Profiling",
         "Track how T, B, NK cells\nchange before and after\nvaccination or treatment"),
        (1.2, 2.0, "#F4ECF7", "#8E44AD",
         "Cell Atlas Projects",
         "Build comprehensive maps\nof every cell type in the\nhuman body (Human Cell Atlas)"),
        (5.0, 2.0, "#FDEDEC", "#E74C3C",
         "Biomarker Discovery",
         "Identify rare cell populations\nthat predict patient outcomes\nor disease progression"),
        (8.8, 2.0, "#FEF9E7", "#F39C12",
         "Drug Development",
         "Understand off-target effects:\nwhich cell types are affected\nby a new compound"),
    ]

    for x, y, fc, ec, title, desc in apps:
        rect = FancyBboxPatch((x-1.5, y-0.9), 3.0, 1.8,
                               boxstyle="round,pad=0.1",
                               facecolor=fc, edgecolor=ec, linewidth=2)
        ax.add_patch(rect)
        ax.text(x, y+0.55, title, ha="center", va="center",
                fontsize=11, fontweight="bold", color=ec)
        ax.text(x, y-0.2, desc, ha="center", va="center",
                fontsize=9, color=DARK, multialignment="center")

    # Bottom callout
    rect_b = FancyBboxPatch((0.5, 0.15), 9.0, 0.65,
                             boxstyle="round,pad=0.08",
                             facecolor="#1E8449", edgecolor="white", linewidth=1)
    ax.add_patch(rect_b)
    ax.text(5.0, 0.48,
            "Without cell-type annotation, single-cell data is just 20,000 "
            "numbers per cell — annotation gives it biological meaning.",
            ha="center", va="center", fontsize=10.5, color="white",
            fontweight="bold")

    footer(fig, 9)
    pdf.savefig(fig, bbox_inches="tight"); plt.close()

    # ══════════════════════════════════════════════════════════════════════════
    # SLIDE 10 — Summary comparison table
    # ══════════════════════════════════════════════════════════════════════════
    fig = slide("Summary: Zero-Shot vs Reference Mapping",
                "Two fundamentally different strategies for the same goal",
                accent="#1A252F")

    ax = fig.add_axes([0.03, 0.08, 0.94, 0.78])
    ax.set_facecolor(BG); ax.set_xticks([]); ax.set_yticks([])
    for sp in ax.spines.values(): sp.set_visible(False)

    compare_rows = [
        ["", "Zero-Shot (Marker Genes)", "Reference Mapping"],
        ["Core idea",
         "Match cluster's top genes to\nknown marker gene lists",
         "Align cells to a pre-annotated\nreference atlas"],
        ["Prior knowledge\nneeded",
         "Curated marker gene lists\n(literature / LLM knowledge)",
         "A labelled reference dataset\n(e.g. Human Cell Atlas)"],
        ["Granularity",
         "Cluster-level label\n(all cells in a cluster get same label)",
         "Cell-level label\n(each cell annotated independently)"],
        ["Strengths",
         "- No reference data required\n- Fast and interpretable\n- Works with any organism",
         "- Cell-level resolution\n- Handles novel datasets well\n- Leverages large training sets"],
        ["Weaknesses",
         "- Limited by cluster resolution\n- Misses rare cell types\n- Requires good marker genes",
         "- Needs a good reference\n- Batch effects can mislead\n- Reference may be incomplete"],
        ["Accuracy\n(PBMC3k test)",
         "~85%  (Claude & Llama)\n76%   (Gemma)",
         "~89%  (Claude / CellTypist)\n77%   (Gemma / Scanorama)\n73%   (Llama / dot-product)"],
        ["Best when...",
         "Reference data unavailable\nor working with novel tissue",
         "High accuracy needed\nand a good reference exists"],
    ]

    col_w   = [0.22, 0.39, 0.39]
    row_h   = 0.105
    y_start = 0.95
    col_colors = [DARK, "#1B4F72", "#1A5276"]

    for r_idx, row in enumerate(compare_rows):
        y = y_start - r_idx * row_h
        x = 0.0
        for c_idx, (cell, cw) in enumerate(zip(row, col_w)):
            if r_idx == 0:
                fc = col_colors[c_idx]; tc = "white"; fs = 12; fw = "bold"
            elif r_idx % 2 == 0:
                fc = "#EAECEE" if c_idx == 0 else "#EBF5FB" if c_idx == 1 else "#E8F8F5"
                tc = DARK; fs = 9.5; fw = "normal"
            else:
                fc = "#D5D8DC" if c_idx == 0 else "#D6EAF8" if c_idx == 1 else "#D5F5E3"
                tc = DARK; fs = 9.5; fw = "normal"
            rect = FancyBboxPatch((x, y-row_h), cw, row_h,
                                   boxstyle="square,pad=0", linewidth=0.5,
                                   edgecolor="white", facecolor=fc,
                                   transform=ax.transAxes, clip_on=False)
            ax.add_patch(rect)
            ax.text(x + cw/2, y - row_h/2, cell,
                    transform=ax.transAxes, ha="center", va="center",
                    fontsize=fs, fontweight=fw, color=tc,
                    multialignment="center")
            x += cw

    # Take-home
    fig.text(0.5, 0.04,
             "Both methods are complementary — for best results, use both and compare!",
             ha="center", fontsize=11, color="#1A5276", fontweight="bold",
             style="italic")

    footer(fig, 10)
    pdf.savefig(fig, bbox_inches="tight"); plt.close()

print(f"Saved: {OUT}")
from pathlib import Path
print(f"Size : {Path(OUT).stat().st_size//1024} KB")
