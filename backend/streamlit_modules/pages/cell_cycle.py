"""Cell cycle module — simple S / G2M phase scoring."""
from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st

from app.services.advanced_analysis import compute_cell_cycle_phase
from streamlit_modules import state


PHASE_COLORS = {"G1": "#06b6d4", "S": "#10b981", "G2/M": "#ec4899"}


def render() -> None:
    st.subheader("🔄 Cell Cycle Scoring")
    qc = state.get("qc")
    if qc is None:
        st.warning("Run **QC** first.")
        return

    st.markdown(
        "Cells are classified into **G1**, **S**, or **G2/M** based on mean "
        "expression of canonical S-phase (MCM, PCNA, TYMS…) and G2/M genes "
        "(MKI67, TOP2A, CENPF…). When those genes aren't present the cells "
        "default to G1 — the demo dataset is synthetic, so expect mostly G1."
    )

    if st.button("▶️ Score cell cycle", use_container_width=True):
        with st.spinner("Scoring…"):
            phases = compute_cell_cycle_phase(qc["_counts"])
            state.set_("cycle_phases", phases)

    phases = state.get("cycle_phases")
    if phases is None:
        st.info("Click **Score cell cycle** to compute phases.")
        return

    counts = pd.Series(phases).value_counts().reindex(["G1", "S", "G2/M"]).fillna(0)
    cols = st.columns(3)
    for i, ph in enumerate(["G1", "S", "G2/M"]):
        cols[i].metric(ph, int(counts[ph]))

    c1, c2 = st.columns(2)
    with c1:
        fig = px.pie(values=counts.values, names=counts.index, hole=0.45,
                     color=counts.index, color_discrete_map=PHASE_COLORS,
                     title="Phase distribution")
        fig.update_layout(height=360, margin=dict(l=20, r=20, t=40, b=20),
                          paper_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig, use_container_width=True)
    with c2:
        fig = px.bar(x=counts.index, y=counts.values,
                     color=counts.index, color_discrete_map=PHASE_COLORS,
                     labels={"x": "Phase", "y": "# cells"},
                     title="Phase counts")
        fig.update_layout(height=360, showlegend=False,
                          margin=dict(l=20, r=20, t=40, b=20),
                          paper_bgcolor="rgba(0,0,0,0)",
                          plot_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig, use_container_width=True)

    # Per-cluster breakdown
    clusters = state.get("clusters")
    if clusters is not None:
        labels = np.asarray(clusters["_labels"])
        df = pd.DataFrame({"cluster": labels, "phase": phases})
        ct = pd.crosstab(df["cluster"], df["phase"]).reindex(
            columns=["G1", "S", "G2/M"], fill_value=0)
        fig = px.bar(ct, barmode="stack", color_discrete_map=PHASE_COLORS,
                     labels={"value": "# cells", "cluster": "Cluster"},
                     title="Cell cycle composition per cluster")
        fig.update_layout(height=360, margin=dict(l=20, r=20, t=40, b=40),
                          paper_bgcolor="rgba(0,0,0,0)",
                          plot_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig, use_container_width=True)

    umap = state.get("umap")
    if umap is not None:
        coords = np.asarray(umap["_coords"])
        fig = px.scatter(x=coords[:, 0], y=coords[:, 1], color=phases,
                         color_discrete_map=PHASE_COLORS,
                         labels={"x": "UMAP 1", "y": "UMAP 2",
                                 "color": "Phase"},
                         title="Cell cycle phases on UMAP")
        fig.update_traces(marker=dict(size=5, opacity=0.85))
        fig.update_layout(height=460, margin=dict(l=20, r=20, t=40, b=20),
                          paper_bgcolor="rgba(0,0,0,0)",
                          plot_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig, use_container_width=True)
