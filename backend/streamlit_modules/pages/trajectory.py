"""Trajectory / pseudotime module — k-NN-graph geodesic ordering."""
from __future__ import annotations

import numpy as np
import plotly.express as px
import streamlit as st

from app.services.trajectory import infer_pseudotime
from streamlit_modules import state


def render() -> None:
    st.subheader("🌐 Trajectory & Pseudotime")
    pca = state.get("pca")
    if pca is None:
        st.warning("Run **Dimensionality Reduction** first.")
        return

    components = np.asarray(pca["_components"])
    params = state.get("params")

    c1, c2, c3 = st.columns(3)
    with c1:
        k = st.slider("k-NN neighbors", 5, 50,
                      value=params["trajectory_k"])
    with c2:
        root_choice = st.text_input("Root cell index (blank = auto)", value="")
    with c3:
        st.write(" ")
        run = st.button("▶️ Infer pseudotime", use_container_width=True)

    if run:
        root_idx = None
        if root_choice.strip():
            try:
                root_idx = int(root_choice.strip())
            except ValueError:
                st.warning("Root cell index must be an integer; using auto.")
        with st.spinner("Building k-NN graph and computing geodesics…"):
            try:
                res = infer_pseudotime(components, k=int(k), root_index=root_idx)
                state.set_("trajectory", {**res.to_dict(),
                                          "_pseudotime": res.pseudotime})
                params["trajectory_k"] = int(k)
            except Exception as exc:
                st.error(f"Trajectory inference failed: {exc}")
                return

    traj = state.get("trajectory")
    if traj is None:
        st.info("Click **Infer pseudotime** to order the cells.")
        return

    cols = st.columns(3)
    cols[0].metric("Root cell idx", traj["root_index"])
    cols[1].metric("k-NN graph density", f"{traj['knn_graph_density']:.4f}")
    cols[2].metric("Approx. branches", traj["branch_count"])

    pseudo = np.asarray(traj["_pseudotime"])

    # Pseudotime histogram
    fig = px.histogram(x=pseudo, nbins=50,
                       color_discrete_sequence=["#6366f1"],
                       labels={"x": "Pseudotime"},
                       title="Pseudotime distribution")
    fig.update_layout(height=300, margin=dict(l=20, r=20, t=40, b=30),
                      paper_bgcolor="rgba(0,0,0,0)",
                      plot_bgcolor="rgba(0,0,0,0)", showlegend=False)
    st.plotly_chart(fig, use_container_width=True)

    # Pseudotime on UMAP
    umap = state.get("umap")
    if umap is not None:
        coords = np.asarray(umap["_coords"])
        fig = px.scatter(x=coords[:, 0], y=coords[:, 1], color=pseudo,
                         color_continuous_scale="Magma",
                         labels={"x": "UMAP 1", "y": "UMAP 2",
                                 "color": "Pseudotime"},
                         title="Pseudotime on UMAP")
        fig.update_traces(marker=dict(size=5, opacity=0.85))
        # Highlight root
        root_x, root_y = coords[traj["root_index"]]
        fig.add_scatter(x=[root_x], y=[root_y],
                        mode="markers+text",
                        marker=dict(size=18, color="#10b981",
                                    line=dict(color="white", width=2),
                                    symbol="star"),
                        text=["Root"], textposition="top center",
                        showlegend=False)
        fig.update_layout(height=460, margin=dict(l=20, r=20, t=40, b=20),
                          paper_bgcolor="rgba(0,0,0,0)",
                          plot_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig, use_container_width=True)

    # Pseudotime vs cluster (boxplot)
    clusters = state.get("clusters")
    if clusters is not None:
        labels = np.asarray(clusters["_labels"])
        fig = px.box(x=labels.astype(str), y=pseudo, color=labels.astype(str),
                     color_discrete_sequence=px.colors.qualitative.Bold,
                     labels={"x": "Cluster", "y": "Pseudotime"},
                     title="Pseudotime ranges per cluster")
        fig.update_layout(height=380, showlegend=False,
                          margin=dict(l=20, r=20, t=40, b=40),
                          paper_bgcolor="rgba(0,0,0,0)",
                          plot_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig, use_container_width=True)
