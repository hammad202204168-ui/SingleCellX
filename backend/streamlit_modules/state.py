"""
Central pipeline state manager.

Holds the shared session-state keys used by every page module so they
can each read/write without stomping on each other, and provides the
canonical step order used by the animated stepper.
"""
from __future__ import annotations

from typing import Any, Optional

import streamlit as st


PIPELINE_STEPS = [
    "Data",
    "QC",
    "Normalize",
    "Dim. reduction",
    "Clustering",
    "Markers",
    "Annotation",
    "Cell cycle",
    "Trajectory",
    "Diff. expression",
]


DEFAULT_PARAMS = {
    # QC
    "min_genes_per_cell": 150,
    "min_cells_per_gene": 3,
    "max_pct_mito": 20.0,
    "use_ribo_filter": False,
    "max_pct_ribo": 50.0,
    "run_doublets": False,
    "expected_doublet_rate": 0.06,
    # PCA
    "n_pca_components": 50,
    # UMAP
    "umap_n_neighbors": 15,
    "umap_min_dist": 0.1,
    # Clustering
    "n_clusters": None,
    "cluster_k_nn": 15,
    "cluster_resolution": 1.0,
    # Markers
    "n_marker_genes": 15,
    # Trajectory
    "trajectory_k": 15,
    # Demo data
    "demo_n_cells": 600,
    "demo_n_genes": 2500,
    "demo_n_clusters": 6,
    "demo_seed": 42,
}


SESSION_KEYS = (
    "data", "qc", "pca", "umap", "tsne", "clusters", "markers",
    "annotation", "cycle_phases", "trajectory", "de_table", "de_pair",
    "benchmark", "params", "current_step",
)


def init_state() -> None:
    """Initialize every session-state key the app relies on."""
    for k in SESSION_KEYS:
        st.session_state.setdefault(k, None)
    if st.session_state.get("params") is None:
        st.session_state["params"] = dict(DEFAULT_PARAMS)
    st.session_state.setdefault("current_step", None)
    st.session_state.setdefault("page", "🏠 Home")


def get(key: str, default: Any = None) -> Any:
    return st.session_state.get(key, default)


def set_(key: str, value: Any) -> None:
    st.session_state[key] = value


def reset_pipeline(keep_data: bool = True) -> None:
    """Clear downstream results without touching loaded data (by default)."""
    keep = {"data", "params", "page"} if keep_data else set()
    for k in SESSION_KEYS:
        if k not in keep:
            st.session_state[k] = None
    st.session_state["current_step"] = None


def step_completed(step_name: str) -> bool:
    """Heuristic: a step is 'done' when its result key is populated."""
    mapping = {
        "Data":              "data",
        "QC":                "qc",
        "Normalize":         "qc",            # normalization lives inside QC result
        "Dim. reduction":    "pca",
        "Clustering":        "clusters",
        "Markers":           "markers",
        "Annotation":        "annotation",
        "Cell cycle":        "cycle_phases",
        "Trajectory":        "trajectory",
        "Diff. expression":  "de_table",
    }
    return get(mapping.get(step_name, "")) is not None


def current_step_index() -> Optional[int]:
    """Index into PIPELINE_STEPS of the highest completed step (+1 if running)."""
    last_done = -1
    for i, s in enumerate(PIPELINE_STEPS):
        if step_completed(s):
            last_done = i
    return last_done if last_done >= 0 else None
