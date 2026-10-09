"""
Pairwise differential expression analysis.

For two user-selected clusters, compute per-gene statistics suitable for a
volcano plot:
  - log2 fold-change (mean expression A vs B)
  - Welch's t-test p-value
  - -log10 p-value (clipped)
  - Significance flag (|log2FC| > threshold AND adj. p < alpha)

Multiple-testing correction: simple Benjamini–Hochberg.
"""
from __future__ import annotations

from typing import Dict, List

import numpy as np
import pandas as pd
from scipy import stats


def _bh_adjust(p: np.ndarray) -> np.ndarray:
    """Benjamini–Hochberg FDR adjustment."""
    p = np.asarray(p, dtype=float)
    n = len(p)
    if n == 0:
        return p
    order = np.argsort(p)
    ranked = p[order] * n / (np.arange(n) + 1)
    # Enforce monotonicity from the largest p down
    ranked = np.minimum.accumulate(ranked[::-1])[::-1]
    adj = np.empty_like(p)
    adj[order] = np.clip(ranked, 0, 1)
    return adj


def pairwise_de(
    counts: pd.DataFrame,
    labels: np.ndarray,
    cluster_a: int,
    cluster_b: int,
    log_fc_threshold: float = 1.0,
    alpha: float = 0.05,
    max_genes: int = 5000,
) -> pd.DataFrame:
    """Compute DE table between two clusters.

    Returns a DataFrame with columns:
      gene, mean_a, mean_b, log2_fc, p_value, p_adj, neg_log10_p, significant
    """
    if cluster_a == cluster_b:
        raise ValueError("cluster_a and cluster_b must differ.")

    mask_a = labels == cluster_a
    mask_b = labels == cluster_b
    if mask_a.sum() < 2 or mask_b.sum() < 2:
        raise ValueError("Each cluster needs at least 2 cells.")

    genes = list(counts.columns[:max_genes])
    data_a = counts.loc[mask_a, genes].values
    data_b = counts.loc[mask_b, genes].values

    mean_a = data_a.mean(axis=0)
    mean_b = data_b.mean(axis=0)

    # log2 fold-change with pseudocount
    log2_fc = np.log2((mean_a + 1e-9) / (mean_b + 1e-9))

    # Welch's t-test vectorized — fall back to per-gene if variance is zero
    with np.errstate(invalid="ignore", divide="ignore"):
        _, p_values = stats.ttest_ind(data_a, data_b, axis=0, equal_var=False, nan_policy="omit")
    p_values = np.where(np.isfinite(p_values), p_values, 1.0)

    p_adj = _bh_adjust(p_values)
    neg_log10_p = -np.log10(np.clip(p_values, 1e-300, 1.0))

    significant = (np.abs(log2_fc) >= log_fc_threshold) & (p_adj < alpha)

    df = pd.DataFrame({
        "gene": genes,
        "mean_a": mean_a,
        "mean_b": mean_b,
        "log2_fc": log2_fc,
        "p_value": p_values,
        "p_adj": p_adj,
        "neg_log10_p": neg_log10_p,
        "significant": significant,
    })

    df = df.replace([np.inf, -np.inf], np.nan).dropna(subset=["log2_fc", "p_value"])
    return df.sort_values("p_adj").reset_index(drop=True)


def summarize_de(df: pd.DataFrame) -> Dict[str, int]:
    """Quick summary counts for a DE table."""
    if df.empty:
        return {"total": 0, "up": 0, "down": 0, "significant": 0}
    return {
        "total": int(len(df)),
        "up": int((df["significant"] & (df["log2_fc"] > 0)).sum()),
        "down": int((df["significant"] & (df["log2_fc"] < 0)).sum()),
        "significant": int(df["significant"].sum()),
    }
