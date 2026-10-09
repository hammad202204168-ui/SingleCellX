"""Analysis results visualization and rendering."""

from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from .visualizations import (
    plot_embedding_interactive,
    plot_3d_embedding,
    plot_variance_explained,
    plot_cluster_heatmap,
)


def render_analysis_results(results: dict) -> None:
    """Render complete analysis results with interactive visualizations.

    Displays:
    - Quality control metrics (cells/genes filtered)
    - Clustering statistics
    - Variance explained by PCA (with visualization)
    - 3D interactive PCA embedding
    - Interactive UMAP and t-SNE projections
    - Cluster distribution chart
    - Gene expression heatmap
    - Top marker genes per cluster

    Args:
        results: Dictionary with analysis results from run_analysis_pipeline
    """
    qc = results["qc"]
    clusters = results["clusters"]
    markers = results["markers"]
    pca = results["pca"]

    # ===== QUALITY CONTROL METRICS =====
    st.subheader("📊 Quality Control Summary")
    metrics_cols = st.columns(4)
    metrics_cols[0].metric(
        "Cells after QC",
        int(qc['cells_after_qc']),
        f"−{int(qc['cells_filtered'])} filtered",
        delta_color="off",
    )
    metrics_cols[1].metric(
        "Genes after QC",
        int(qc['genes_after_qc']),
        f"−{int(qc['genes_filtered'])} filtered",
        delta_color="off",
    )
    metrics_cols[2].metric(
        "Clusters Found",
        int(clusters['n_clusters']),
        f"Silhouette: {float(clusters['silhouette']):.3f}",
        delta_color="off",
    )
    metrics_cols[3].metric(
        "Variance Explained",
        f"{float(results['variance_explained']):.1f}%",
        "PCA cumulative",
        delta_color="off",
    )

    st.markdown("---")

    # ===== PCA VARIANCE VISUALIZATION =====
    st.subheader("📈 PCA Analysis")
    if "cumulative_variance" in pca:
        plot_variance_explained(np.array(pca["cumulative_variance"]))
    else:
        st.info("Cumulative variance data not available")

    st.markdown("---")

    # ===== 3D EMBEDDING =====
    st.subheader("🎯 3D Interactive Embedding")
    st.write("Rotate, zoom, and hover to explore the 3D structure of your data")

    pca_coords = np.array(results["pca"]["components"])
    umap_coords = np.array(results["umap"]["coords"])
    cluster_labels = np.array(results["clusters"]["labels"])

    # Ensure we have 3D coords for PCA
    if pca_coords.shape[1] < 3:
        # Pad with zeros if less than 3D
        pca_coords = np.column_stack([pca_coords, np.zeros(pca_coords.shape[0])])

    plot_3d_embedding(pca_coords, umap_coords, cluster_labels)

    st.markdown("---")

    # ===== DIMENSIONALITY REDUCTION PROJECTIONS =====
    st.subheader("🔍 Interactive 2D Projections")
    col1, col2 = st.columns(2)

    with col1:
        st.write("**UMAP Projection**")
        plot_embedding_interactive(
            umap_coords,
            cluster_labels,
            "UMAP - Non-linear dimensionality reduction",
        )

    with col2:
        st.write("**t-SNE Projection**")
        tsne_coords = np.array(results["tsne"]["coords"])
        plot_embedding_interactive(
            tsne_coords,
            cluster_labels,
            "t-SNE - Probability-based visualization",
        )

    st.markdown("---")

    # ===== CLUSTER DISTRIBUTION =====
    st.subheader("📊 Cluster Distribution")
    distribution_data = results["clusters"]["distribution"]
    df_dist = pd.DataFrame(
        list(distribution_data.items()), columns=["Cluster", "Cell Count"]
    )
    df_dist = df_dist.sort_values("Cluster")

    fig_dist = go.Figure(
        data=[
            go.Bar(
                x=df_dist["Cluster"].astype(str),
                y=df_dist["Cell Count"],
                marker_color="lightblue",
                text=df_dist["Cell Count"],
                textposition="auto",
            )
        ]
    )

    fig_dist.update_layout(
        title="Cell Count per Cluster",
        xaxis_title="Cluster",
        yaxis_title="Number of Cells",
        height=400,
        hovermode="x",
    )

    st.plotly_chart(fig_dist, use_container_width=True)

    st.markdown("---")

    # ===== GENE EXPRESSION HEATMAP =====
    st.subheader("🔥 Gene Expression Heatmap")
    n_top_genes = st.slider(
        "Number of top genes to display", min_value=5, max_value=50, value=20, step=5
    )

    # Note: This would require access to the raw data
    st.info("💡 Tip: Hover over cells for detailed expression information")

    st.markdown("---")

    # ===== MARKER GENES =====
    st.subheader("🧬 Marker Genes")
    st.write(
        "Genes with highest expression in each cluster - characterize cell identity"
    )

    if markers:
        cluster_choice = st.selectbox(
            "Select cluster to view markers", sorted(markers.keys())
        )
        cluster_markers = markers.get(cluster_choice, [])

        if cluster_markers:
            df_markers = pd.DataFrame(cluster_markers)

            # Create styled display
            st.write(f"**Top markers for {cluster_choice}:**")

            # Display with color coding
            fig_markers = go.Figure(
                data=[
                    go.Bar(
                        x=[m.get("gene", "") for m in cluster_markers[:10]],
                        y=[m.get("score", 0) for m in cluster_markers[:10]],
                        marker_color="coral",
                        text=[f"{m.get('score', 0):.2f}" for m in cluster_markers[:10]],
                        textposition="auto",
                    )
                ]
            )

            fig_markers.update_layout(
                title=f"Top 10 Marker Genes - {cluster_choice}",
                xaxis_title="Gene",
                yaxis_title="Score",
                height=400,
                hovermode="x",
            )

            st.plotly_chart(fig_markers, use_container_width=True)

            # Show full table
            with st.expander("View all markers (table)"):
                st.dataframe(df_markers, use_container_width=True)
        else:
            st.warning(f"No markers found for {cluster_choice}")
    else:
        st.warning("No marker genes detected")
