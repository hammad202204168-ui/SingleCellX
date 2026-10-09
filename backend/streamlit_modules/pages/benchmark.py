"""Benchmark page — quantitative comparison vs ground-truth labels."""
from __future__ import annotations

import io

import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st

from app.services.benchmark import (
    extract_demo_ground_truth, benchmark_clusters, purity_table, compare_methods,
)
from app.services.clustering import cluster_cells
from app.services.graph_clustering import cluster_graph
from streamlit_modules import state


def _read_truth_upload(uploaded) -> pd.Series | None:
    """Accept a 2-column CSV: cell_id, true_label."""
    try:
        df = pd.read_csv(io.BytesIO(uploaded.getvalue()))
    except Exception as exc:
        st.error(f"Failed to parse CSV: {exc}")
        return None
    if df.shape[1] < 2:
        st.error("Need at least 2 columns: cell_id, true_label.")
        return None
    return pd.Series(df.iloc[:, 1].values, index=df.iloc[:, 0].astype(str))


def render() -> None:
    st.subheader("📐 Benchmark vs ground truth")
    st.markdown(
        "Validate your pipeline against a **labeled** reference dataset. "
        "For the bundled demo data the ground truth is encoded in the "
        "cell IDs (`Cell_C<k>_<i>`) so the benchmark works out of the box. "
        "For real data, upload a CSV mapping `cell_id → true_label`."
    )

    qc = state.get("qc")
    pca = state.get("pca")
    clusters = state.get("clusters")
    if qc is None or pca is None:
        st.warning("Run **QC** and **Dim. Reduction** first.")
        return

    counts = qc["_counts"]
    components = np.asarray(pca["_components"])
    cell_ids = list(counts.index)

    # Ground truth source
    src = st.radio("Ground truth source",
                   ["🎲 From demo cell IDs", "📁 Upload CSV"],
                   horizontal=True)

    true_series: pd.Series | None = None
    if src.startswith("🎲"):
        truth = extract_demo_ground_truth(cell_ids)
        if truth is None:
            st.error(
                "Demo cell-ID pattern not detected. Either load a demo "
                "dataset or upload a CSV."
            )
            return
        true_series = pd.Series(truth, index=cell_ids)
        st.caption(f"Detected {len(np.unique(truth))} ground-truth classes.")
    else:
        up = st.file_uploader("CSV with `cell_id,true_label` columns",
                              type=["csv"], key="truth_upload")
        if up is None:
            st.info("Upload a ground-truth CSV to continue.")
            return
        true_series = _read_truth_upload(up)
        if true_series is None:
            return

    # Align with current cells (post-QC may have removed some)
    aligned = true_series.reindex(cell_ids)
    if aligned.isna().any():
        st.warning(
            f"{aligned.isna().sum()} cells have no ground-truth label "
            f"and will be ignored."
        )
        valid_mask = aligned.notna().values
    else:
        valid_mask = np.ones(len(cell_ids), dtype=bool)
    true_labels = aligned[valid_mask].astype("category").cat.codes.values

    # Methods to compare
    st.markdown("### Methods to evaluate")
    c1, c2, c3 = st.columns(3)
    use_current = c1.checkbox("Current clustering", value=True,
                              disabled=clusters is None)
    use_kmeans = c2.checkbox("K-means sweep (k = n_true)", value=True)
    use_leiden = c3.checkbox("Leiden (default settings)", value=True)

    if st.button("▶️ Run benchmark", use_container_width=True):
        results = {}
        n_true = int(len(np.unique(true_labels)))
        comps_valid = components[valid_mask]

        if use_current and clusters is not None:
            results["Current (active)"] = (
                np.asarray(clusters["_labels"])[valid_mask]
            )

        if use_kmeans:
            try:
                with st.spinner("Running k-means…"):
                    km = cluster_cells(components, n_clusters=n_true)
                    results[f"K-means (k={n_true})"] = km.labels[valid_mask]
            except Exception as exc:
                st.warning(f"K-means failed: {exc}")

        if use_leiden:
            try:
                with st.spinner("Running Leiden…"):
                    le = cluster_graph(components, method="leiden",
                                       k=15, resolution=1.0)
                    results["Leiden (r=1.0)"] = le.labels[valid_mask]
            except Exception as exc:
                st.warning(f"Leiden failed: {exc}")

        if not results:
            st.error("Select at least one method.")
            return

        with st.spinner("Computing ARI / NMI / FMI / silhouette…"):
            comparison = compare_methods(results, true_labels,
                                         embedding=comps_valid)
            state.set_("benchmark", {
                "comparison": comparison,
                "per_method_labels": {k: v.tolist() for k, v in results.items()},
                "true_labels": true_labels.tolist(),
            })

    bench = state.get("benchmark")
    if bench is None:
        st.info("Click **Run benchmark** to compare methods.")
        return

    comparison = bench["comparison"]
    st.markdown("### Comparison")
    st.dataframe(comparison, use_container_width=True, hide_index=True)

    # Bar chart of ARI / NMI / FMI
    metrics_long = comparison.melt(id_vars=["method"],
                                   value_vars=[m for m in ["ari", "nmi", "fmi"]
                                               if m in comparison.columns],
                                   var_name="metric", value_name="score")
    fig = px.bar(metrics_long, x="method", y="score", color="metric",
                 barmode="group",
                 color_discrete_sequence=px.colors.qualitative.Bold,
                 title="Agreement with ground truth (higher = better)")
    fig.update_layout(height=400, margin=dict(l=20, r=20, t=40, b=80),
                      paper_bgcolor="rgba(0,0,0,0)",
                      plot_bgcolor="rgba(0,0,0,0)",
                      yaxis=dict(range=[0, 1]))
    st.plotly_chart(fig, use_container_width=True)

    # Per-cluster purity for top method
    top_method = comparison.iloc[0]["method"]
    top_labels = np.asarray(bench["per_method_labels"][top_method])
    truth = np.asarray(bench["true_labels"])
    pt = purity_table(top_labels, truth)
    st.markdown(f"### Per-cluster purity — **{top_method}**")
    st.dataframe(pt, use_container_width=True, hide_index=True)
    fig = px.bar(pt, x="predicted_cluster", y="purity", color="purity",
                 color_continuous_scale="Viridis",
                 title="Purity of each predicted cluster")
    fig.update_layout(height=320, yaxis=dict(range=[0, 1]),
                      margin=dict(l=20, r=20, t=40, b=40),
                      paper_bgcolor="rgba(0,0,0,0)",
                      plot_bgcolor="rgba(0,0,0,0)")
    st.plotly_chart(fig, use_container_width=True)
