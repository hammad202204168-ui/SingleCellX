"""
Dimensionality reduction.

Three projections are produced for downstream visualization:
- PCA  : linear; used both as a denoising preprocessing step and for variance plots.
- UMAP : non-linear; preserves local + global structure (preferred for cell-type discovery).
- t-SNE: non-linear; preserves local structure (kept for compatibility/comparison).

Each function takes the normalized matrix and returns a small dataclass with
the embedding and the metadata needed to render it.
"""
from dataclasses import dataclass
import numpy as np
import pandas as pd
from sklearn.decomposition import PCA
from sklearn.manifold import TSNE

try:
    import umap
    UMAP_AVAILABLE = True
except ImportError:  # pragma: no cover — graceful fallback
    UMAP_AVAILABLE = False


@dataclass
class PCAResult:
    components: np.ndarray            # shape (n_cells, n_components)
    variance_ratio: np.ndarray
    cumulative_variance: np.ndarray
    n_components: int

    def to_dict(self) -> dict:
        return {
            "n_components": self.n_components,
            "variance_ratio": self.variance_ratio.tolist(),
            "cumulative_variance": self.cumulative_variance.tolist(),
            # Only ship the first two components to the frontend by default
            "embedding_2d": self.components[:, :2].tolist(),
            # Include full components for 3D visualization
            "components": self.components.tolist(),
        }


@dataclass
class EmbeddingResult:
    method: str
    coords: np.ndarray   # shape (n_cells, 2)

    def to_dict(self) -> dict:
        return {"method": self.method, "coords": self.coords.tolist()}


def run_pca(normalized: pd.DataFrame, n_components: int = 50) -> PCAResult:
    """Linear PCA on the normalized matrix."""
    max_comp = min(n_components, normalized.shape[0] - 1, normalized.shape[1])
    if max_comp < 2:
        raise ValueError("Not enough samples for PCA.")
    pca = PCA(n_components=max_comp, random_state=42)
    comps = pca.fit_transform(normalized)
    return PCAResult(
        components=comps,
        variance_ratio=pca.explained_variance_ratio_,
        cumulative_variance=np.cumsum(pca.explained_variance_ratio_),
        n_components=max_comp,
    )


def run_umap(
    pca_components: np.ndarray,
    n_neighbors: int = 15,
    min_dist: float = 0.1,
) -> EmbeddingResult:
    """UMAP projection on the top PCs; falls back to t-SNE if umap-learn is missing."""
    inp = pca_components[:, : min(30, pca_components.shape[1])]
    n_samples = inp.shape[0]
    n_neighbors = max(2, min(n_neighbors, n_samples - 1))

    if UMAP_AVAILABLE:
        reducer = umap.UMAP(
            n_components=2,
            n_neighbors=n_neighbors,
            min_dist=min_dist,
            metric="euclidean",
            random_state=42,
        )
        coords = reducer.fit_transform(inp)
    else:
        # Fallback so the platform never crashes if optional dep is absent
        perp = max(5, min(30, n_samples // 3))
        coords = TSNE(n_components=2, perplexity=perp, random_state=42).fit_transform(inp)

    return EmbeddingResult(method="UMAP" if UMAP_AVAILABLE else "UMAP(t-SNE fallback)", coords=coords)


def run_tsne(pca_components: np.ndarray, perplexity: int = 30) -> EmbeddingResult:
    """t-SNE projection with adaptive perplexity."""
    inp = pca_components[:, : min(30, pca_components.shape[1])]
    max_perp = max(5, (inp.shape[0] - 1) // 3)
    perplexity = min(perplexity, max_perp)
    coords = TSNE(n_components=2, perplexity=perplexity, random_state=42).fit_transform(inp)
    return EmbeddingResult(method="t-SNE", coords=coords)
