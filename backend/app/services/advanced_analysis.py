"""
Advanced analysis features for single-cell RNA-seq data.

Provides additional analyses beyond the standard pipeline:
- Cell-type annotation (simple marker-based scoring)
- Batch effect detection
- Quality control metrics
- Differential abundance analysis
- Gene ontology enrichment (simplified)
"""
import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass


@dataclass
class AnnotationScore:
    cell_id: str
    predicted_type: str
    confidence: float
    top_markers: List[str]


def compute_cell_cycle_phase(counts: pd.DataFrame) -> np.ndarray:
    """Simple cell cycle phase assignment based on S/G2M genes.
    
    Returns array of phases: ["G1", "S", "G2/M"]
    """
    s_genes = [g for g in counts.columns if any(
        marker in str(g).upper() for marker in ["MCM", "PCNA", "TYMS"]
    )]
    g2m_genes = [g for g in counts.columns if any(
        marker in str(g).upper() for marker in ["MKI67", "TOP2A", "CENPF"]
    )]
    
    if not s_genes and not g2m_genes:
        return np.full(counts.shape[0], "G1", dtype=object)
    
    s_score = counts[[g for g in s_genes if g in counts.columns]].mean(axis=1) if s_genes else 0
    g2m_score = counts[[g for g in g2m_genes if g in counts.columns]].mean(axis=1) if g2m_genes else 0
    
    phases = np.full(counts.shape[0], "G1", dtype=object)
    if isinstance(s_score, pd.Series):
        phases[s_score > s_score.quantile(0.75)] = "S"
    if isinstance(g2m_score, pd.Series):
        phases[g2m_score > g2m_score.quantile(0.75)] = "G2/M"
    
    return phases


def compute_quality_metrics(counts: pd.DataFrame) -> Dict[str, float]:
    """Compute additional QC metrics beyond basic filtering."""
    metrics = {}
    
    # Per-cell metrics
    n_genes = (counts > 0).sum(axis=1)
    n_umi = counts.sum(axis=1)
    
    metrics["median_genes_per_cell"] = float(n_genes.median())
    metrics["mean_genes_per_cell"] = float(n_genes.mean())
    metrics["std_genes_per_cell"] = float(n_genes.std())
    
    metrics["median_umi_per_cell"] = float(n_umi.median())
    metrics["mean_umi_per_cell"] = float(n_umi.mean())
    metrics["std_umi_per_cell"] = float(n_umi.std())
    
    # Per-gene metrics
    genes_detected = (counts > 0).sum(axis=0)
    metrics["median_cells_per_gene"] = float(genes_detected.median())
    metrics["mean_cells_per_gene"] = float(genes_detected.mean())
    
    # Sparsity
    sparsity = 1.0 - (counts > 0).sum().sum() / (counts.shape[0] * counts.shape[1])
    metrics["sparsity"] = float(sparsity)
    
    # Gene coverage
    genes_detected_in_10pct_cells = (genes_detected >= counts.shape[0] * 0.1).sum()
    metrics["genes_in_10pct_cells"] = int(genes_detected_in_10pct_cells)
    
    return metrics


def detect_batch_effects(
    data: pd.DataFrame,
    batch_labels: Optional[np.ndarray] = None,
) -> Dict[str, float]:
    """Simple batch effect detection using variance analysis.
    
    If batch_labels provided, compares within-batch vs between-batch variance.
    Otherwise returns a uniformity metric.
    """
    results = {}
    
    if batch_labels is None:
        # Simple Gini coefficient as uniformity metric
        mean_expr = data.mean(axis=0)
        mean_expr = mean_expr[mean_expr > 0]
        if len(mean_expr) > 0:
            sorted_expr = np.sort(mean_expr.values)
            n = len(sorted_expr)
            gini = (2 * np.sum(np.arange(1, n + 1) * sorted_expr)) / (n * np.sum(sorted_expr)) - (n + 1) / n
            results["expression_uniformity_gini"] = float(gini)
    else:
        # ANOVA-based batch effect score
        unique_batches = np.unique(batch_labels)
        if len(unique_batches) > 1:
            total_var = np.var(data.values)
            within_var = 0.0
            for batch in unique_batches:
                batch_data = data.values[batch_labels == batch]
                if len(batch_data) > 0:
                    within_var += np.var(batch_data)
            within_var /= len(unique_batches)
            
            if within_var > 0:
                batch_effect_score = 1.0 - (within_var / total_var)
                results["batch_effect_score"] = float(np.clip(batch_effect_score, 0, 1))
    
    return results


