"""Cell type annotation module — marker-panel scoring per cluster."""
from __future__ import annotations

import numpy as np
import plotly.express as px
import streamlit as st

from app.services.cell_type_annotation import (
    CANONICAL_PANELS, annotate_clusters
)
from streamlit_modules import state


def render() -> None:
    st.subheader("🩺 Cell-type Annotation")
    qc = state.get("qc")
    clusters = state.get("clusters")
    if qc is None or clusters is None:
        st.warning("Run **QC** and **Clustering** first.")
        return

    st.markdown(
        "Each cluster is scored against marker-gene panels. The highest-"
        "scoring type is assigned, with a confidence based on the margin "
        "over the runner-up."
    )

    with st.expander("Marker panels in use"):
        st.json(CANONICAL_PANELS)

    if st.button("▶️ Annotate clusters", use_container_width=True):
        with st.spinner("Scoring panels…"):
            try:
                ann = annotate_clusters(qc["_counts"],
                                        np.asarray(clusters["_labels"]))
                state.set_("annotation", ann)
            except Exception as exc:
                st.error(f"Annotation failed: {exc}")
                return

    ann = state.get("annotation")
    if ann is None:
        st.info("Click **Annotate clusters** to label them.")
        return

    st.dataframe(ann, use_container_width=True, hide_index=True)

    # Bar of cells per type
    cells_per_type = ann.groupby("cell_type")["n_cells"].sum().reset_index()
    fig = px.bar(cells_per_type, x="cell_type", y="n_cells",
                 color="cell_type",
                 color_discrete_sequence=px.colors.qualitative.Bold,
                 title="Cells per inferred type")
    fig.update_layout(height=340, showlegend=False,
                      margin=dict(l=20, r=20, t=40, b=60),
                      paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
    st.plotly_chart(fig, use_container_width=True)

    # Overlay on UMAP
    umap = state.get("umap")
    if umap is not None:
        coords = np.asarray(umap["_coords"])
        labels = np.asarray(clusters["_labels"])
        # cluster → type
        cluster_to_type = dict(zip(ann["cluster"], ann["cell_type"]))
        cell_type = np.array([cluster_to_type.get(int(l), "Unknown") for l in labels])
        fig2 = px.scatter(x=coords[:, 0], y=coords[:, 1], color=cell_type,
                          labels={"x": "UMAP 1", "y": "UMAP 2", "color": "Type"},
                          color_discrete_sequence=px.colors.qualitative.Bold,
                          title="Inferred cell types on UMAP")
        fig2.update_traces(marker=dict(size=5, opacity=0.85))
        fig2.update_layout(height=460, margin=dict(l=20, r=20, t=40, b=20),
                           paper_bgcolor="rgba(0,0,0,0)",
                           plot_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig2, use_container_width=True)

    # Confidence chart
    fig3 = px.bar(ann.sort_values("confidence"), x="confidence", y="cell_type",
                  orientation="h", color="confidence",
                  color_continuous_scale="Viridis",
                  title="Annotation confidence (margin over runner-up)")
    fig3.update_layout(height=320, margin=dict(l=20, r=20, t=40, b=20),
                       paper_bgcolor="rgba(0,0,0,0)",
                       plot_bgcolor="rgba(0,0,0,0)")
    st.plotly_chart(fig3, use_container_width=True)
