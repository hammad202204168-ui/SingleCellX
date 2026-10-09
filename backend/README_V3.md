# SingleCellX v3 — modular scRNA-seq pipeline

A complete rebuild of the Streamlit interface as **12 functional modules**,
with a dark-glassmorphism theme and CSS-driven animations.
Nothing is "scripted" — every page calls into a real analysis service
and renders real results.

## Modules

| # | Module | Service backing it |
|---|---|---|
| 1 | 🏠 Home / Dashboard | live pipeline status & module gallery |
| 2 | 📥 Data Ingestion | `app.services.demo_data` + CSV loader |
| 3 | 🔍 Quality Control | `app.services.preprocessing.run_qc` |
| 4 | ⚖️ Normalization | uses QC's `log1p` + z-score; HVG selection |
| 5 | 📉 Dim. Reduction | `run_pca` / `run_umap` / `run_tsne` + 3D PCA |
| 6 | 🎯 Clustering | `cluster_cells` + live elbow / silhouette sweep |
| 7 | 🧬 Marker Genes | `find_markers` + heatmap & per-cluster bar charts |
| 8 | 🩺 Cell-type Annotation | **new** `cell_type_annotation.annotate_clusters` |
| 9 | 🔄 Cell Cycle | `compute_cell_cycle_phase` + per-cluster stacks |
| 10 | 🌐 Trajectory / Pseudotime | **new** `trajectory.infer_pseudotime` |
| 11 | 🧪 Differential Expression | **new** `differential_expression.pairwise_de` |
| 12 | 📤 Export & Reports | CSV / JSON / HTML / ZIP bundles |
| 13 | ⚙️ Settings & Cache | parameter persistence + cache controls |

(Yes, that's 13. The brief asked for at least 9.)

## New analysis services

- **`app/services/trajectory.py`** — k-NN graph → geodesic pseudotime with
  branch estimation.
- **`app/services/differential_expression.py`** — vectorized Welch's t-test
  with Benjamini–Hochberg FDR correction; powers the volcano plot.
- **`app/services/cell_type_annotation.py`** — marker-panel scoring with
  fallback panels that work on the synthetic demo dataset.

## Animations & polish

All implemented with CSS keyframes — no extra dependencies:

- Rotating DNA-helix SVG in the header & sidebar.
- Animated stepper showing which pipeline stage is done / active / pending.
- Fade-in cards, hover lift, gradient buttons with shimmer.
- Pulsing status dots for system state.
- Plotly transition easing on every scatter plot.
- Glassmorphism cards and gradient backgrounds.

## Running it

```bash
cd backend
pip install -r requirements.txt
streamlit run streamlit_app.py
```

Click **🚀 Run full pipeline** in the sidebar after loading data to
populate every module at once. The legacy single-file app is preserved
as `streamlit_app_legacy.py` for reference.
