"""Pairwise differential expression — volcano plot, MA plot, ranked table."""
from __future__ import annotations

import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from app.services.differential_expression import pairwise_de, summarize_de
from streamlit_modules import state


def render() -> None:
    st.subheader("🧪 Differential Expression")
    qc = state.get("qc")
    clusters = state.get("clusters")
    if qc is None or clusters is None:
        st.warning("Run **QC** and **Clustering** first.")
        return

    labels = np.asarray(clusters["_labels"])
    cluster_ids = sorted(int(c) for c in np.unique(labels))
    if len(cluster_ids) < 2:
        st.warning("Need at least 2 clusters for pairwise DE.")
        return

    c1, c2, c3, c4 = st.columns([1, 1, 1, 1])
    with c1:
        a = st.selectbox("Cluster A", cluster_ids, index=0)
    with c2:
        b = st.selectbox("Cluster B", cluster_ids,
                         index=1 if len(cluster_ids) > 1 else 0)
    with c3:
        fc_thresh = st.slider("|log2 FC| ≥", 0.1, 5.0, 1.0, step=0.1)
    with c4:
        alpha = st.slider("FDR α", 0.001, 0.2, 0.05, step=0.005)

    if st.button("▶️ Run DE A vs B", use_container_width=True):
        if a == b:
            st.error("Pick two different clusters.")
        else:
            with st.spinner("Running Welch's t-tests…"):
                try:
                    df = pairwise_de(qc["_counts"], labels,
                                     int(a), int(b),
                                     log_fc_threshold=float(fc_thresh),
                                     alpha=float(alpha))
                    state.set_("de_table", df)
                    state.set_("de_pair", (int(a), int(b)))
                except Exception as exc:
                    st.error(f"DE failed: {exc}")
                    return

    df = state.get("de_table")
    pair = state.get("de_pair")
    if df is None or df.empty:
        st.info("Pick two clusters and click **Run DE** to populate plots.")
        return

    a, b = pair
    summary = summarize_de(df)
    cols = st.columns(4)
    cols[0].metric("Genes tested", summary["total"])
    cols[1].metric("Significant", summary["significant"])
    cols[2].metric(f"Up in C{a}", summary["up"])
    cols[3].metric(f"Up in C{b}", summary["down"])

    # Volcano
    df_plot = df.copy()
    df_plot["category"] = np.where(
        df_plot["significant"],
        np.where(df_plot["log2_fc"] > 0, f"Up in C{a}", f"Up in C{b}"),
        "Not significant",
    )
    color_map = {f"Up in C{a}": "#ec4899",
                 f"Up in C{b}": "#06b6d4",
                 "Not significant": "#475569"}
    fig = px.scatter(df_plot, x="log2_fc", y="neg_log10_p", color="category",
                     hover_data=["gene", "p_adj"],
                     color_discrete_map=color_map,
                     title=f"Volcano plot — Cluster {a} vs Cluster {b}")
    fig.update_traces(marker=dict(size=6, opacity=0.85))
    fig.add_vline(x=fc_thresh, line_dash="dot", line_color="rgba(255,255,255,0.4)")
    fig.add_vline(x=-fc_thresh, line_dash="dot", line_color="rgba(255,255,255,0.4)")
    fig.add_hline(y=-np.log10(alpha), line_dash="dot",
                  line_color="rgba(255,255,255,0.4)")
    fig.update_layout(height=480, margin=dict(l=40, r=20, t=40, b=40),
                      paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
    st.plotly_chart(fig, use_container_width=True)

    # MA plot
    df_plot["mean_expr"] = (df_plot["mean_a"] + df_plot["mean_b"]) / 2
    fig2 = px.scatter(df_plot, x="mean_expr", y="log2_fc",
                      color="category", color_discrete_map=color_map,
                      hover_data=["gene", "p_adj"],
                      title="MA plot",
                      log_x=True)
    fig2.update_traces(marker=dict(size=5, opacity=0.8))
    fig2.update_layout(height=380, margin=dict(l=40, r=20, t=40, b=40),
                       paper_bgcolor="rgba(0,0,0,0)",
                       plot_bgcolor="rgba(0,0,0,0)")
    st.plotly_chart(fig2, use_container_width=True)

    # Top-20 tables
    st.markdown("### Ranked tables")
    t1, t2 = st.columns(2)
    with t1:
        st.markdown(f"**Top up in Cluster {a}**")
        st.dataframe(df[df["significant"] & (df["log2_fc"] > 0)]
                     .head(20)[["gene", "log2_fc", "p_value", "p_adj"]],
                     use_container_width=True, hide_index=True)
    with t2:
        st.markdown(f"**Top up in Cluster {b}**")
        st.dataframe(df[df["significant"] & (df["log2_fc"] < 0)]
                     .sort_values("log2_fc")
                     .head(20)[["gene", "log2_fc", "p_value", "p_adj"]],
                     use_container_width=True, hide_index=True)
