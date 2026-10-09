"""Normalization & highly-variable gene selection."""
from __future__ import annotations

import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from streamlit_modules import state


def _hvg_table(counts, top_n: int):
    """Identify highly-variable genes via dispersion (var/mean)."""
    mean = counts.mean(axis=0).values
    var = counts.var(axis=0).values
    dispersion = np.where(mean > 0, var / (mean + 1e-9), 0)
    idx = np.argsort(dispersion)[::-1][:top_n]
    import pandas as pd
    return pd.DataFrame({
        "gene": counts.columns[idx],
        "mean": mean[idx].round(3),
        "variance": var[idx].round(3),
        "dispersion": dispersion[idx].round(3),
    })


def render() -> None:
    st.subheader("⚖️ Normalization & Scaling")
    qc = state.get("qc")
    if qc is None:
        st.warning("Run **Quality Control** first to obtain a filtered matrix.")
        return

    counts = qc["_counts"]
    normalized = qc["_normalized"]

    st.markdown(
        "QC already produces a `log1p`-then-`z-score`-scaled matrix. "
        "This module visualizes the effect and lets you preview "
        "highly-variable gene selection."
    )

    # Before / after comparison on a sample of cells
    sample_n = min(500, counts.shape[0])
    rng = np.random.default_rng(0)
    cell_idx = rng.choice(counts.shape[0], sample_n, replace=False)
    raw_vals = counts.iloc[cell_idx].values.flatten()
    norm_vals = normalized.iloc[cell_idx].values.flatten()
    # Subsample again to keep plotly responsive
    raw_vals = raw_vals[:30_000]
    norm_vals = norm_vals[:30_000]

    c1, c2 = st.columns(2)
    with c1:
        st.markdown("**Raw counts distribution**")
        fig = px.histogram(x=raw_vals[raw_vals > 0], nbins=60, log_y=True,
                           color_discrete_sequence=["#ec4899"])
        fig.update_layout(height=320, margin=dict(l=20, r=20, t=10, b=30),
                          paper_bgcolor="rgba(0,0,0,0)",
                          plot_bgcolor="rgba(0,0,0,0)", showlegend=False)
        st.plotly_chart(fig, use_container_width=True)
    with c2:
        st.markdown("**After log1p + z-score**")
        fig = px.histogram(x=norm_vals, nbins=60,
                           color_discrete_sequence=["#10b981"])
        fig.update_layout(height=320, margin=dict(l=20, r=20, t=10, b=30),
                          paper_bgcolor="rgba(0,0,0,0)",
                          plot_bgcolor="rgba(0,0,0,0)", showlegend=False)
        st.plotly_chart(fig, use_container_width=True)

    st.divider()
    st.markdown("### Highly variable genes")
    top_n = st.slider("Top N highly variable genes", 10, 500, 50)
    hvg = _hvg_table(counts, top_n)
    st.dataframe(hvg, use_container_width=True, hide_index=True)

    # Mean vs dispersion scatter
    mean_all = counts.mean(axis=0).values
    var_all = counts.var(axis=0).values
    disp_all = np.where(mean_all > 0, var_all / (mean_all + 1e-9), 0)
    is_hvg = np.zeros_like(mean_all, dtype=bool)
    is_hvg[np.argsort(disp_all)[::-1][:top_n]] = True

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=mean_all[~is_hvg], y=disp_all[~is_hvg],
                             mode="markers", name="Other",
                             marker=dict(size=4, color="#475569", opacity=0.55)))
    fig.add_trace(go.Scatter(x=mean_all[is_hvg], y=disp_all[is_hvg],
                             mode="markers", name=f"Top {top_n} HVG",
                             marker=dict(size=6, color="#06b6d4")))
    fig.update_layout(title="Mean expression vs. dispersion",
                      xaxis_title="Mean", yaxis_title="Dispersion (var / mean)",
                      xaxis_type="log", yaxis_type="log", height=380,
                      margin=dict(l=20, r=20, t=40, b=40),
                      paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
    st.plotly_chart(fig, use_container_width=True)
