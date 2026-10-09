"""
Quality control and normalization.

Implements the standard scRNA-seq preprocessing pipeline:
1. Cell filter: drop cells expressing fewer than `min_genes` genes.
2. Gene filter: drop genes detected in fewer than `min_cells` cells.
3. Library-size aware normalization: log1p of counts.
4. Z-score scaling across cells.

Returns a `QCResult` dataclass for downstream consumers.
"""
from dataclasses import dataclass
import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler


@dataclass
class QCResult:
    counts: pd.DataFrame              # filtered raw counts
    normalized: pd.DataFrame          # log1p + z-score scaled
    n_cells_in: int
    n_genes_in: int
    n_cells_out: int
    n_genes_out: int
    sparsity_pct: float
    median_genes_per_cell: float
    median_counts_per_cell: float

    def to_summary(self) -> dict:
        return {
            "cells_input": self.n_cells_in,
            "genes_input": self.n_genes_in,
            "cells_after_qc": self.n_cells_out,
            "genes_after_qc": self.n_genes_out,
            "cells_filtered": self.n_cells_in - self.n_cells_out,
            "genes_filtered": self.n_genes_in - self.n_genes_out,
            "sparsity_pct": round(self.sparsity_pct, 2),
            "median_genes_per_cell": round(self.median_genes_per_cell, 1),
            "median_counts_per_cell": round(self.median_counts_per_cell, 1),
        }


def run_qc(
    data: pd.DataFrame,
    min_genes_per_cell: int = 150,
    min_cells_per_gene: int = 3,
) -> QCResult:
    """Filter, normalize and scale a cells×genes expression matrix."""
    if data.empty:
        raise ValueError("Input matrix is empty.")
    if not np.issubdtype(data.values.dtype, np.number):
        raise ValueError("Input matrix must contain numeric values.")

    n_cells_in, n_genes_in = data.shape

    # Adaptive thresholds — never wipe the whole matrix
    min_genes_per_cell = min(min_genes_per_cell, max(1, data.shape[1] // 2))
    min_cells_per_gene = min(min_cells_per_gene, max(1, data.shape[0] // 10))

    # Cell filter
    genes_per_cell = (data > 0).sum(axis=1)
    cell_mask = genes_per_cell >= min_genes_per_cell
    if cell_mask.sum() == 0:
        cell_mask = genes_per_cell >= int(genes_per_cell.median())
    data = data.loc[cell_mask]

    # Gene filter
    cells_per_gene = (data > 0).sum(axis=0)
    gene_mask = cells_per_gene >= min_cells_per_gene
    if gene_mask.sum() == 0:
        gene_mask = cells_per_gene >= 1
    data = data.loc[:, gene_mask]

    if data.shape[0] < 5 or data.shape[1] < 5:
        raise ValueError(
            f"Insufficient data after QC ({data.shape[0]} cells × {data.shape[1]} genes). "
            f"Loosen min_genes_per_cell/min_cells_per_gene."
        )

    # Normalization: log1p then per-gene z-score
    log_counts = np.log1p(data)
    scaler = StandardScaler()
    normalized = pd.DataFrame(
        scaler.fit_transform(log_counts),
        index=data.index,
        columns=data.columns,
    )

    return QCResult(
        counts=data,
        normalized=normalized,
        n_cells_in=n_cells_in,
        n_genes_in=n_genes_in,
        n_cells_out=data.shape[0],
        n_genes_out=data.shape[1],
        sparsity_pct=float((data == 0).sum().sum() / data.size * 100),
        median_genes_per_cell=float((data > 0).sum(axis=1).median()),
        median_counts_per_cell=float(data.sum(axis=1).median()),
    )
