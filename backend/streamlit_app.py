"""
SingleCellX v3 — modular single-cell RNA-seq analysis pipeline.

Entry point. Wires together 12 functional modules with an animated UI.
Run with:

    streamlit run streamlit_app.py
"""
from __future__ import annotations

import sys
import traceback
from pathlib import Path

import streamlit as st

# Make the `app` package importable when launched from the backend folder
ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from streamlit_modules import state, theme  # noqa: E402
from streamlit_modules.theme import (        # noqa: E402
    inject_global_css, render_hero, render_pipeline_steps,
    render_status, render_footer,
)
from streamlit_modules.pages import (        # noqa: E402
    home, data_ingestion, qc, normalization, dim_reduction,
    clustering, markers, annotation, cell_cycle, trajectory,
    differential, benchmark, export, settings,
)


PAGE_REGISTRY = [
    ("🏠 Home",              home.render,            None),
    ("📥 Data Ingestion",   data_ingestion.render,  "Data"),
    ("🔍 Quality Control",  qc.render,              "QC"),
    ("⚖️ Normalization",    normalization.render,   "Normalize"),
    ("📉 Dim. Reduction",   dim_reduction.render,   "Dim. reduction"),
    ("🎯 Clustering",       clustering.render,      "Clustering"),
    ("🧬 Markers",          markers.render,         "Markers"),
    ("🩺 Annotation",       annotation.render,      "Annotation"),
    ("🔄 Cell Cycle",       cell_cycle.render,      "Cell cycle"),
    ("🌐 Trajectory",       trajectory.render,      "Trajectory"),
    ("🧪 Diff. Expression", differential.render,    "Diff. expression"),
    ("📐 Benchmark",        benchmark.render,       None),
    ("📤 Export",           export.render,          None),
    ("⚙️ Settings",         settings.render,        None),
]


def _configure() -> None:
    st.set_page_config(
        page_title="SingleCellX v3",
        page_icon="🧬",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    inject_global_css()


def _quick_pipeline() -> None:
    """Run every analysis module end-to-end with current parameters."""
    from app.services.preprocessing import run_qc
    from app.services.dimensionality import run_pca, run_umap, run_tsne
    from app.services.clustering import cluster_cells
    from app.services.markers import find_markers
    from app.services.advanced_analysis import compute_cell_cycle_phase
    from app.services.cell_type_annotation import annotate_clusters
    from app.services.trajectory import infer_pseudotime
    import numpy as np

    data = state.get("data")
    if data is None:
        st.sidebar.error("Load data first.")
        return
    params = state.get("params")
    bar = st.sidebar.progress(0, text="Starting…")
    try:
        bar.progress(5, "QC…")
        r = run_qc(data, min_genes_per_cell=params["min_genes_per_cell"],
                   min_cells_per_gene=params["min_cells_per_gene"])
        state.set_("qc", {**r.to_summary(),
                          "_counts": r.counts, "_normalized": r.normalized})

        bar.progress(20, "PCA…")
        pca = run_pca(r.normalized, n_components=params["n_pca_components"])
        state.set_("pca", {**pca.to_dict(), "_components": pca.components})

        bar.progress(35, "UMAP…")
        try:
            u = run_umap(pca.components,
                         n_neighbors=params["umap_n_neighbors"],
                         min_dist=params["umap_min_dist"])
            state.set_("umap", {**u.to_dict(), "_coords": u.coords})
        except Exception:
            pass

        bar.progress(50, "t-SNE…")
        try:
            t = run_tsne(pca.components)
            state.set_("tsne", {**t.to_dict(), "_coords": t.coords})
        except Exception:
            pass

        bar.progress(65, "Clustering…")
        cl = cluster_cells(pca.components, n_clusters=params["n_clusters"])
        state.set_("clusters", {**cl.to_dict(), "_labels": cl.labels})

        bar.progress(75, "Markers…")
        m = find_markers(r.counts, cl.labels, top_n=params["n_marker_genes"])
        state.set_("markers", m)

        bar.progress(85, "Annotation…")
        try:
            state.set_("annotation", annotate_clusters(r.counts, cl.labels))
        except Exception:
            pass

        bar.progress(92, "Cell cycle…")
        try:
            state.set_("cycle_phases", compute_cell_cycle_phase(r.counts))
        except Exception:
            pass

        bar.progress(97, "Trajectory…")
        try:
            tr = infer_pseudotime(pca.components, k=params["trajectory_k"])
            state.set_("trajectory", {**tr.to_dict(),
                                      "_pseudotime": tr.pseudotime})
        except Exception:
            pass

        bar.progress(100, "Done")
        st.sidebar.success("✅ Quick pipeline complete!")
        st.balloons()
    except Exception as exc:
        st.sidebar.error(f"Pipeline failed: {exc}")
        st.sidebar.code(traceback.format_exc())


def _sidebar() -> str:
    st.sidebar.markdown(
        '<div style="text-align:center;padding:8px 0 14px;">'
        f'{theme._dna_svg(54)}'
        '<div style="font-size:1.3rem;font-weight:800;margin-top:4px;'
        'background:linear-gradient(90deg,#6366f1,#ec4899);'
        '-webkit-background-clip:text;color:transparent;">SingleCellX</div>'
        '<div style="color:#94a3b8;font-size:0.8rem;">v3 · modular pipeline</div>'
        '</div>',
        unsafe_allow_html=True,
    )

    # Status indicator
    data_loaded = state.get("data") is not None
    render_status(
        f"Dataset {'loaded' if data_loaded else 'not loaded'}",
        kind="ok" if data_loaded else "warn",
    )

    st.sidebar.markdown("---")

    # Page navigation
    page_names = [name for name, _, _ in PAGE_REGISTRY]
    page = st.sidebar.radio("Navigate", page_names,
                            index=page_names.index(
                                state.get("page", page_names[0])
                                if state.get("page") in page_names
                                else page_names[0]),
                            label_visibility="collapsed")
    state.set_("page", page)

    st.sidebar.markdown("---")
    st.sidebar.markdown("**Quick actions**")
    if st.sidebar.button("🚀 Run full pipeline", use_container_width=True):
        _quick_pipeline()
    if st.sidebar.button("🔁 Reset pipeline", use_container_width=True):
        state.reset_pipeline(keep_data=True)
        st.sidebar.success("Reset.")

    # Cache mini-card
    from app.services.cache import get_cache
    stats = get_cache().stats()
    st.sidebar.markdown(
        f'<div class="sc-card" style="margin-top:14px;font-size:0.85rem;">'
        f'<b>⚡ Cache</b><br>'
        f'Hits: <b>{stats["hits"]}</b> · Misses: <b>{stats["misses"]}</b><br>'
        f'Items: <b>{stats["cached_items"]}</b>'
        f'</div>',
        unsafe_allow_html=True,
    )

    return page


def main() -> None:
    _configure()
    state.init_state()
    theme.inject_color_overrides(state.get("colors") or {})

    page = _sidebar()

    render_hero(
        "🧬 SingleCellX",
        "A modular, animated single-cell RNA-seq analysis pipeline — "
        "12 functional modules, each producing real results.",
    )

    # Animated step indicator
    render_pipeline_steps(state.PIPELINE_STEPS,
                          current=state.current_step_index())

    # Render selected page
    page_map = {name: fn for name, fn, _ in PAGE_REGISTRY}
    fn = page_map.get(page, home.render)
    try:
        fn()
    except Exception as exc:
        st.error(f"Module crashed: {exc}")
        st.code(traceback.format_exc())

    render_footer("3.0")


if __name__ == "__main__":
    main()
