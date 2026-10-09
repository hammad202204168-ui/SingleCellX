"""
Trajectory inference & pseudotime ordering.

A lightweight, dependency-free implementation that approximates diffusion
pseudotime:
  1. Build a k-NN graph in PCA space.
  2. Compute shortest-path (geodesic) distances from a root cell.
  3. Rank cells by distance => pseudotime in [0, 1].

The root cell is chosen automatically as the cell with the most extreme
projection on PC1 (a reasonable default for monotonic processes), or it
can be supplied explicitly.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import numpy as np
from scipy.sparse import csr_matrix
from scipy.sparse.csgraph import shortest_path
from sklearn.neighbors import kneighbors_graph


@dataclass
class TrajectoryResult:
    pseudotime: np.ndarray          # shape (n_cells,), values in [0, 1]
    root_index: int
    knn_graph_density: float
    branch_count: int               # rough estimate via connected components of pruned graph

    def to_dict(self) -> dict:
        return {
            "pseudotime": self.pseudotime.tolist(),
            "root_index": int(self.root_index),
            "knn_graph_density": float(self.knn_graph_density),
            "branch_count": int(self.branch_count),
        }


def infer_pseudotime(
    pca_components: np.ndarray,
    k: int = 15,
    root_index: Optional[int] = None,
) -> TrajectoryResult:
    """Compute pseudotime ordering for each cell."""
    n = pca_components.shape[0]
    if n < 5:
        raise ValueError("Need at least 5 cells for trajectory inference.")
    k = max(2, min(k, n - 1))

    # k-NN graph on top PCs
    inp = pca_components[:, : min(20, pca_components.shape[1])]
    graph = kneighbors_graph(inp, n_neighbors=k, mode="distance", include_self=False)

    # Symmetrize so geodesic distances are well-defined
    graph = graph.maximum(graph.T)

    # Pick root: extreme on PC1 unless user supplies
    if root_index is None:
        root_index = int(np.argmin(inp[:, 0]))
    root_index = int(np.clip(root_index, 0, n - 1))

    # Geodesic distances from root
    dist = shortest_path(csgraph=csr_matrix(graph), directed=False, indices=root_index)

    # Replace unreachable cells with the max finite distance (graph is usually connected)
    finite = dist[np.isfinite(dist)]
    if finite.size == 0:
        # Degenerate fallback — Euclidean from root
        dist = np.linalg.norm(inp - inp[root_index], axis=1)
    else:
        dist = np.where(np.isfinite(dist), dist, finite.max())

    # Normalize to [0, 1]
    rng = dist.max() - dist.min()
    pseudotime = (dist - dist.min()) / rng if rng > 0 else np.zeros(n)

    # Branch estimate: count connected components after dropping long edges
    long_edge_thresh = np.percentile(graph.data, 90) if graph.nnz else np.inf
    pruned = graph.copy()
    pruned.data[pruned.data > long_edge_thresh] = 0
    pruned.eliminate_zeros()
    from scipy.sparse.csgraph import connected_components
    n_comp, _ = connected_components(pruned, directed=False)

    density = float(graph.nnz / (n * (n - 1)))

    return TrajectoryResult(
        pseudotime=pseudotime,
        root_index=root_index,
        knn_graph_density=density,
        branch_count=int(n_comp),
    )
