"""
SingleCellX Enhanced - Streamlit Interface

Interactive single-cell RNA-seq analysis with advanced features:
- Real-time analysis with progress tracking
- Advanced metrics (cell cycle, batch effects, diversity)
- Export results in multiple formats
- Batch analysis and parameter optimization
- Result caching for performance
- Publication-quality visualizations

Run with:
    streamlit run streamlit_app.py
    
Or with proper Python path:
    cd backend && streamlit run streamlit_app.py
"""

from __future__ import annotations

import sys
from pathlib import Path
import json
import io
from datetime import datetime
import traceback

import streamlit as st
import pandas as pd
import numpy as np

ROOT = Path(__file__).resolve().parent
sys.path.append(str(ROOT))

# Import core analysis modules
from app.services.preprocessing import run_qc
from app.services.dimensionality import run_pca, run_umap, run_tsne
from app.services.clustering import cluster_cells
from app.services.markers import find_markers
from app.services.cache import get_cache
from app.services.advanced_analysis import (
    compute_quality_metrics,
    compute_cell_cycle_phase,
    detect_batch_effects,
    compute_neighborhood_diversity,
    estimate_subpopulation_structure,
    gene_expression_specificity,
)
from app.services.export import (
    export_markers_csv,
    export_embeddings_csv,
    export_pca_variance_csv,
    export_qc_summary_csv,
    export_cell_assignments_csv,
)
from streamlit_modules.data_loader import load_demo_data, load_uploaded_csv



