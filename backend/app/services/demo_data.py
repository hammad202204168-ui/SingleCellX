"""
Synthetic demo data generator.

Produces a cells × genes negative-binomial expression matrix with a
controlled number of latent "ground truth" clusters. Each cluster
over-expresses a disjoint block of marker genes, so the pipeline can
recover meaningful structure for demonstrations.
"""
import numpy as np
import pandas as pd


def create_demo_data(
    n_cells: int = 600,
    n_genes: int = 2500,
    n_clusters: int = 6,
    seed: int = 42,
) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    cells_per_cluster = n_cells // n_clusters
    blocks = []
    cell_ids = []
    for c in range(n_clusters):
        block = rng.negative_binomial(5, 0.3, (cells_per_cluster, n_genes)).astype(float)
        # Upregulate this cluster's marker block 3x
        start = c * (n_genes // n_clusters)
        end = start + (n_genes // n_clusters)
        block[:, start:end] *= 3
        blocks.append(block)
        cell_ids.extend([f"Cell_C{c}_{i+1}" for i in range(cells_per_cluster)])
    matrix = np.vstack(blocks)
    gene_names = [f"Gene_{i+1}" for i in range(n_genes)]
    return pd.DataFrame(matrix, index=cell_ids, columns=gene_names)
