"""Dimensionality reduction — PCA, UMAP, t-SNE with interactive plots."""
from __future__ import annotations

import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from app.services.dimensionality import run_pca, run_umap, run_tsne
from streamlit_modules import state


def _scree_plot(var_ratio, cum_var):
    fig = go.Figure()
    fig.add_trace(go.Bar(x=list(range(1, len(var_ratio) + 1)), y=var_ratio * 100,
                         name="Per-PC", marker_color="#6366f1", opacity=0.55))
    fig.add_trace(go.Scatter(x=list(range(1, len(cum_var) + 1)),
                             y=cum_var * 100, mode="lines+markers",
                             name="Cumulative",
                             line=dict(color="#ec4899", width=3),
                             yaxis="y2"))
    fig.update_layout(
        title="PCA scree plot",
        xaxis_title="Component",
        yaxis=dict(title="Variance (%)"),
        yaxis2=dict(title="Cumulative (%)", overlaying="y", side="right",
                    range=[0, 100]),
        height=380,
        margin=dict(l=40, r=40, t=40, b=40),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        legend=dict(orientation="h", y=1.1),
    )
    return fig


def _embed_scatter(coords, labels, title):
    color = labels.astype(str) if labels is not None else None
    fig = px.scatter(x=coords[:, 0], y=coords[:, 1], color=color,
                     labels={"x": "Dim 1", "y": "Dim 2", "color": "Cluster"},
                     title=title,
                     color_discrete_sequence=px.colors.qualitative.Bold)
    fig.update_traces(marker=dict(size=5, opacity=0.85,
                                  line=dict(width=0.2, color="white")))
    fig.update_layout(height=420, margin=dict(l=20, r=20, t=40, b=20),
                      paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                      transition=dict(duration=500, easing="cubic-in-out"))
    return fig


def render() -> None:
    st.subheader("📉 Dimensionality Reduction")
    qc = state.get("qc")
    if qc is None:
        st.warning("Run **Quality Control** first.")
        return

    params = state.get("params")
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        n_pca = st.slider("PCA components", 2, 200,
                          value=params["n_pca_components"])
    with c2:
        umap_n = st.slider("UMAP neighbors", 2, 100,
                           value=params["umap_n_neighbors"])
    with c3:
        umap_d = st.slider("UMAP min dist", 0.001, 1.0,
                           value=params["umap_min_dist"])
    with c4:
        st.write(" ")
        run = st.button("▶️ Run PCA / UMAP / t-SNE", use_container_width=True)

    if run:
        normalized = qc["_normalized"]
        with st.spinner("PCA…"):
            pca = run_pca(normalized, n_components=int(n_pca))
            state.set_("pca", {**pca.to_dict(), "_components": pca.components})
            params["n_pca_components"] = int(n_pca)
        with st.spinner("UMAP…"):
            try:
                u = run_umap(pca.components, n_neighbors=int(umap_n),
                             min_dist=float(umap_d))
                state.set_("umap", {**u.to_dict(), "_coords": u.coords})
                params["umap_n_neighbors"] = int(umap_n)
                params["umap_min_dist"] = float(umap_d)
            except Exception as exc:
                st.warning(f"UMAP failed: {exc}")
        with st.spinner("t-SNE…"):
            try:
                t = run_tsne(pca.components)
                state.set_("tsne", {**t.to_dict(), "_coords": t.coords})
            except Exception as exc:
                st.warning(f"t-SNE failed: {exc}")
        st.success("✅ Embeddings ready.")

    pca = state.get("pca")
    if pca is None:
        st.info("Click **Run** to compute embeddings.")
        return

    # Scree
    st.plotly_chart(_scree_plot(np.asarray(pca["variance_ratio"]),
                                np.asarray(pca["cumulative_variance"])),
                    use_container_width=True)

    # 2D scatters
    clusters = state.get("clusters")
    labels = np.asarray(clusters["labels"]) if clusters else None

    c1, c2 = st.columns(2)
    pca_coords = np.asarray(pca["_components"])[:, :2]
    c1.plotly_chart(_embed_scatter(pca_coords, labels, "PCA (PC1 vs PC2)"),
                    use_container_width=True)
    umap = state.get("umap")
    if umap is not None:
        c2.plotly_chart(_embed_scatter(np.asarray(umap["_coords"]),
                                       labels, "UMAP"),
                        use_container_width=True)
    tsne = state.get("tsne")
    if tsne is not None:
        st.plotly_chart(_embed_scatter(np.asarray(tsne["_coords"]),
                                       labels, "t-SNE"),
                        use_container_width=True)

    # 3D PCA
    if np.asarray(pca["_components"]).shape[1] >= 3:
        st.markdown("### 3D PCA (interactive)")
        coords3 = np.asarray(pca["_components"])[:, :3]
        color = labels.astype(str) if labels is not None else None
        fig = px.scatter_3d(x=coords3[:, 0], y=coords3[:, 1], z=coords3[:, 2],
                            color=color,
                            labels={"x": "PC1", "y": "PC2", "z": "PC3",
                                    "color": "Cluster"},
                            color_discrete_sequence=px.colors.qualitative.Bold)
        fig.update_traces(marker=dict(size=3, opacity=0.85))
        fig.update_layout(height=520, margin=dict(l=0, r=0, t=10, b=0),
                          paper_bgcolor="rgba(0,0,0,0)",
                          scene=dict(bgcolor="rgba(0,0,0,0)"))
        st.plotly_chart(fig, use_container_width=True)
