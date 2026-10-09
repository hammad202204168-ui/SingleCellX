"""
AnnData (.h5ad) input / output helpers.

AnnData is the canonical container in modern scRNA-seq software
(scanpy, scvi-tools, CELLxGENE). Supporting it lets users drop in real
datasets without converting to CSV first.

We deliberately keep the surface small:
- `load_anndata`  : read .h5ad → cells×genes DataFrame
- `save_anndata`  : dump pipeline results back to .h5ad with the
  standard slots (obs, obsm, var, uns).
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional, Union

import numpy as np
import pandas as pd


def load_anndata(path_or_buffer) -> pd.DataFrame:
    """Load .h5ad and return cells×genes DataFrame.

    Accepts a path string or a file-like object (Streamlit upload).
    Densifies sparse matrices automatically.
    """
    import anndata as ad
    # anndata.read_h5ad works with both paths and file-like objects
    adata = ad.read_h5ad(path_or_buffer)
    X = adata.X
    if hasattr(X, "toarray"):
        X = X.toarray()
    cell_ids = list(adata.obs_names)
    gene_ids = list(adata.var_names)
    return pd.DataFrame(np.asarray(X), index=cell_ids, columns=gene_ids)


def save_anndata(
    path: Union[str, Path],
    counts: pd.DataFrame,
    obs: Optional[pd.DataFrame] = None,
    var: Optional[pd.DataFrame] = None,
    obsm: Optional[Dict[str, np.ndarray]] = None,
    uns: Optional[Dict[str, Any]] = None,
) -> str:
    """Write an AnnData bundle out.

    Parameters
    ----------
    path  : destination .h5ad
    counts: cells×genes matrix (rows = cells, cols = genes)
    obs   : per-cell metadata (cluster, cell_type, pct_mito, ...)
    var   : per-gene metadata
    obsm  : embeddings, e.g. {'X_pca': ..., 'X_umap': ...}
    uns   : unstructured (params, summary stats, ...)
    """
    import anndata as ad
    obs = obs if obs is not None else pd.DataFrame(index=counts.index)
    var = var if var is not None else pd.DataFrame(index=counts.columns)
    adata = ad.AnnData(
        X=counts.values.astype(np.float32),
        obs=obs.loc[counts.index],
        var=var.loc[counts.columns],
    )
    if obsm:
        for k, v in obsm.items():
            arr = np.asarray(v)
            if arr.shape[0] == adata.n_obs:
                adata.obsm[k] = arr
    if uns:
        for k, v in uns.items():
            try:
                adata.uns[k] = v
            except Exception:
                adata.uns[k] = str(v)
    adata.write_h5ad(str(path))
    return str(path)


def assemble_anndata_from_results(
    qc, pca=None, umap=None, tsne=None, clusters=None,
    annotation=None, cycle_phases=None, trajectory=None,
    params=None,
) -> "ad.AnnData":          # type: ignore[name-defined]
    """Build an AnnData object from the in-memory pipeline state.

    Mirrors what `save_anndata` writes but returns the object so
    callers (export module) can serialize it however they want.
    """
    import anndata as ad
    counts = qc["_counts"]
    obs = pd.DataFrame(index=counts.index)
    if clusters is not None:
        obs["cluster"] = np.asarray(clusters["_labels"]).astype(str)
    if cycle_phases is not None:
        obs["phase"] = np.asarray(cycle_phases)
    if trajectory is not None:
        obs["pseudotime"] = np.asarray(trajectory["_pseudotime"])
    if annotation is not None:
        mapping = dict(zip(annotation["cluster"].astype(int),
                           annotation["cell_type"]))
        if "cluster" in obs.columns:
            obs["cell_type"] = obs["cluster"].astype(int).map(mapping)

    adata = ad.AnnData(X=counts.values.astype(np.float32),
                       obs=obs, var=pd.DataFrame(index=counts.columns))
    if pca is not None:
        adata.obsm["X_pca"] = np.asarray(pca["_components"])
    if umap is not None:
        adata.obsm["X_umap"] = np.asarray(umap["_coords"])
    if tsne is not None:
        adata.obsm["X_tsne"] = np.asarray(tsne["_coords"])
    if params:
        adata.uns["params"] = dict(params)
    return adata
