"""Analysis pipeline execution module."""

from __future__ import annotations

from typing import Any

import pandas as pd
import streamlit as st

from app.services.clustering import cluster_cells
from app.services.dimensionality import run_pca, run_tsne, run_umap
from app.services.markers import find_markers
from app.services.preprocessing import run_qc


def run_analysis_pipeline(
    data: pd.DataFrame,
    min_genes_per_cell: int,
    min_cells_per_gene: int,
    n_pca_components: int,
    umap_n_neighbors: int,
    umap_min_dist: float,
    tsne_perplexity: int,
    n_clusters_override: int | None,
    top_n_markers: int,
) -> dict[str, Any]:
    """Execute complete scRNA-seq analysis pipeline.

    Runs QC, normalization, PCA, dimensionality reduction, clustering,
    and marker gene detection in sequence.

    Args:
        data: Gene expression matrix (cells × genes)
        min_genes_per_cell: Minimum genes per cell for QC
        min_cells_per_gene: Minimum cells per gene for QC
        n_pca_components: Number of PCA components
        umap_n_neighbors: UMAP neighbor parameter
        umap_min_dist: UMAP minimum distance
        tsne_perplexity: t-SNE perplexity parameter
        n_clusters_override: Override auto-detected cluster count (0 = auto)
        top_n_markers: Number of markers per cluster

    Returns:
        Dictionary with complete analysis results including:
        - qc: Quality control summary
        - pca: PCA results
        - umap: UMAP coordinates
        - tsne: t-SNE coordinates
        - clusters: Clustering results
        - markers: Top marker genes per cluster
        - variance_explained: PCA cumulative variance %
    """
    # Quality control
    qc = run_qc(
        data,
        min_genes_per_cell=min_genes_per_cell,
        min_cells_per_gene=min_cells_per_gene,
    )

    # Dimensionality reduction - PCA
    pca = run_pca(qc.normalized, n_components=n_pca_components)

    # Dimensionality reduction - UMAP and t-SNE
    umap = run_umap(pca.components, n_neighbors=umap_n_neighbors, min_dist=umap_min_dist)
    tsne = run_tsne(pca.components, perplexity=tsne_perplexity)

    # Clustering
    n_clusters = None if n_clusters_override == 0 else int(n_clusters_override)
    clusters = cluster_cells(pca.components, n_clusters=n_clusters)

    # Marker detection
    markers = find_markers(qc.counts, clusters.labels, top_n=top_n_markers)

    # Assemble results
    results = {
        "qc": qc.to_summary(),
        "pca": pca.to_dict(),
        "umap": umap.to_dict(),
        "tsne": tsne.to_dict(),
        "clusters": clusters.to_dict(),
        "markers": markers,
        "variance_explained": float(pca.cumulative_variance[-1] * 100),
    }

    return results
