"""Data ingestion module — demo generator + CSV upload + preview."""
from __future__ import annotations

import io

import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st

from app.services.demo_data import create_demo_data
from streamlit_modules import state


def _load_csv(uploaded) -> pd.DataFrame:
    content = uploaded.getvalue()
    try:
        df = pd.read_csv(io.BytesIO(content), index_col=0)
    except Exception:
        df = pd.read_csv(io.BytesIO(content))
        first = df.columns[0]
        if str(first).lower() in ("cell", "cell_id", "id", "index"):
            df = df.set_index(first)
    if df.empty:
        raise ValueError("Uploaded file contains no rows.")
    numeric = df.select_dtypes(include=[np.number])
    if numeric.shape[1] == 0:
        raise ValueError("File must contain numeric expression values.")
    return numeric.fillna(0)


def _load_h5ad(uploaded) -> pd.DataFrame:
    """Load .h5ad upload via a temp file so AnnData can mmap it."""
    import tempfile, os
    from app.services.anndata_io import load_anndata
    with tempfile.NamedTemporaryFile(suffix=".h5ad", delete=False) as tmp:
        tmp.write(uploaded.getvalue())
        tmp_path = tmp.name
    try:
        return load_anndata(tmp_path)
    finally:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass


def render() -> None:
    st.subheader("📥 Data Ingestion")
    st.write("Choose a data source to start the pipeline.")

    tab_demo, tab_upload, tab_h5ad = st.tabs(
        ["🎲 Demo dataset", "📁 Upload CSV", "🧪 Upload .h5ad (AnnData)"]
    )

    params = state.get("params")

    with tab_demo:
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            n_cells = st.number_input("Cells", 100, 10_000,
                                      value=params["demo_n_cells"], step=100)
        with c2:
            n_genes = st.number_input("Genes", 200, 20_000,
                                      value=params["demo_n_genes"], step=100)
        with c3:
            n_clusters = st.number_input("Ground-truth clusters", 2, 12,
                                         value=params["demo_n_clusters"])
        with c4:
            seed = st.number_input("Random seed", 0, 9999, value=params["demo_seed"])

        if st.button("🎲 Generate demo dataset", use_container_width=True):
            with st.spinner("Generating synthetic expression matrix…"):
                df = create_demo_data(int(n_cells), int(n_genes),
                                      int(n_clusters), int(seed))
                state.set_("data", df)
                state.reset_pipeline(keep_data=True)
                params.update(demo_n_cells=int(n_cells), demo_n_genes=int(n_genes),
                              demo_n_clusters=int(n_clusters), demo_seed=int(seed))
            st.success(f"✅ Generated **{df.shape[0]} cells × {df.shape[1]} genes**.")

    with tab_upload:
        st.caption("CSV layout: cells in rows, genes in columns. First column = cell IDs.")
        uploaded = st.file_uploader("Drop a CSV here", type=["csv"], key="upload_csv")
        if uploaded is not None and st.button("📁 Load uploaded file",
                                              use_container_width=True):
            try:
                with st.spinner("Parsing CSV…"):
                    df = _load_csv(uploaded)
                    state.set_("data", df)
                    state.reset_pipeline(keep_data=True)
                st.success(f"✅ Loaded **{df.shape[0]} cells × {df.shape[1]} genes**.")
            except Exception as exc:
                st.error(f"Failed to load file: {exc}")

    with tab_h5ad:
        st.caption(
            "AnnData (.h5ad) is the field-standard container used by "
            "scanpy, scvi-tools and CELLxGENE. The `X` matrix is read as "
            "cells × genes; sparse matrices are densified automatically."
        )
        h5ad_up = st.file_uploader("Drop a .h5ad file here",
                                   type=["h5ad"], key="upload_h5ad")
        if h5ad_up is not None and st.button("🧪 Load .h5ad",
                                             use_container_width=True):
            try:
                with st.spinner("Reading AnnData…"):
                    df = _load_h5ad(h5ad_up)
                    state.set_("data", df)
                    state.reset_pipeline(keep_data=True)
                st.success(
                    f"✅ Loaded **{df.shape[0]} cells × {df.shape[1]} genes** "
                    f"from AnnData."
                )
            except Exception as exc:
                st.error(f"Failed to load .h5ad: {exc}")

    # Preview
    data = state.get("data")
    if data is None:
        st.info("No dataset loaded yet. Generate a demo or upload a CSV above.")
        return

    st.divider()
    st.markdown("### Dataset preview")
    c1, c2, c3, c4 = st.columns(4)
    sparsity = float((data.values == 0).sum()) / data.values.size * 100
    with c1: st.metric("Cells", f"{data.shape[0]:,}")
    with c2: st.metric("Genes", f"{data.shape[1]:,}")
    with c3: st.metric("Sparsity", f"{sparsity:.1f}%")
    with c4: st.metric("Mean UMI / cell", f"{data.sum(axis=1).mean():,.0f}")

    with st.expander("Show first 10 cells × 12 genes", expanded=False):
        st.dataframe(data.iloc[:10, :12], use_container_width=True)

    # Distribution glimpse
    st.markdown("#### Library size distribution")
    lib = data.sum(axis=1)
    fig = px.histogram(lib, nbins=50,
                       labels={"value": "Counts per cell", "count": "# cells"},
                       color_discrete_sequence=["#6366f1"])
    fig.update_layout(height=300, margin=dict(l=20, r=20, t=20, b=30),
                      paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                      showlegend=False)
    st.plotly_chart(fig, use_container_width=True)
