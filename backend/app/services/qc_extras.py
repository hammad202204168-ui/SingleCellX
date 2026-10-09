"""
Advanced QC: mitochondrial/ribosomal content + doublet detection.

Both implementations are dependency-light (scikit-learn only) so they
fit alongside the rest of the project without bringing in heavy
external packages.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Tuple

import numpy as np
import pandas as pd
from sklearn.decomposition import PCA
from sklearn.neighbors import NearestNeighbors


# ---------------------------------------------------------------------------
# Mitochondrial / ribosomal content
# ---------------------------------------------------------------------------
MITO_PREFIXES = ("MT-", "MT.", "mt-", "mt.")
RIBO_PREFIXES = ("RPS", "RPL", "Rps", "Rpl")


def _mask(gene_names, prefixes) -> np.ndarray:
    g = np.asarray([str(x) for x in gene_names])
    return np.array([any(name.startswith(p) for p in prefixes) for name in g])


def per_cell_qc(counts: pd.DataFrame) -> pd.DataFrame:
    """Per-cell QC table: n_genes, n_counts, pct_mito, pct_ribo."""
    arr = counts.values.astype(float)
    n_counts = arr.sum(axis=1)
    n_genes = (arr > 0).sum(axis=1)

    mito_mask = _mask(counts.columns, MITO_PREFIXES)
    ribo_mask = _mask(counts.columns, RIBO_PREFIXES)

    pct_mito = (arr[:, mito_mask].sum(axis=1) / np.maximum(n_counts, 1)) * 100
    pct_ribo = (arr[:, ribo_mask].sum(axis=1) / np.maximum(n_counts, 1)) * 100

    return pd.DataFrame({
        "cell": counts.index,
        "n_genes": n_genes,
        "n_counts": n_counts,
        "pct_mito": pct_mito,
        "pct_ribo": pct_ribo,
    }).set_index("cell")


def filter_by_thresholds(
    counts: pd.DataFrame,
    max_pct_mito: float | None = 20.0,
    max_pct_ribo: float | None = None,
    min_counts: float | None = None,
    max_counts: float | None = None,
) -> Tuple[pd.DataFrame, pd.Series]:
    """Apply mito/ribo/count thresholds. Returns filtered counts + boolean keep mask."""
    qc = per_cell_qc(counts)
    keep = pd.Series(True, index=counts.index)
    if max_pct_mito is not None:
        keep &= qc["pct_mito"] <= max_pct_mito
    if max_pct_ribo is not None:
        keep &= qc["pct_ribo"] <= max_pct_ribo
    if min_counts is not None:
        keep &= qc["n_counts"] >= min_counts
    if max_counts is not None:
        keep &= qc["n_counts"] <= max_counts
    return counts.loc[keep], keep


# ---------------------------------------------------------------------------
# Scrublet-style doublet detection
# ---------------------------------------------------------------------------
@dataclass
class DoubletResult:
    scores: np.ndarray              # per-cell doublet score in [0, 1]
    predicted: np.ndarray           # boolean: True if classified as doublet
    threshold: float                # score cutoff applied
    expected_rate: float            # input expected doublet rate
    detected_rate: float            # fraction of cells actually flagged

    def to_dict(self) -> dict:
        return {
            "scores": self.scores.tolist(),
            "predicted": self.predicted.astype(int).tolist(),
            "threshold": float(self.threshold),
            "expected_rate": float(self.expected_rate),
            "detected_rate": float(self.detected_rate),
        }


def detect_doublets(
    normalized: pd.DataFrame,
    expected_rate: float = 0.06,
    sim_ratio: float = 2.0,
    k: int = 30,
    n_pcs: int = 30,
    seed: int = 0,
) -> DoubletResult:
    """Scrublet-style nearest-neighbour doublet score.

    Pipeline:
      1. Simulate `sim_ratio * n_cells` synthetic doublets by averaging
         pairs of random observed cells.
      2. PCA-embed the concatenated (real + simulated) matrix.
      3. For each real cell, look at its k-NN; doublet score = fraction
         that are simulated.
      4. Threshold = `expected_rate`-quantile of the score distribution.
    """
    n_cells = normalized.shape[0]
    if n_cells < 10:
        raise ValueError("Need at least 10 cells for doublet detection.")

    rng = np.random.default_rng(seed)
    n_sim = max(10, int(sim_ratio * n_cells))

    # Simulate doublets as the mean of two random cells (in normalized space)
    X = normalized.values
    pair_a = rng.integers(0, n_cells, n_sim)
    pair_b = rng.integers(0, n_cells, n_sim)
    sim = 0.5 * (X[pair_a] + X[pair_b])

    combined = np.vstack([X, sim])

    n_components = max(2, min(n_pcs, combined.shape[1] - 1,
                              combined.shape[0] - 1))
    pcs = PCA(n_components=n_components, random_state=seed).fit_transform(combined)

    k = max(5, min(k, combined.shape[0] - 1))
    nn = NearestNeighbors(n_neighbors=k + 1).fit(pcs)
    _, idx = nn.kneighbors(pcs[:n_cells])
    # idx[:, 0] is the cell itself
    neighbor_is_sim = idx[:, 1:] >= n_cells
    scores = neighbor_is_sim.mean(axis=1)

    # Threshold: keep the top `expected_rate` fraction as doublets, with a floor
    cutoff = float(np.quantile(scores, 1.0 - expected_rate)) if scores.size else 1.0
    cutoff = max(cutoff, 0.3)  # never call doublets at very low scores
    predicted = scores >= cutoff

    return DoubletResult(
        scores=scores,
        predicted=predicted,
        threshold=cutoff,
        expected_rate=expected_rate,
        detected_rate=float(predicted.mean()),
    )
