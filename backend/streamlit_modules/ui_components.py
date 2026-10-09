"""UI components and sidebar controls."""

from __future__ import annotations

from typing import Any

import streamlit as st


def render_sidebar_controls() -> dict[str, Any]:
    """Render sidebar controls and return configuration.

    Returns:
        Dictionary with all user-selected parameters:
        - data_source: "Demo dataset" or "Upload CSV"
        - demo_options: Demo parameters (n_cells, n_genes, n_clusters, seed)
        - uploaded_file: File upload object if CSV selected
        - min_genes_per_cell: QC parameter
        - min_cells_per_gene: QC parameter
        - n_pca_components: PCA components
        - umap_n_neighbors: UMAP neighbors
        - umap_min_dist: UMAP minimum distance
        - tsne_perplexity: t-SNE perplexity
        - n_clusters_override: Force cluster count (0 = auto)
        - top_n_markers: Markers per cluster
        - run_button: Whether analysis was requested
    """
    sidebar = st.sidebar
    sidebar.header("Dataset selection")
    data_source = sidebar.radio("Data source", ["Demo dataset", "Upload CSV"])

    demo_options = {}
    uploaded_file = None
    if data_source == "Demo dataset":
        demo_options["n_cells"] = sidebar.slider("Cells", 100, 1800, 600, step=100)
        demo_options["n_genes"] = sidebar.slider("Genes", 100, 4000, 2500, step=100)
        demo_options["n_clusters"] = sidebar.slider("True clusters", 2, 12, 6)
        demo_options["seed"] = sidebar.number_input(
            "Random seed", min_value=0, max_value=9999, value=42
        )
    else:
        uploaded_file = sidebar.file_uploader("Upload counts matrix CSV", type=["csv"])

    sidebar.markdown("---")
    sidebar.header("Pipeline settings")
    min_genes_per_cell = sidebar.number_input(
        "Min genes per cell", min_value=1, max_value=1000, value=150
    )
    min_cells_per_gene = sidebar.number_input(
        "Min cells per gene", min_value=1, max_value=1000, value=3
    )
    n_pca_components = sidebar.number_input(
        "PCA components", min_value=2, max_value=100, value=50
    )
    umap_n_neighbors = sidebar.number_input(
        "UMAP neighbors", min_value=2, max_value=200, value=15
    )
    umap_min_dist = sidebar.slider(
        "UMAP min dist", 0.0, 1.0, 0.1, step=0.05
    )
    tsne_perplexity = sidebar.number_input(
        "t-SNE perplexity", min_value=5, max_value=100, value=30
    )
    n_clusters_override = sidebar.number_input(
        "Force clusters (0 = auto)", min_value=0, max_value=20, value=0
    )
    top_n_markers = sidebar.number_input(
        "Marker genes per cluster", min_value=1, max_value=50, value=15
    )

    run_button = sidebar.button("Run analysis")

    return {
        "data_source": data_source,
        "demo_options": demo_options,
        "uploaded_file": uploaded_file,
        "min_genes_per_cell": min_genes_per_cell,
        "min_cells_per_gene": min_cells_per_gene,
        "n_pca_components": n_pca_components,
        "umap_n_neighbors": umap_n_neighbors,
        "umap_min_dist": umap_min_dist,
        "tsne_perplexity": tsne_perplexity,
        "n_clusters_override": n_clusters_override,
        "top_n_markers": top_n_markers,
        "run_button": run_button,
    }
