"""Visualization module for analysis results."""

from __future__ import annotations

import matplotlib.pyplot as plt
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st


def plot_embedding(
    coords: np.ndarray, labels: np.ndarray | None, title: str
) -> None:
    """Plot 2D embedding with optional cluster labels.

    Args:
        coords: Array of shape (n_samples, 2) with 2D coordinates
        labels: Optional array of cluster labels for coloring
        title: Plot title
    """
    fig, ax = plt.subplots(figsize=(6, 5))
    if labels is not None:
        scatter = ax.scatter(
            coords[:, 0], coords[:, 1], c=labels, cmap="tab10", s=40, alpha=0.85
        )
        legend1 = ax.legend(
            *scatter.legend_elements(), title="Cluster", loc="best", fontsize="small"
        )
        ax.add_artist(legend1)
    else:
        ax.scatter(coords[:, 0], coords[:, 1], s=40, alpha=0.85)

    ax.set_title(title)
    ax.set_xlabel("Component 1")
    ax.set_ylabel("Component 2")
    ax.grid(True, linestyle="--", alpha=0.25)
    st.pyplot(fig)


def plot_embedding_interactive(
    coords: np.ndarray, labels: np.ndarray | None, title: str
) -> None:
    """Plot interactive 2D embedding using Plotly.

    Args:
        coords: Array of shape (n_samples, 2) with 2D coordinates
        labels: Optional array of cluster labels for coloring
        title: Plot title
    """
    df_plot = {
        "x": coords[:, 0],
        "y": coords[:, 1],
        "cluster": labels.astype(int) if labels is not None else [0] * len(coords),
    }

    fig = px.scatter(
        df_plot,
        x="x",
        y="y",
        color="cluster",
        title=title,
        labels={"x": "Component 1", "y": "Component 2"},
        color_continuous_scale="Viridis",
        opacity=0.7,
        hover_data={"x": ":.3f", "y": ":.3f", "cluster": True},
    )

    fig.update_traces(marker=dict(size=6))
    fig.update_layout(
        hovermode="closest",
        height=500,
        showlegend=True,
    )

    st.plotly_chart(fig, use_column_width=True)


def plot_3d_embedding(
    coords_pca: np.ndarray,
    coords_umap: np.ndarray,
    labels: np.ndarray | None,
) -> None:
    """Plot 3D PCA-UMAP hybrid embedding.

    Args:
        coords_pca: Array of shape (n_samples, 3) with PCA coordinates
        coords_umap: Array of shape (n_samples, 2) with UMAP coordinates
        labels: Optional array of cluster labels for coloring
    """
    # Create 3D scatter using first 3 PCA components and UMAP as Z-axis
    if labels is not None:
        cluster_names = [f"Cluster {int(c)}" for c in labels]
    else:
        cluster_names = ["All cells"] * len(coords_pca)

    fig = go.Figure(
        data=[
            go.Scatter3d(
                x=coords_pca[:, 0],
                y=coords_pca[:, 1],
                z=coords_pca[:, 2] if coords_pca.shape[1] >= 3 else coords_umap[:, 0],
                mode="markers",
                marker=dict(
                    size=4,
                    color=labels if labels is not None else np.arange(len(coords_pca)),
                    colorscale="Viridis",
                    opacity=0.8,
                    showscale=True,
                    colorbar=dict(title="Cluster"),
                ),
                text=cluster_names,
                hovertemplate="<b>%{text}</b><br>PC1: %{x:.3f}<br>PC2: %{y:.3f}<br>PC3: %{z:.3f}<extra></extra>",
            )
        ]
    )

    fig.update_layout(
        title="3D PCA Embedding - Interactive",
        scene=dict(
            xaxis_title="PC1",
            yaxis_title="PC2",
            zaxis_title="PC3",
            camera=dict(
                eye=dict(x=1.5, y=1.5, z=1.3),
            ),
        ),
        height=600,
        hovermode="closest",
    )

    st.plotly_chart(fig, use_column_width=True)


def plot_variance_explained(variance_cumsum: np.ndarray) -> None:
    """Plot cumulative variance explained by PCA components.

    Args:
        variance_cumsum: Cumulative variance explained array
    """
    fig = go.Figure()

    fig.add_trace(
        go.Scatter(
            x=np.arange(1, len(variance_cumsum) + 1),
            y=variance_cumsum * 100,
            mode="lines+markers",
            name="Cumulative Variance",
            line=dict(color="rgb(31, 119, 180)", width=3),
            marker=dict(size=6),
            fill="tozeroy",
            fillcolor="rgba(31, 119, 180, 0.2)",
        )
    )

    # Find and mark where 80% and 95% variance is reached
    idx_80 = np.where(variance_cumsum >= 0.8)[0]
    idx_95 = np.where(variance_cumsum >= 0.95)[0]

    if len(idx_80) > 0:
        fig.add_vline(
            x=idx_80[0] + 1,
            line_dash="dash",
            line_color="orange",
            annotation_text=f"80% var. at PC{idx_80[0] + 1}",
        )

    if len(idx_95) > 0:
        fig.add_vline(
            x=idx_95[0] + 1,
            line_dash="dash",
            line_color="red",
            annotation_text=f"95% var. at PC{idx_95[0] + 1}",
        )

    fig.update_layout(
        title="Cumulative Variance Explained (PCA)",
        xaxis_title="Number of Components",
        yaxis_title="Variance Explained (%)",
        height=400,
        hovermode="x unified",
    )

    st.plotly_chart(fig, use_column_width=True)


def plot_cluster_heatmap(
    data: np.ndarray, labels: np.ndarray, top_genes: int = 20
) -> None:
    """Plot heatmap of top genes per cluster.

    Args:
        data: Gene expression matrix (cells × genes)
        labels: Cluster labels
        top_genes: Number of top genes to display
    """
    import pandas as pd

    # Calculate mean expression per cluster
    unique_clusters = np.unique(labels)
    cluster_means = []

    for cluster in sorted(unique_clusters):
        mask = labels == cluster
        mean_expr = data[mask].mean(axis=0)
        cluster_means.append(mean_expr)

    cluster_means = np.array(cluster_means)

    # Get top genes (most variable across clusters)
    gene_variance = cluster_means.var(axis=0)
    top_gene_idx = np.argsort(gene_variance)[-top_genes:][::-1]

    # Create heatmap
    heatmap_data = cluster_means[:, top_gene_idx]

    fig = go.Figure(
        data=go.Heatmap(
            z=heatmap_data,
            x=[f"Gene {i}" for i in range(top_genes)],
            y=[f"Cluster {int(c)}" for c in sorted(unique_clusters)],
            colorscale="RdYlBu_r",
        )
    )

    fig.update_layout(
        title=f"Top {top_genes} Variable Genes by Cluster",
        height=400,
        xaxis_title="Genes",
        yaxis_title="Clusters",
    )

    st.plotly_chart(fig, use_column_width=True)

