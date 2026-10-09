"""Data loading module for Streamlit app."""

from __future__ import annotations

import io
from typing import Optional

import numpy as np
import pandas as pd
import streamlit as st

from app.services.demo_data import create_demo_data


@st.cache_data
def load_demo_data(
    n_cells: int, n_genes: int, n_clusters: int, seed: int
) -> pd.DataFrame:
    """Load demo dataset with specified parameters.

    Args:
        n_cells: Number of cells to generate
        n_genes: Number of genes to generate
        n_clusters: Number of clusters in the data
        seed: Random seed for reproducibility

    Returns:
        DataFrame with gene expression data (cells × genes)
    """
    return create_demo_data(
        n_cells=n_cells, n_genes=n_genes, n_clusters=n_clusters, seed=seed
    )


@st.cache_data
def load_uploaded_csv(uploaded_file) -> pd.DataFrame:
    """Load and validate uploaded CSV file.

    Expects a cells × genes expression matrix.
    Automatically detects and sets cell identifiers as index.

    Args:
        uploaded_file: Streamlit uploaded file object

    Returns:
        Numeric expression DataFrame with cells as rows

    Raises:
        ValueError: If file is empty or contains no numeric data
    """
    content = uploaded_file.getvalue()
    try:
        df = pd.read_csv(io.BytesIO(content), index_col=0)
    except Exception:
        df = pd.read_csv(io.BytesIO(content))
        if (
            df.shape[1] > 1
            and df.columns[0].lower() in ("cell", "cell_id", "id", "index")
        ):
            df = df.set_index(df.columns[0])

    if df.empty:
        raise ValueError("Uploaded file contains no data.")

    numeric = df.select_dtypes(include=[np.number])
    if numeric.shape[1] == 0:
        raise ValueError(
            "Uploaded dataset must contain numeric expression values."
        )

    return numeric.fillna(0)
