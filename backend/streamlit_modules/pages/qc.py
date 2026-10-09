"""Quality control module — counts/genes filter + mito/ribo + doublet flagging."""
from __future__ import annotations

import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from app.services.preprocessing import run_qc
from app.services.advanced_analysis import compute_quality_metrics
from app.services.qc_extras import per_cell_qc, filter_by_thresholds, detect_doublets
from streamlit_modules import state


def _hist(values, title, color):
    fig = go.Figure(go.Histogram(x=values, nbinsx=40,
                                 marker_color=color, opacity=0.85))
    fig.update_layout(title=title, height=260,
                      margin=dict(l=20, r=20, t=40, b=30),
                      paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                      showlegend=False, bargap=0.04)
    return fig


def render() -> None:
    st.subheader("🔍 Quality Control")

    data = state.get("data")
    if data is None:
        st.warning("Load a dataset in **Data Ingestion** first.")
        return

    params = state.get("params")

    # ---- Per-cell QC preview (mito / ribo / counts) ----
    qc_table = per_cell_qc(data)
    qcols = st.columns(4)
    qcols[0].metric("Median genes/cell",  f"{qc_table['n_genes'].median():.0f}")
    qcols[1].metric("Median counts/cell", f"{qc_table['n_counts'].median():.0f}")
    qcols[2].metric("Median %mito",       f"{qc_table['pct_mito'].median():.2f}%")
    qcols[3].metric("Median %ribo",       f"{qc_table['pct_ribo'].median():.2f}%")
    if qc_table['pct_mito'].max() == 0 and qc_table['pct_ribo'].max() == 0:
        st.caption("⚠️ No `MT-` or `RPS/RPL` genes detected — this is "
                   "synthetic demo data. Mito/ribo filters will be no-ops.")

    pc1, pc2 = st.columns(2)
    pc1.plotly_chart(_hist(qc_table['n_genes'].values, "Genes per cell (raw)",
                           "#06b6d4"), use_container_width=True)
    pc2.plotly_chart(_hist(qc_table['pct_mito'].values,
                           "% mitochondrial reads", "#ec4899"),
                     use_container_width=True)

    st.divider()
    st.markdown("### Filtering thresholds")

    c1, c2 = st.columns(2)
    with c1:
        st.markdown("**Basic filters**")
        min_genes = st.slider("Min genes per cell", 10, 1000,
                              value=params["min_genes_per_cell"], step=10)
        min_cells = st.slider("Min cells per gene", 1, 100,
                              value=params["min_cells_per_gene"])
    with c2:
        st.markdown("**Content filters**")
        max_mito = st.slider("Max %mito", 0.0, 100.0,
                             value=float(params.get("max_pct_mito", 20.0)))
        use_ribo = st.checkbox("Also apply max %ribo",
                               value=params.get("use_ribo_filter", False))
        max_ribo = st.slider("Max %ribo", 0.0, 100.0,
                             value=float(params.get("max_pct_ribo", 50.0)),
                             disabled=not use_ribo)

    c3, c4 = st.columns(2)
    with c3:
        run_doublets = st.checkbox(
            "Also detect & remove doublets (Scrublet-style)",
            value=params.get("run_doublets", False),
        )
    with c4:
        expected_doublet_rate = st.slider(
            "Expected doublet rate", 0.01, 0.20,
            value=float(params.get("expected_doublet_rate", 0.06)),
            step=0.01, disabled=not run_doublets,
        )

    run = st.button("▶️ Run QC", use_container_width=True)

    if run:
        with st.spinner("Filtering and normalizing…"):
            try:
                # Stage 1: mito/ribo pre-filter
                filtered, keep_mask = filter_by_thresholds(
                    data,
                    max_pct_mito=max_mito,
                    max_pct_ribo=max_ribo if use_ribo else None,
                )
                n_removed_content = int((~keep_mask).sum())

                # Stage 2: standard run_qc (gene/cell count filters + normalize)
                result = run_qc(filtered,
                                min_genes_per_cell=int(min_genes),
                                min_cells_per_gene=int(min_cells))

                # Stage 3: doublet detection on normalized matrix
                n_doublets = 0
                doublet_info = None
                if run_doublets and result.normalized.shape[0] >= 10:
                    dres = detect_doublets(
                        result.normalized,
                        expected_rate=float(expected_doublet_rate),
                    )
                    n_doublets = int(dres.predicted.sum())
                    if 0 < n_doublets < result.normalized.shape[0] - 5:
                        keep = ~dres.predicted
                        result.counts = result.counts.loc[keep]
                        result.normalized = result.normalized.loc[keep]
                        result.n_cells_out = int(keep.sum())
                    doublet_info = dres.to_dict()

                summary = result.to_summary()
                try:
                    summary.update(compute_quality_metrics(result.counts))
                except Exception:
                    pass
                summary["cells_removed_content_filter"] = n_removed_content
                summary["cells_removed_doublets"] = n_doublets

                state.set_("qc", {**summary,
                                  "_counts": result.counts,
                                  "_normalized": result.normalized,
                                  "_doublets": doublet_info})

                params["min_genes_per_cell"] = int(min_genes)
                params["min_cells_per_gene"] = int(min_cells)
                params["max_pct_mito"] = float(max_mito)
                params["use_ribo_filter"] = bool(use_ribo)
                params["max_pct_ribo"] = float(max_ribo)
                params["run_doublets"] = bool(run_doublets)
                params["expected_doublet_rate"] = float(expected_doublet_rate)
            except Exception as exc:
                st.error(f"QC failed: {exc}")
                return
        st.success("✅ QC complete — downstream modules can now run.")

    qc = state.get("qc")
    if qc is None:
        st.info("Click **Run QC** to populate the next modules.")
        return

    st.divider()
    st.markdown("### QC summary")
    cols = st.columns(6)
    cols[0].metric("Cells after",       qc["cells_after_qc"])
    cols[1].metric("Genes after",       qc["genes_after_qc"])
    cols[2].metric("Cells filtered",    qc["cells_filtered"])
    cols[3].metric("Genes filtered",    qc["genes_filtered"])
    cols[4].metric("Mito/ribo removed", qc.get("cells_removed_content_filter", 0))
    cols[5].metric("Doublets removed",  qc.get("cells_removed_doublets", 0))

    post = per_cell_qc(qc["_counts"])
    f1, f2, f3 = st.columns(3)
    f1.plotly_chart(_hist(post['n_genes'].values, "Genes / cell (post)",
                          "#10b981"), use_container_width=True)
    f2.plotly_chart(_hist(post['n_counts'].values, "Counts / cell (post)",
                          "#f59e0b"), use_container_width=True)
    f3.plotly_chart(_hist(post['pct_mito'].values, "% mito (post)",
                          "#a855f7"), use_container_width=True)

    dinfo = qc.get("_doublets")
    if dinfo is not None:
        st.markdown("### Doublet detection")
        d1, d2, d3 = st.columns(3)
        d1.metric("Score threshold", f"{dinfo['threshold']:.3f}")
        d2.metric("Expected rate", f"{dinfo['expected_rate']:.1%}")
        d3.metric("Detected rate", f"{dinfo['detected_rate']:.1%}")
        fig = px.histogram(x=dinfo["scores"], nbins=40,
                           color_discrete_sequence=["#ec4899"],
                           labels={"x": "Doublet score"},
                           title="Per-cell doublet score distribution")
        fig.add_vline(x=dinfo["threshold"], line_color="white",
                      line_dash="dash",
                      annotation_text=f"cutoff = {dinfo['threshold']:.2f}")
        fig.update_layout(height=300, margin=dict(l=20, r=20, t=40, b=30),
                          paper_bgcolor="rgba(0,0,0,0)",
                          plot_bgcolor="rgba(0,0,0,0)", showlegend=False)
        st.plotly_chart(fig, use_container_width=True)

    with st.expander("All QC metrics"):
        keep = {k: v for k, v in qc.items() if not k.startswith("_")}
        st.json(keep)
