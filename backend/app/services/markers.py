"""
Marker gene identification.

For every cluster we perform a one-vs-rest differential expression test
on each gene:
- log2 fold-change of mean(in-cluster) vs mean(out-cluster)
- Welch's t-test for significance
- Percent of cells in/out expressing the gene
- A simple monotonic trend label for visualization

Genes passing |log2FC| > 0.5 and p < 0.05 are reported, sorted by FC.
"""
from typing import Dict, List
import numpy as np
import pandas as pd
from scipy import stats


def find_markers(
    counts: pd.DataFrame,
    labels: np.ndarray,
    top_n: int = 15,
    log_fc_threshold: float = 0.5,
    p_value_threshold: float = 0.05,
) -> Dict[str, List[dict]]:
    """Compute top marker genes per cluster.

    Returns: dict mapping "Cluster_<i>" -> list of marker dicts.
    """
    if counts.shape[0] != len(labels):
        raise ValueError("Label vector length must match number of cells.")

    out: Dict[str, List[dict]] = {}
    unique_clusters = np.unique(labels)

    for cid in unique_clusters:
        in_mask = labels == cid
        out_mask = ~in_mask
        if in_mask.sum() < 2 or out_mask.sum() < 2:
            out[f"Cluster_{int(cid)}"] = []
            continue

        rows: List[dict] = []
        in_data = counts.loc[in_mask]
        out_data = counts.loc[out_mask]

        for gene in counts.columns:
            try:
                expr_in = in_data[gene].values
                expr_out = out_data[gene].values

                if expr_in.var() == 0 and expr_out.var() == 0:
                    continue

                mean_in = float(expr_in.mean())
                mean_out = max(float(expr_out.mean()), 1e-10)
                fc = mean_in / mean_out
                if not np.isfinite(fc) or fc <= 0:
                    continue
                log_fc = float(np.log2(fc))

                try:
                    _, p_value = stats.ttest_ind(expr_in, expr_out, equal_var=False)
                    p_value = float(p_value) if np.isfinite(p_value) else 1.0
                except Exception:
                    p_value = 1.0

                pct_in = float((expr_in > 0).sum() / len(expr_in) * 100)
                pct_out = float((expr_out > 0).sum() / len(expr_out) * 100)

                # Lightweight trend classifier
                trend = "stable"
                if expr_in.std() > 0:
                    sorted_expr = np.sort(expr_in)
                    corr = float(np.corrcoef(sorted_expr, np.arange(len(sorted_expr)))[0, 1])
                    if corr > 0.3:
                        trend = "increasing"
                    elif corr < -0.3:
                        trend = "decreasing"

                rows.append({
                    "gene": str(gene),
                    "log_fc": round(log_fc, 4),
                    "p_value": p_value,
                    "mean_in": round(mean_in, 4),
                    "mean_out": round(mean_out, 4),
                    "pct_in": round(pct_in, 2),
                    "pct_out": round(pct_out, 2),
                    "trend": trend,
                })
            except Exception:
                continue

        if rows:
            df = pd.DataFrame(rows)
            sig = df[(df["log_fc"] > log_fc_threshold) & (df["p_value"] < p_value_threshold)]
            sig = sig.sort_values("log_fc", ascending=False).head(top_n)
            out[f"Cluster_{int(cid)}"] = sig.to_dict(orient="records")
        else:
            out[f"Cluster_{int(cid)}"] = []

    return out
