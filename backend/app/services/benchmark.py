"""
Clustering benchmark utilities.

Given a labeled dataset (cells with known cell-type or ground-truth
cluster), evaluate the pipeline's predicted clusters with:

- ARI  : Adjusted Rand Index — corrected-for-chance agreement.
- NMI  : Normalized Mutual Information — information overlap.
- FMI  : Fowlkes–Mallows Index — geometric mean of precision & recall.
- Silhouette : intrinsic cluster quality on the embedding.
- Per-cluster purity : dominant true label fraction per predicted cluster.

The demo dataset has obvious ground truth (`Cell_C<k>_<i>` ids), so the
benchmark module can self-test out of the box.
"""
from __future__ import annotations

from typing import Dict, List

import numpy as np
import pandas as pd
from sklearn.metrics import (adjusted_rand_score, normalized_mutual_info_score,
                             fowlkes_mallows_score, silhouette_score,
                             confusion_matrix)


def extract_demo_ground_truth(cell_ids) -> np.ndarray | None:
    """Demo cell ids look like 'Cell_C2_17' — extract the cluster index.

    Returns None if the naming doesn't match.
    """
    out = []
    for cid in cell_ids:
        s = str(cid)
        if s.startswith("Cell_C") and "_" in s[6:]:
            try:
                out.append(int(s[6:].split("_", 1)[0]))
            except Exception:
                return None
        else:
            return None
    return np.asarray(out, dtype=int)


def benchmark_clusters(
    pred_labels: np.ndarray,
    true_labels: np.ndarray,
    embedding: np.ndarray | None = None,
) -> Dict[str, float]:
    """Return ARI / NMI / FMI / (optionally) silhouette."""
    out = {
        "ari": float(adjusted_rand_score(true_labels, pred_labels)),
        "nmi": float(normalized_mutual_info_score(true_labels, pred_labels)),
        "fmi": float(fowlkes_mallows_score(true_labels, pred_labels)),
        "n_pred": int(len(np.unique(pred_labels))),
        "n_true": int(len(np.unique(true_labels))),
    }
    if embedding is not None and len(np.unique(pred_labels)) > 1:
        try:
            out["silhouette"] = float(silhouette_score(
                embedding, pred_labels,
                sample_size=min(2000, len(pred_labels)),
            ))
        except Exception:
            pass
    return out


def purity_table(pred_labels: np.ndarray, true_labels: np.ndarray) -> pd.DataFrame:
    """For each predicted cluster, report dominant true label & purity."""
    cm = confusion_matrix(true_labels, pred_labels)
    rows: List[dict] = []
    pred_ids = sorted(np.unique(pred_labels))
    true_ids = sorted(np.unique(true_labels))
    for j, pid in enumerate(pred_ids):
        col = cm[:, j]
        total = int(col.sum())
        if total == 0:
            continue
        dom_idx = int(col.argmax())
        rows.append({
            "predicted_cluster": int(pid),
            "size": total,
            "dominant_true_label": int(true_ids[dom_idx]),
            "purity": round(float(col[dom_idx] / total), 3),
        })
    return pd.DataFrame(rows)


def compare_methods(results: Dict[str, np.ndarray],
                    true_labels: np.ndarray,
                    embedding: np.ndarray | None = None) -> pd.DataFrame:
    """Run benchmark_clusters for every (method_name -> labels) pair."""
    rows = []
    for name, labels in results.items():
        metrics = benchmark_clusters(np.asarray(labels), true_labels, embedding)
        rows.append({"method": name, **metrics})
    return pd.DataFrame(rows).sort_values("ari", ascending=False).reset_index(drop=True)
