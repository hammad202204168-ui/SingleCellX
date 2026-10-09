"""Home / dashboard — landing page with pipeline status and quick actions."""
from __future__ import annotations

import streamlit as st

from streamlit_modules import state
from streamlit_modules.theme import render_card


def render() -> None:
    st.subheader("Welcome to the pipeline")
    st.write(
        "SingleCellX is a modular single-cell RNA-seq analysis toolkit. "
        "Use the sidebar to navigate; each module performs a real, "
        "reproducible step of the pipeline and feeds into the next."
    )

    # Pipeline status overview
    cols = st.columns(4)
    data = state.get("data")
    qc = state.get("qc")
    clusters = state.get("clusters")
    markers = state.get("markers")

    with cols[0]:
        st.metric("Dataset", "Loaded ✓" if data is not None else "—",
                  f"{data.shape[0]} × {data.shape[1]}" if data is not None else "no data")
    with cols[1]:
        st.metric("QC", "Done ✓" if qc is not None else "—",
                  f"{qc['cells_after_qc']} cells" if qc else "pending")
    with cols[2]:
        st.metric("Clusters", str(clusters["n_clusters"]) if clusters else "—",
                  f"silhouette {clusters['silhouette']:.3f}" if clusters and clusters.get("silhouette") else "pending")
    with cols[3]:
        total_markers = sum(len(v) for v in markers.values()) if markers else 0
        st.metric("Markers", str(total_markers) if markers else "—",
                  "across clusters" if markers else "pending")

    st.write("")

    # Module gallery
    col1, col2, col3 = st.columns(3)
    modules = [
        ("📥 Data Ingestion", "Load demo data or upload your own CSV expression matrix."),
        ("🔍 Quality Control", "Filter low-quality cells and rarely-detected genes."),
        ("⚖️ Normalization", "Library-size, log1p, z-score scaling + HVG selection."),
        ("📉 Dim. Reduction", "PCA scree, UMAP, t-SNE and an interactive 3D PCA view."),
        ("🎯 Clustering", "k-Means with elbow / silhouette diagnostics."),
        ("🧬 Marker Genes", "One-vs-rest DE testing per cluster."),
        ("🩺 Annotation", "Marker-panel scoring → cell-type labels per cluster."),
        ("🔄 Cell Cycle", "S / G2M phase scoring with summary plots."),
        ("🌐 Trajectory", "k-NN-graph geodesic pseudotime ordering."),
        ("🧪 Diff. Expression", "Pairwise cluster DE with volcano plots."),
        ("📐 Benchmark", "ARI / NMI / purity vs. ground-truth labels."),
        ("📤 Export", "CSV / JSON / HTML / AnnData / ZIP bundles."),
        ("⚙️ Settings", "Parameter persistence and cache controls."),
    ]
    for i, (title, desc) in enumerate(modules):
        col = (col1, col2, col3)[i % 3]
        with col:
            render_card(title, f"<p style='color:#94a3b8;margin:0;'>{desc}</p>")

    # Tip
    st.info(
        "💡 **Tip** — start with **Data Ingestion** → run the **Quick Pipeline** "
        "in the sidebar to populate every module at once."
    )
