"""
Graph-based clustering on a k-NN graph (Leiden / Louvain).

This is the de-facto standard for scRNA-seq clustering. We build a
k-nearest-neighbour graph in PCA space, optionally weight edges by
distance, and run a community-detection algorithm.

Dependencies: python-igraph + leidenalg (Louvain falls back to igraph's
built-in `community_multilevel`).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import numpy as np
from sklearn.neighbors import kneighbors_graph


@dataclass
class GraphClusterResult:
    labels: np.ndarray
    n_clusters: int
    modularity: float
    method: str
    resolution: float
    distribution: dict

    def to_dict(self) -> dict:
        return {
            "labels": self.labels.tolist(),
            "n_clusters": int(self.n_clusters),
            "modularity": float(self.modularity),
            "method": self.method,
            "resolution": float(self.resolution),
            "distribution": {str(k): int(v) for k, v in self.distribution.items()},
        }


def _build_igraph(pca_components: np.ndarray, k: int):
    import igraph as ig
    n = pca_components.shape[0]
    k = max(2, min(k, n - 1))
    knn = kneighbors_graph(pca_components, n_neighbors=k,
                           mode="distance", include_self=False)
    knn = knn.maximum(knn.T)         # symmetric
    coo = knn.tocoo()
    # Edge weights: 1 / (1 + distance) so closer pairs have higher weight
    edges = list(zip(coo.row.tolist(), coo.col.tolist()))
    weights = (1.0 / (1.0 + coo.data)).tolist()
    g = ig.Graph(n=n, edges=edges, directed=False)
    g.es["weight"] = weights
    g.simplify(combine_edges={"weight": "mean"})
    return g


def cluster_graph(
    pca_components: np.ndarray,
    method: str = "leiden",
    k: int = 15,
    resolution: float = 1.0,
    seed: int = 0,
) -> GraphClusterResult:
    """Run Leiden (default) or Louvain on the k-NN graph."""
    method = method.lower()
    g = _build_igraph(pca_components, k=k)

    if method == "leiden":
        import leidenalg as la
        partition = la.find_partition(
            g, la.RBConfigurationVertexPartition,
            weights=g.es["weight"], resolution_parameter=resolution, seed=seed,
        )
    elif method == "louvain":
        # igraph's built-in multilevel ≈ Louvain
        partition = g.community_multilevel(weights="weight",
                                           resolution=resolution)
    else:
        raise ValueError(f"Unknown clustering method: {method}")

    labels = np.asarray(partition.membership, dtype=int)
    unique, counts = np.unique(labels, return_counts=True)
    try:
        modularity = float(g.modularity(partition.membership, weights="weight"))
    except Exception:
        modularity = 0.0

    return GraphClusterResult(
        labels=labels,
        n_clusters=int(len(unique)),
        modularity=modularity,
        method=method,
        resolution=resolution,
        distribution={int(u): int(c) for u, c in zip(unique, counts)},
    )
