"""Marker genes module — one-vs-rest DE per cluster + visualizations."""
from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from app.services.markers import find_markers
from streamlit_modules import state


def render() -> None:
    st.subheader("🧬 Marker Gene Discovery")
    qc = state.get("qc")
    clusters = state.get("clusters")
    if qc is None or clusters is None:
        st.warning("Run **QC** and **Clustering** first.")
        return

    params = state.get("params")
    c1, c2, c3 = st.columns(3)
    with c1:
        top_n = st.slider("Top markers / cluster", 5, 50,
                          value=params["n_marker_genes"])
    with c2:
        log_fc = st.slider("|log2 FC| threshold", 0.1, 5.0, 0.5, step=0.1)
    with c3:
        st.write(" ")
        run = st.button("▶️ Find markers", use_container_width=True)

    if run:
        with st.spinner("Computing one-vs-rest tests…"):
            markers = find_markers(qc["_counts"],
                                   np.asarray(clusters["_labels"]),
                                   top_n=int(top_n),
                                   log_fc_threshold=float(log_fc))
            state.set_("markers", markers)
            params["n_marker_genes"] = int(top_n)

    markers = state.get("markers")
    if not markers:
        st.info("Click **Find markers** to populate the table.")
        return

    # Summary metric
    total = sum(len(v) for v in markers.values())
    c1, c2, c3 = st.columns(3)
    c1.metric("Total markers", total)
    c2.metric("Clusters with markers",
              sum(1 for v in markers.values() if v))
    c3.metric("Avg per cluster",
              f"{total / max(1, len(markers)):.1f}")

    # Heatmap of top markers
    st.markdown("### Top markers heatmap")
    counts = qc["_counts"]
    labels = np.asarray(clusters["_labels"])
    top_per = []
    for cname, ms in markers.items():
        for m in ms[:5]:
            top_per.append((cname, m["gene"]))
    if top_per:
        unique_genes = list(dict.fromkeys(g for _, g in top_per))
        unique_genes = [g for g in unique_genes if g in counts.columns][:40]
        cluster_means = []
        cluster_ids = sorted(np.unique(labels))
        for cid in cluster_ids:
            cluster_means.append(counts.loc[labels == cid, unique_genes]
                                       .mean(axis=0).values)
        z = np.asarray(cluster_means)
        # row-normalize for visual contrast
        z_n = (z - z.mean(axis=0)) / (z.std(axis=0) + 1e-9)
        fig = go.Figure(go.Heatmap(z=z_n, x=unique_genes,
                                   y=[f"C{c}" for c in cluster_ids],
                                   colorscale="RdBu_r", zmid=0,
                                   colorbar=dict(title="z-score")))
        fig.update_layout(height=380, margin=dict(l=40, r=20, t=20, b=80),
                          paper_bgcolor="rgba(0,0,0,0)",
                          plot_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig, use_container_width=True)

    # Detail tables
    st.markdown("### Cluster details")
    for cname, ms in markers.items():
        if not ms:
            continue
        with st.expander(f"{cname}  ·  {len(ms)} markers"):
            df = pd.DataFrame(ms)
            st.dataframe(df, use_container_width=True, hide_index=True)
            if "log_fc" in df.columns:
                fig = px.bar(df.head(15), x="gene", y="log_fc",
                             color="log_fc", color_continuous_scale="Plasma",
                             title=f"{cname} — top markers by log2 FC")
                fig.update_layout(height=320, showlegend=False,
                                  margin=dict(l=20, r=20, t=40, b=80),
                                  paper_bgcolor="rgba(0,0,0,0)",
                                  plot_bgcolor="rgba(0,0,0,0)")
                st.plotly_chart(fig, use_container_width=True)