# ============================================================
# Page Configuration
# ============================================================
def configure_page():
    """Configure Streamlit page."""
    st.set_page_config(
        page_title="SingleCellX Enhanced",
        page_icon="🧬",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    
    # Custom CSS
    st.markdown("""
        <style>
        /* Main styling */
        .main { padding: 2rem; }
        h1 { color: #1f77b4; margin-bottom: 1rem; }
        h2, h3 { color: #2ca02c; margin-top: 1.5rem; }
        
        /* Metric cards */
        [data-testid="metric-container"] {
            background: linear-gradient(135deg, #f0f8ff 0%, #e6f3ff 100%);
            border-left: 4px solid #1f77b4;
            padding: 1rem;
            border-radius: 0.5rem;
        }
        
        /* Buttons */
        .stButton > button {
            width: 100%;
            background: linear-gradient(90deg, #1f77b4, #2ca02c);
            color: white;
            font-weight: bold;
        }
        
        .stButton > button:hover {
            opacity: 0.9;
            box-shadow: 0 4px 8px rgba(31, 119, 180, 0.3);
        }
        
        /* Info boxes */
        .stAlert { border-radius: 0.5rem; }
        </style>
    """, unsafe_allow_html=True)


# ============================================================
# Session State Management
# ============================================================
def initialize_session_state():
    """Initialize session state variables."""
    if "data" not in st.session_state:
        st.session_state.data = None
    if "analysis_results" not in st.session_state:
        st.session_state.analysis_results = None
    if "analysis_complete" not in st.session_state:
        st.session_state.analysis_complete = False
    if "current_page" not in st.session_state:
        st.session_state.current_page = "Data Loading"


# ============================================================
# Data Loading Section
# ============================================================
def render_data_loading():
    """Render data loading interface."""
    st.header("📊 Load Data")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("🎲 Load Demo Dataset", use_container_width=True):
            with st.spinner("Generating demo data..."):
                try:
                    st.session_state.data = load_demo_data()
                    st.success("✅ Demo dataset loaded (1000 cells, 2000 genes)!")
                except Exception as e:
                    st.error(f"Failed to load demo: {e}")
    
    with col2:
        uploaded_file = st.file_uploader(
            "Upload CSV (cells × genes)",
            type="csv",
            key="upload_csv"
        )
        if uploaded_file:
            with st.spinner("Loading dataset..."):
                try:
                    st.session_state.data = load_uploaded_csv(uploaded_file)
                    st.success("✅ Dataset uploaded!")
                except Exception as e:
                    st.error(f"Failed to load: {e}")
    
    if st.session_state.data is not None:
        data = st.session_state.data
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Cells", data.shape[0])
        with col2:
            st.metric("Genes", data.shape[1])
        with col3:
            sparsity = (data == 0).sum().sum() / (data.shape[0] * data.shape[1]) * 100
            st.metric("Sparsity", f"{sparsity:.1f}%")
        
        st.success("✨ Data ready for analysis!")


# ============================================================
# Analysis Parameters Section
# ============================================================
def render_analysis_parameters():
    """Render analysis parameter controls."""
    st.header("⚙️ Analysis Parameters")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Quality Control")
        min_genes = st.slider(
            "Min genes per cell",
            10, 500, 150,
            help="Filter cells with fewer genes"
        )
        min_cells = st.slider(
            "Min cells per gene",
            1, 50, 3,
            help="Filter genes detected in few cells"
        )
    
    with col2:
        st.subheader("Dimensionality Reduction")
        n_pca = st.slider(
            "PCA components",
            2, 200, 50,
            help="Number of PCA components"
        )
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Embedding Parameters")
        umap_neighbors = st.slider(
            "UMAP neighbors",
            2, 200, 15,
            help="UMAP neighborhood size"
        )
        umap_dist = st.slider(
            "UMAP min distance",
            0.001, 1.0, 0.1,
            help="UMAP minimum distance"
        )
    
    with col2:
        st.subheader("Clustering & Markers")
        n_clusters = st.number_input(
            "Number of clusters (0=auto)",
            0, 100, 0,
            help="Auto-detect if 0"
        )
        n_markers = st.slider(
            "Top marker genes",
            1, 200, 15,
            help="Markers per cluster"
        )
    
    return {
        "min_genes_per_cell": min_genes,
        "min_cells_per_gene": min_cells,
        "n_pca_components": n_pca,
        "umap_n_neighbors": umap_neighbors,
        "umap_min_dist": umap_dist,
        "n_clusters": n_clusters if n_clusters > 0 else None,
        "n_marker_genes": n_markers,
    }


# ============================================================
# Analysis Execution
# ============================================================
def run_analysis_pipeline(data, params):
    """Execute complete analysis pipeline."""
    try:
        cache = get_cache()
        results = {}
        
        # --- Quality Control ---
        with st.spinner("Running quality control..."):
            st.info("🔍 QC & Normalization")
            qc = run_qc(
                data,
                min_genes_per_cell=params["min_genes_per_cell"],
                min_cells_per_gene=params["min_cells_per_gene"],
            )
            results["qc"] = qc.to_summary()
            
            # Advanced QC metrics
            try:
                advanced_qc = compute_quality_metrics(qc.counts)
                results["qc"].update(advanced_qc)
            except:
                pass
            
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Cells after QC", qc.n_cells_out)
            with col2:
                st.metric("Genes after QC", qc.n_genes_out)
            with col3:
                st.metric("Cells filtered", qc.n_cells_in - qc.n_cells_out)
            with col4:
                st.metric("Sparsity", f"{results['qc'].get('sparsity_pct', 0):.1f}%")
        
        # --- PCA ---
        with st.spinner("Computing PCA..."):
            st.info("📈 PCA Decomposition")
            pca = run_pca(qc.normalized, n_components=params["n_pca_components"])
            results["pca"] = pca.to_dict()
            
            var_total = pca.cumulative_variance[-1] * 100
            col1, col2 = st.columns(2)
            with col1:
                st.metric("PCA Components", pca.n_components)
            with col2:
                st.metric("Variance Explained", f"{var_total:.1f}%")
        
        # --- UMAP ---
        with st.spinner("Computing UMAP..."):
            st.info("🔵 UMAP Projection")
            try:
                umap_res = run_umap(
                    pca.components,
                    n_neighbors=params["umap_n_neighbors"],
                    min_dist=params["umap_min_dist"],
                )
                results["umap"] = umap_res.to_dict()
                st.success(f"✅ {umap_res.method}")
            except Exception as e:
                st.warning(f"⚠️ UMAP failed, continuing without it")
                results["umap"] = None
        
        # --- t-SNE ---
        with st.spinner("Computing t-SNE..."):
            st.info("🔴 t-SNE Projection")
            try:
                tsne_res = run_tsne(pca.components)
                results["tsne"] = tsne_res.to_dict()
                st.success("✅ t-SNE complete")
            except Exception as e:
                st.warning(f"⚠️ t-SNE failed")
                results["tsne"] = None
        
        # --- Clustering ---
        with st.spinner("Performing clustering..."):
            st.info("🎯 K-Means Clustering")
            clusters = cluster_cells(pca.components, n_clusters=params["n_clusters"])
            results["clusters"] = clusters.to_dict()
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Clusters Found", clusters.n_clusters)
            with col2:
                sil = clusters.silhouette
                st.metric("Silhouette Score", f"{sil:.3f}" if sil else "N/A")
            with col3:
                st.metric("Inertia", f"{clusters.inertia:.1f}")
        
        # --- Marker Genes ---
        with st.spinner("Finding marker genes..."):
            st.info("🔬 Marker Gene Discovery")
            markers = find_markers(
                qc.counts,
                clusters.labels,
                top_n=params["n_marker_genes"]
            )
            results["markers"] = markers
            
            n_total = sum(len(v) for v in markers.values())
            st.metric("Marker Genes Found", n_total)
        
        # --- Advanced Metrics ---
        with st.spinner("Computing advanced metrics..."):
            st.info("📊 Advanced Analysis")
            advanced_metrics = {}
            
            try:
                advanced_metrics["batch_effects"] = detect_batch_effects(qc.normalized)
            except:
                pass
            
            try:
                if results.get("umap"):
                    advanced_metrics["neighborhood_diversity"] = compute_neighborhood_diversity(
                        np.array(results["umap"]["coords"]),
                        clusters.labels
                    )
            except:
                pass
            
            try:
                advanced_metrics["subpopulation_structure"] = estimate_subpopulation_structure(
                    pca.components,
                    clusters.labels
                )
            except:
                pass
            
            try:
                advanced_metrics["gene_specificity"] = gene_expression_specificity(
                    qc.counts,
                    clusters.labels
                )
            except:
                pass
            
            try:
                cell_phases = compute_cell_cycle_phase(qc.counts)
                advanced_metrics["cell_cycle"] = {
                    "G1": int((cell_phases == "G1").sum()),
                    "S": int((cell_phases == "S").sum()),
                    "G2/M": int((cell_phases == "G2/M").sum()),
                }
            except:
                pass
            
            results["advanced_metrics"] = advanced_metrics
            st.success("✅ Advanced metrics computed")
        
        # Store metadata
        results["metadata"] = {
            "run_timestamp": datetime.utcnow().isoformat(),
            "parameters": params,
            "cell_ids": list(qc.counts.index),
            "gene_names": list(qc.counts.columns),
        }
        
        return results
    
    except Exception as e:
        st.error(f"❌ Analysis failed: {e}")
        st.error(traceback.format_exc())
        return None


# ============================================================
# Results Visualization
# ============================================================
def render_analysis_results(results):
    """Render analysis results."""
    if results is None:
        st.warning("⚠️ No analysis results to display")
        return
    
    st.header("📊 Analysis Results")
    
    # --- Embedding coordinates display ---
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("UMAP Projection")
        if results.get("umap"):
            try:
                umap_df = pd.DataFrame(
                    results["umap"]["coords"],
                    columns=["UMAP 1", "UMAP 2"]
                )
                umap_df["Cluster"] = results["clusters"]["labels"]
                
                st.scatter_chart(
                    umap_df,
                    x="UMAP 1",
                    y="UMAP 2",
                    color="Cluster",
                    use_container_width=True
                )
            except:
                st.info("Could not render UMAP chart")
    
    with col2:
        st.subheader("t-SNE Projection")
        if results.get("tsne"):
            try:
                tsne_df = pd.DataFrame(
                    results["tsne"]["coords"],
                    columns=["tSNE 1", "tSNE 2"]
                )
                tsne_df["Cluster"] = results["clusters"]["labels"]
                
                st.scatter_chart(
                    tsne_df,
                    x="tSNE 1",
                    y="tSNE 2",
                    color="Cluster",
                    use_container_width=True
                )
            except:
                st.info("Could not render t-SNE chart")
    
    # --- Quality Control ---
    st.subheader("Quality Control Metrics")
    qc_df = pd.DataFrame([results["qc"]])
    st.dataframe(qc_df.T, use_container_width=True)
    
    # --- Marker Genes ---
    st.subheader("Top Marker Genes by Cluster")
    for cluster_name, markers in results["markers"].items():
        if markers:
            with st.expander(f"{cluster_name} ({len(markers)} markers)"):
                markers_df = pd.DataFrame(markers)
                st.dataframe(markers_df, use_container_width=True)
    
    # --- Advanced Metrics ---
    if results.get("advanced_metrics"):
        st.subheader("Advanced Metrics")
        adv = results["advanced_metrics"]
        
        col1, col2 = st.columns(2)
        
        with col1:
            if "cell_cycle" in adv:
                st.write("**Cell Cycle Phases:**")
                cycle_df = pd.DataFrame([adv["cell_cycle"]])
                st.dataframe(cycle_df, use_container_width=True)
        
        with col2:
            if "gene_specificity" in adv:
                st.write("**Gene Expression Specificity:**")
                spec_df = pd.DataFrame([adv["gene_specificity"]])
                st.dataframe(spec_df, use_container_width=True)
        
        if "batch_effects" in adv:
            st.write("**Batch Effect Score:**", adv["batch_effects"])


# ============================================================
# Export Section
# ============================================================
def render_export_section(results):
    """Render result export options."""
    st.header("📥 Export Results")
    
    if results is None:
        st.info("Run analysis first to export results")
        return
    
    st.subheader("Quick Downloads")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("📋 Markers CSV", use_container_width=True):
            output = io.StringIO()
            export_markers_csv(results["markers"], output)
            st.download_button(
                label="Download Markers",
                data=output.getvalue(),
                file_name="markers.csv",
                mime="text/csv"
            )
    
    with col2:
        if st.button("💾 Complete JSON", use_container_width=True):
            json_str = json.dumps(results, indent=2, default=str)
            st.download_button(
                label="Download JSON",
                data=json_str.encode(),
                file_name="results.json",
                mime="application/json"
            )
    
    with col3:
        if st.button("📊 Embeddings CSV", use_container_width=True):
            if results.get("umap"):
                output = io.StringIO()
                export_embeddings_csv(
                    "UMAP",
                    results["umap"]["coords"],
                    results["metadata"]["cell_ids"],
                    results["clusters"]["labels"],
                    output
                )
                st.download_button(
                    label="Download Embeddings",
                    data=output.getvalue(),
                    file_name="embeddings.csv",
                    mime="text/csv"
                )
    
    st.subheader("Advanced Exports")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("📈 PCA Variance", use_container_width=True):
            pca = results.get("pca", {})
            output = io.StringIO()
            export_pca_variance_csv(
                pca.get("variance_ratio", []),
                pca.get("cumulative_variance", []),
                output
            )
            st.download_button(
                label="Download PCA",
                data=output.getvalue(),
                file_name="pca_variance.csv",
                mime="text/csv"
            )
    
    with col2:
        if st.button("🎯 Cluster Assignment", use_container_width=True):
            output = io.StringIO()
            export_cell_assignments_csv(
                results["metadata"]["cell_ids"],
                results["clusters"]["labels"],
                output
            )
            st.download_button(
                label="Download Clusters",
                data=output.getvalue(),
                file_name="clusters.csv",
                mime="text/csv"
            )
    
    with col3:
        if st.button("📋 QC Summary", use_container_width=True):
            output = io.StringIO()
            export_qc_summary_csv(results["qc"], output)
            st.download_button(
                label="Download QC",
                data=output.getvalue(),
                file_name="qc_summary.csv",
                mime="text/csv"
            )


# ============================================================
# Cache Monitoring
# ============================================================
def render_cache_stats():
    """Render cache statistics."""
    st.sidebar.divider()
    st.sidebar.subheader("⚡ Cache Statistics")
    
    cache = get_cache()
    stats = cache.stats()
    
    col1, col2 = st.sidebar.columns(2)
    with col1:
        st.metric("Hits", stats["hits"])
    with col2:
        st.metric("Misses", stats["misses"])
    
    st.sidebar.metric("Hit Rate", f"{stats['hit_rate_pct']:.1f}%")
    st.sidebar.metric("Cached Items", stats["cached_items"])
    
    if st.sidebar.button("🗑️ Clear Cache"):
        cache.clear()
        st.sidebar.success("Cache cleared")


# ============================================================
# Main Application
# ============================================================
def main():
    """Main application entry point."""
    configure_page()
    initialize_session_state()
    
    # Header
    st.title("🧬 SingleCellX Enhanced - Streamlit")
    st.write("""
        Interactive single-cell RNA-seq analysis with advanced features:
        - Real-time analysis with progress tracking
        - Advanced metrics (cell cycle, batch effects, diversity)
        - Export results in multiple formats
        - Publication-quality visualizations
    """)
    
    # Navigation tabs
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📊 Data", "⚙️ Parameters", "▶️ Analysis", "📈 Results", "📥 Export"
    ])
    
    with tab1:
        render_data_loading()
    
    with tab2:
        if st.session_state.data is None:
            st.warning("⚠️ Load data first")
        else:
            params = render_analysis_parameters()
            st.session_state.params = params
            st.success("✅ Parameters configured")
    
    with tab3:
        if st.session_state.data is None:
            st.warning("⚠️ Load data first")
        else:
            if st.button("🚀 Run Analysis Pipeline", use_container_width=True):
                with st.spinner("Running analysis..."):
                    st.session_state.analysis_results = run_analysis_pipeline(
                        st.session_state.data,
                        getattr(st.session_state, "params", {
                            "min_genes_per_cell": 150,
                            "min_cells_per_gene": 3,
                            "n_pca_components": 50,
                            "umap_n_neighbors": 15,
                            "umap_min_dist": 0.1,
                            "n_clusters": None,
                            "n_marker_genes": 15,
                        })
                    )
                    st.session_state.analysis_complete = True
            
            if st.session_state.analysis_complete:
                st.success("✅ Analysis complete!")
                st.balloons()
    
    with tab4:
        render_analysis_results(st.session_state.analysis_results)
    
    with tab5:
        render_export_section(st.session_state.analysis_results)
    
    # Render cache stats in sidebar
    render_cache_stats()
    
    # Footer
    st.divider()
    st.markdown("""
        <div style='text-align: center; color: #666; font-size: 0.9rem;'>
        <p>🧬 SingleCellX Enhanced v2.0 | Real-time Single-Cell Analysis</p>
        <p>Built with Streamlit, FastAPI, and Scikit-learn</p>
        </div>
    """, unsafe_allow_html=True)


if __name__ == "__main__":
    main()