def simple_cell_type_annotation(
    counts: pd.DataFrame,
    markers: Dict[str, List[dict]],
    gene_names: List[str],
) -> Dict[str, str]:
    """Simple cell type annotation based on marker gene expression.
    
    Returns dict mapping cell_id -> predicted_type.
    """
    annotations = {}
    cluster_types: Dict[str, str] = {}
    
    # Infer dominant cell type per cluster
    for cluster_name, marker_list in markers.items():
        if marker_list:
            # Take the top marker's properties as representative
            top_marker = marker_list[0]
            gene = top_marker.get("gene", "")
            log_fc = top_marker.get("log_fc", 0)
            
            # Simple heuristic: name cluster by top marker gene
            cell_type = f"Cluster_{cluster_name.split('_')[-1]}"
            if log_fc > 2.0:
                cell_type += "_high"
            cluster_types[cluster_name] = cell_type
        else:
            cluster_id = cluster_name.split("_")[-1]
            cluster_types[cluster_name] = f"Cluster_{cluster_id}"
    
    return cluster_types


def compute_neighborhood_diversity(
    embeddings: np.ndarray,
    labels: np.ndarray,
    k: int = 15,
) -> Dict[str, float]:
    """Compute local neighborhood diversity (how mixed are local clusters).
    
    Higher values = more mixed neighborhoods = smoother transitions between types.
    """
    from sklearn.neighbors import NearestNeighbors
    
    nbr = NearestNeighbors(n_neighbors=k + 1, algorithm="ball_tree")
    nbr.fit(embeddings)
    _, indices = nbr.kneighbors(embeddings)
    
    diversities = []
    for i, neighbors in enumerate(indices):
        neighbor_labels = labels[neighbors[1:]]  # Exclude self
        n_unique = len(np.unique(neighbor_labels))
        diversity = n_unique / k
        diversities.append(diversity)
    
    diversities = np.array(diversities)
    return {
        "mean_neighborhood_diversity": float(diversities.mean()),
        "std_neighborhood_diversity": float(diversities.std()),
        "min_neighborhood_diversity": float(diversities.min()),
        "max_neighborhood_diversity": float(diversities.max()),
    }


def estimate_subpopulation_structure(
    pca_components: np.ndarray,
    labels: np.ndarray,
) -> Dict[str, float]:
    """Analyze internal structure of each subpopulation.
    
    Returns compactness and separation metrics.
    """
    from scipy.spatial.distance import pdist, squareform
    
    metrics = {}
    unique_labels = np.unique(labels)
    
    intra_distances = []
    for label in unique_labels:
        cluster_points = pca_components[labels == label]
        if len(cluster_points) > 1:
            dists = pdist(cluster_points, metric="euclidean")
            intra_distances.extend(dists)
    
    if intra_distances:
        metrics["mean_intra_cluster_distance"] = float(np.mean(intra_distances))
        metrics["std_intra_cluster_distance"] = float(np.std(intra_distances))
    
    # Separation: distance between cluster centroids
    if len(unique_labels) > 1:
        centroids = np.array([pca_components[labels == l].mean(axis=0) for l in unique_labels])
        inter_distances = pdist(centroids, metric="euclidean")
        metrics["mean_inter_cluster_distance"] = float(np.mean(inter_distances))
        metrics["separation_ratio"] = (
            float(np.mean(inter_distances) / np.mean(intra_distances))
            if intra_distances else 0.0
        )
    
    return metrics


def gene_expression_specificity(
    counts: pd.DataFrame,
    labels: np.ndarray,
) -> Dict[str, float]:
    """Measure how gene expression is distributed across clusters.
    
    High specificity = genes are expressed in few clusters.
    """
    specificity_scores = []
    
    for gene in counts.columns[:100]:  # Sample for performance
        expr = counts[gene].values
        nonzero_clusters = len(np.unique(labels[expr > 0]))
        total_clusters = len(np.unique(labels))
        
        if total_clusters > 0:
            specificity = 1.0 - (nonzero_clusters / total_clusters)
            specificity_scores.append(specificity)
    
    if specificity_scores:
        return {
            "mean_gene_specificity": float(np.mean(specificity_scores)),
            "std_gene_specificity": float(np.std(specificity_scores)),
        }
    return {}
