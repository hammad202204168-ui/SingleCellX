"""
Unsupervised clustering of cells.

K-means on the PCA-reduced representation. The number of clusters can be
supplied explicitly or chosen automatically using a simple elbow heuristic
on the within-cluster sum of squares (WCSS) curve.
"""
from dataclasses import dataclass
from typing import Optional
import numpy as np
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score


@dataclass
class ClusterResult:
    labels: np.ndarray
    n_clusters: int
    inertia: float
    silhouette: Optional[float]
    distribution: dict  # cluster_id -> count

    def to_dict(self) -> dict:
        return {
            "labels": self.labels.tolist(),
            "n_clusters": self.n_clusters,
            "inertia": float(self.inertia),
            "silhouette": None if self.silhouette is None else float(self.silhouette),
            "distribution": {str(k): int(v) for k, v in self.distribution.items()},
        }


def _find_optimal_k(pca: np.ndarray, max_k: int = 10) -> int:
    """Pick k using the discrete second derivative of the WCSS curve."""
    max_k = max(2, min(max_k, pca.shape[0] // 3))
    if max_k < 2:
        return 2
    inertias = []
    for k in range(2, max_k + 1):
        km = KMeans(n_clusters=k, random_state=42, n_init=10)
        km.fit(pca)
        inertias.append(km.inertia_)
    if len(inertias) > 2:
        delta = np.diff(inertias)
        delta2 = np.diff(delta)
        elbow = int(np.argmax(delta2)) + 2
        return min(elbow, max_k)
    return max(3, max_k // 2)


def cluster_cells(
    pca_components: np.ndarray,
    n_clusters: Optional[int] = None,
) -> ClusterResult:
    """K-means clustering with optional auto-k via elbow heuristic."""
    if pca_components.shape[0] < 4:
        raise ValueError("Need at least 4 cells to cluster.")

    if n_clusters is None:
        n_clusters = _find_optimal_k(pca_components)
    n_clusters = max(2, min(n_clusters, pca_components.shape[0] - 1))

    km = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
    labels = km.fit_predict(pca_components)

    # Silhouette is only meaningful when k>1 and we have enough samples
    sil = None
    try:
        if 2 <= n_clusters < pca_components.shape[0]:
            sil = float(silhouette_score(pca_components, labels, sample_size=min(2000, pca_components.shape[0])))
    except Exception:
        sil = None

    unique, counts = np.unique(labels, return_counts=True)
    distribution = {int(u): int(c) for u, c in zip(unique, counts)}

    return ClusterResult(
        labels=labels,
        n_clusters=n_clusters,
        inertia=float(km.inertia_),
        silhouette=sil,
        distribution=distribution,
    )
