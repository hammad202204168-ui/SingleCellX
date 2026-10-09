"""Clustering module — k-means, Leiden and Louvain on a k-NN graph."""
from __future__ import annotations

import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score

from app.services.clustering import cluster_cells
from app.services.graph_clustering import cluster_graph
from streamlit_modules import state


def _elbow_curve(pca_components: np.ndarray, k_max: int = 10):
    pts = []
    k_max = max(2, min(k_max, pca_components.shape[0] - 1))
    for k in range(2, k_max + 1):
        km = KMeans(n_clusters=k, random_state=42, n_init=10)
        km.fit(pca_components)
        sil = None
        try:
            sil = silhouette_score(pca_components, km.labels_,
                                   sample_size=min(1000, len(km.labels_)))
        except Exception:
            pass
        pts.append((k, km.inertia_, sil))
    ks, inertias, sils = zip(*pts)
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=ks, y=inertias, mode="lines+markers",
                             name="Inertia",
                             line=dict(color="#6366f1", width=3),
                             marker=dict(size=8)))
    fig.add_trace(go.Scatter(x=ks, y=[s if s is not None else None for s in sils],
                             mode="lines+markers", name="Silhouette",
                             yaxis="y2",
                             line=dict(color="#ec4899", width=3, dash="dot"),
                             marker=dict(size=8)))
    fig.update_layout(
        title="Elbow & silhouette diagnostic (k-means sweep)",
        xaxis_title="k (number of clusters)",
        yaxis=dict(title="Inertia"),
        yaxis2=dict(title="Silhouette", overlaying="y", side="right"),
        height=380, margin=dict(l=40, r=40, t=40, b=40),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        legend=dict(orientation="h", y=1.1),
    )
    return fig


def render() -> None:
    st.subheader("🎯 Clustering")
    pca = state.get("pca")
    if pca is None:
        st.warning("Run **Dimensionality Reduction** first.")
        return

    components = np.asarray(pca["_components"])
    params = state.get("params")

    method = st.radio(
        "Method",
        ["Leiden (graph)", "Louvain (graph)", "K-Means"],
        horizontal=True,
        index=0,
        help=("Leiden is the scRNA-seq community standard — it works on a "
              "k-NN graph in PCA space. K-Means is kept for comparability."),
    )

    if method == "K-Means":
        c1, c2, c3 = st.columns(3)
        with c1:
            auto = st.checkbox("Auto-pick k (elbow)",
                               value=params["n_clusters"] is None)
        with c2:
            k = st.number_input("k", 2, 30,
                                value=params["n_clusters"] or 6, disabled=auto)
        with c3:
            st.write(" ")
            run = st.button("▶️ Run clustering", use_container_width=True)
        with st.expander("Elbow / silhouette diagnostic", expanded=False):
            with st.spinner("Sweeping k = 2..10…"):
                st.plotly_chart(_elbow_curve(components, k_max=10),
                                use_container_width=True)
        if run:
            with st.spinner("Running k-means…"):
                n = None if auto else int(k)
                res = cluster_cells(components, n_clusters=n)
                state.set_("clusters", {**res.to_dict(), "_labels": res.labels})
                params["n_clusters"] = None if auto else int(k)
    else:
        c1, c2, c3 = st.columns(3)
        with c1:
            k_nn = st.slider("k-NN neighbors", 5, 50,
                             value=params.get("cluster_k_nn", 15))
        with c2:
            resolution = st.slider("Resolution",
                                   0.1, 3.0,
                                   value=float(params.get("cluster_resolution", 1.0)),
                                   step=0.1,
                                   help="Higher = more, smaller clusters.")
        with c3:
            st.write(" ")
            run = st.button("▶️ Run clustering", use_container_width=True)

        if run:
            algo = "leiden" if method.startswith("Leiden") else "louvain"
            with st.spinner(f"Running {algo}…"):
                try:
                    res = cluster_graph(components, method=algo,
                                        k=int(k_nn),
                                        resolution=float(resolution))
                    state.set_("clusters", {
                        **res.to_dict(),
                        "_labels": res.labels,
                        # k-means-compatible keys for downstream pages
                        "inertia": 0.0,
                        "silhouette": None,
                    })
                    params["cluster_k_nn"] = int(k_nn)
                    params["cluster_resolution"] = float(resolution)
                except Exception as exc:
                    st.error(f"Graph clustering failed: {exc}")
                    return

    clusters = state.get("clusters")
    if clusters is None:
        st.info("Click **Run clustering** to assign cells to clusters.")
        return

    cols = st.columns(4)
    cols[0].metric("Method", clusters.get("method", "kmeans"))
    cols[1].metric("Clusters found", clusters["n_clusters"])
    if clusters.get("modularity"):
        cols[2].metric("Modularity", f"{clusters['modularity']:.3f}")
    elif clusters.get("silhouette") is not None:
        cols[2].metric("Silhouette", f"{clusters['silhouette']:.3f}")
    else:
        cols[2].metric("Quality", "n/a")
    cols[3].metric("Largest cluster",
                   max(clusters["distribution"].values()))

    # Cluster size bar
    dist = clusters["distribution"]
    fig = px.bar(x=list(dist.keys()), y=list(dist.values()),
                 labels={"x": "Cluster", "y": "# cells"},
                 color=list(dist.keys()),
                 color_discrete_sequence=px.colors.qualitative.Bold,
                 title="Cluster size distribution")
    fig.update_layout(height=320, showlegend=False,
                      margin=dict(l=20, r=20, t=40, b=40),
                      paper_bgcolor="rgba(0,0,0,0)",
                      plot_bgcolor="rgba(0,0,0,0)")
    st.plotly_chart(fig, use_container_width=True)

    # On UMAP
    umap = state.get("umap")
    if umap is not None:
        coords = np.asarray(umap["_coords"])
        labels = np.asarray(clusters["_labels"])
        fig2 = px.scatter(x=coords[:, 0], y=coords[:, 1],
                          color=labels.astype(str),
                          labels={"x": "UMAP 1", "y": "UMAP 2",
                                  "color": "Cluster"},
                          color_discrete_sequence=px.colors.qualitative.Bold,
                          title="Clusters on UMAP")
        fig2.update_traces(marker=dict(size=5, opacity=0.85))
        fig2.update_layout(height=460, margin=dict(l=20, r=20, t=40, b=20),
                           paper_bgcolor="rgba(0,0,0,0)",
                           plot_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig2, use_container_width=True)
