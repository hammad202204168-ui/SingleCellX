"""
Export utilities for analysis results.

Provides functions to export analysis results in multiple formats:
- CSV tables (QC summary, markers, cluster assignments)
- HDF5 (for large-scale data storage)
- JSON (complete results with metadata)
- TSV (tab-separated values for compatibility)
"""
import json
import csv
import io
from pathlib import Path
from typing import BinaryIO, Optional, Dict, Any
import pandas as pd
import numpy as np


def export_markers_csv(markers: Dict[str, list], output: BinaryIO) -> None:
    """Export marker genes as a CSV file (one cluster per row group).
    
    Format:
    Cluster,Gene,Log2FC,P_Value,PctIn,PctOut,MeanIn,MeanOut,Trend
    """
    rows = []
    for cluster_name, marker_list in markers.items():
        for marker in marker_list:
            rows.append({
                "Cluster": cluster_name,
                "Gene": marker.get("gene", ""),
                "Log2FC": marker.get("log_fc", 0),
                "P_Value": marker.get("p_value", 1.0),
                "PctIn": marker.get("pct_in", 0),
                "PctOut": marker.get("pct_out", 0),
                "MeanIn": marker.get("mean_in", 0),
                "MeanOut": marker.get("mean_out", 0),
                "Trend": marker.get("trend", ""),
            })
    
    if rows:
        df = pd.DataFrame(rows)
        df.to_csv(output, index=False)
    else:
        output.write(b"")


def export_embeddings_csv(
    embedding_name: str,
    coords: list,
    cell_ids: list,
    clusters: Optional[list] = None,
    output: Optional[BinaryIO] = None,
) -> str:
    """Export embedding coordinates as CSV.
    
    Format:
    CellID,Dim1,Dim2[,Cluster]
    """
    if output is None:
        output = io.BytesIO()
    
    rows = []
    for i, (x, y) in enumerate(coords):
        row = {
            "CellID": cell_ids[i] if i < len(cell_ids) else f"Cell_{i}",
            f"{embedding_name}_1": x,
            f"{embedding_name}_2": y,
        }
        if clusters is not None and i < len(clusters):
            row["Cluster"] = int(clusters[i])
        rows.append(row)
    
    df = pd.DataFrame(rows)
    df.to_csv(output, index=False)
    return output.getvalue().decode() if isinstance(output, io.BytesIO) else ""


def export_pca_variance_csv(
    variance_ratio: list,
    cumulative_variance: list,
    output: Optional[BinaryIO] = None,
) -> str:
    """Export PCA variance explained per component.
    
    Format:
    Component,VarianceRatio,CumulativeVariance
    """
    if output is None:
        output = io.BytesIO()
    
    rows = [
        {
            "Component": i + 1,
            "VarianceRatio": v,
            "CumulativeVariance": c,
        }
        for i, (v, c) in enumerate(zip(variance_ratio, cumulative_variance))
    ]
    
    df = pd.DataFrame(rows)
    df.to_csv(output, index=False)
    return output.getvalue().decode() if isinstance(output, io.BytesIO) else ""


def export_cluster_summary_csv(
    clusters: Dict[str, Any],
    cell_ids: list,
    output: BinaryIO,
) -> None:
    """Export per-cluster summary statistics.
    
    Format:
    Cluster,CellCount,PercentOfTotal
    """
    distribution = clusters.get("distribution", {})
    total_cells = sum(distribution.values())
    
    rows = [
        {
            "Cluster": cluster_id,
            "CellCount": count,
            "PercentOfTotal": round(count / total_cells * 100, 2) if total_cells > 0 else 0,
        }
        for cluster_id, count in sorted(distribution.items())
    ]
    
    if rows:
        df = pd.DataFrame(rows)
        df.to_csv(output, index=False)
    else:
        output.write(b"")


def export_qc_summary_csv(qc_summary: Dict[str, Any], output: BinaryIO) -> None:
    """Export QC summary as a simple key-value CSV."""
    rows = [
        {"Metric": k, "Value": v}
        for k, v in qc_summary.items()
    ]
    df = pd.DataFrame(rows)
    df.to_csv(output, index=False)


def export_cell_assignments_csv(
    cell_ids: list,
    cluster_labels: list,
    output: BinaryIO,
) -> None:
    """Export cell cluster assignments (CellID, Cluster).
    
    Useful for importing into other tools like Seurat.
    """
    rows = [
        {"CellID": cid, "Cluster": int(c)}
        for cid, c in zip(cell_ids, cluster_labels)
    ]
    df = pd.DataFrame(rows)
    df.to_csv(output, index=False)


def create_export_summary_json(
    run_id: int,
    run_name: str,
    results: Dict[str, Any],
    n_cells: int,
    n_genes: int,
) -> Dict[str, Any]:
    """Create a comprehensive export summary with metadata."""
    return {
        "export_metadata": {
            "run_id": run_id,
            "run_name": run_name,
            "export_timestamp": pd.Timestamp.utcnow().isoformat(),
            "data_shape": {
                "cells": n_cells,
                "genes": n_genes,
            },
        },
        "analysis_results": results,
    }


class ExportPackage:
    """Creates a downloadable archive of analysis results."""
    
    def __init__(self, run_id: int, run_name: str):
        self.run_id = run_id
        self.run_name = run_name
        self.files: Dict[str, bytes] = {}
    
    def add_csv(self, name: str, content: bytes):
        """Add a CSV file to the package."""
        self.files[f"{name}.csv"] = content
    
    def add_json(self, name: str, data: Dict):
        """Add a JSON file to the package."""
        content = json.dumps(data, indent=2, default=str).encode()
        self.files[f"{name}.json"] = content
    
    def add_text(self, name: str, content: str):
        """Add a text file to the package."""
        self.files[f"{name}.txt"] = content.encode()
    
    def get_files(self) -> Dict[str, bytes]:
        """Get all files in the package."""
        return self.files.copy()
    
    def get_manifest(self) -> Dict[str, Any]:
        """Get a manifest of exported files."""
        return {
            "run_id": self.run_id,
            "run_name": self.run_name,
            "files": list(self.files.keys()),
            "file_count": len(self.files),
            "total_size_bytes": sum(len(v) for v in self.files.values()),
        }
