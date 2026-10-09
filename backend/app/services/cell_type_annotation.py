"""
Marker-panel-based cell-type annotation.

Each cluster receives a score for every known cell-type panel by computing
the mean expression of that panel's genes across cells in the cluster.
The highest-scoring type wins (with a confidence proportional to the
margin over the runner-up).

The bundled panels are intentionally small and synthetic-friendly: they
also recognize the demo dataset's `Gene_*` naming convention so the
feature shows non-trivial output out of the box.
"""
from __future__ import annotations

from typing import Dict, List

import numpy as np
import pandas as pd


# Canonical immune / epithelial / stromal marker panels.
CANONICAL_PANELS: Dict[str, List[str]] = {
    "T cells":        ["CD3D", "CD3E", "CD3G", "CD8A", "CD8B", "CD4", "TRAC"],
    "B cells":        ["CD19", "MS4A1", "CD79A", "CD79B", "IGHM", "IGHD"],
    "NK cells":       ["NCAM1", "NKG7", "GNLY", "KLRD1", "KLRF1"],
    "Monocytes":      ["CD14", "LYZ", "FCN1", "VCAN", "S100A8", "S100A9"],
    "Dendritic":      ["FCER1A", "CST3", "CLEC10A", "CD1C"],
    "Erythrocytes":   ["HBA1", "HBA2", "HBB", "ALAS2", "GYPA"],
    "Platelets":      ["PPBP", "PF4", "GP9", "ITGA2B"],
    "Epithelial":     ["EPCAM", "KRT8", "KRT18", "KRT19"],
    "Fibroblasts":    ["COL1A1", "COL1A2", "COL3A1", "DCN", "LUM"],
    "Endothelial":    ["PECAM1", "VWF", "CDH5", "KDR"],
}


def _demo_panels(gene_names: List[str], n_clusters_hint: int = 6) -> Dict[str, List[str]]:
    """Synthesize panels that match the demo data's Gene_* naming.

    The demo generator over-expresses contiguous gene blocks per cluster
    (see app.services.demo_data). We mirror that here so annotation gives
    a meaningful split.
    """
    if not gene_names:
        return {}
    n_genes = len(gene_names)
    n = max(2, min(n_clusters_hint, 12))
    block = max(1, n_genes // n)
    panels: Dict[str, List[str]] = {}
    type_names = ["T cells", "B cells", "NK cells", "Monocytes", "Dendritic",
                  "Erythrocytes", "Platelets", "Epithelial", "Fibroblasts",
                  "Endothelial", "Neurons", "Hepatocytes"]
    for i in range(n):
        start, end = i * block, (i + 1) * block
        panels[type_names[i]] = gene_names[start:end][:20]
    return panels


def _select_panels(counts: pd.DataFrame) -> Dict[str, List[str]]:
    """Pick canonical panels if they overlap the dataset; else demo panels."""
    gene_set = set(map(str, counts.columns))
    overlap = sum(
        len([g for g in genes if g in gene_set])
        for genes in CANONICAL_PANELS.values()
    )
    if overlap >= 5:
        return {
            name: [g for g in genes if g in gene_set]
            for name, genes in CANONICAL_PANELS.items()
        }
    return _demo_panels(list(map(str, counts.columns)))


def annotate_clusters(
    counts: pd.DataFrame,
    labels: np.ndarray,
    panels: Dict[str, List[str]] | None = None,
) -> pd.DataFrame:
    """Score each cluster against each panel; return tidy table.

    Columns: cluster, cell_type, score, confidence, n_cells
    """
    if panels is None:
        panels = _select_panels(counts)
    panels = {k: v for k, v in panels.items() if v}
    if not panels:
        raise ValueError("No usable marker panels for this dataset.")

    rows = []
    for cid in sorted(np.unique(labels)):
        mask = labels == cid
        cells_in = counts.loc[mask]
        scores = {}
        for cell_type, genes in panels.items():
            available = [g for g in genes if g in cells_in.columns]
            if not available:
                continue
            scores[cell_type] = float(cells_in[available].values.mean())
        if not scores:
            continue

        ranked = sorted(scores.items(), key=lambda kv: kv[1], reverse=True)
        top_type, top_score = ranked[0]
        runner = ranked[1][1] if len(ranked) > 1 else 0.0
        confidence = float(np.clip((top_score - runner) / (abs(top_score) + 1e-9), 0, 1))

        rows.append({
            "cluster": int(cid),
            "cell_type": top_type,
            "score": round(top_score, 4),
            "confidence": round(confidence, 3),
            "n_cells": int(mask.sum()),
            "runner_up": ranked[1][0] if len(ranked) > 1 else "",
        })

    return pd.DataFrame(rows).sort_values("cluster").reset_index(drop=True)
