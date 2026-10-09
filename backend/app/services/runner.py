"""
Analysis orchestrator.

Runs the complete scRNA-seq pipeline asynchronously, persisting state
to the database after every step so the frontend can poll progress.
The output is also serialized to disk as a JSON blob for retrieval.

Features:
- Asynchronous execution with progress tracking
- Comprehensive error handling and recovery
- Advanced analysis metrics (batch effects, cell cycle, neighborhood diversity)
- Result caching for performance optimization
- Audit logging for all steps
"""
import json
import traceback
import logging
from datetime import datetime
from pathlib import Path
import numpy as np
import pandas as pd
from sqlalchemy.orm import Session

from ..config import settings
from ..database import SessionLocal
from ..models import AnalysisRun, LogEntry
from .preprocessing import run_qc
from .dimensionality import run_pca, run_umap, run_tsne
from .clustering import cluster_cells
from .markers import find_markers
from .advanced_analysis import (
    compute_quality_metrics,
    detect_batch_effects,
    compute_neighborhood_diversity,
    estimate_subpopulation_structure,
    gene_expression_specificity,
    compute_cell_cycle_phase,
)
from .cache import get_cache

# Configure logging
logger = logging.getLogger(__name__)


# ============================================================
# Logging helpers
# ============================================================
def _log(db: Session, run_id: int, message: str, level: str = "info") -> None:
    """Append a log line to the run's audit trail."""
    db.add(LogEntry(run_id=run_id, message=message, level=level))
    db.commit()


def _update(db: Session, run_id: int, **kwargs) -> None:
    """Patch fields on the run row."""
    run = db.query(AnalysisRun).filter(AnalysisRun.id == run_id).first()
    if run is None:
        return
    for k, v in kwargs.items():
        setattr(run, k, v)
    db.commit()


# ============================================================
# Main pipeline
# ============================================================
def execute_analysis(run_id: int) -> None:
    """Run a single analysis end-to-end. Designed to be called as a BackgroundTask.
    
    Includes standard pipeline steps plus advanced metrics:
    - Data loading & validation
    - Quality control & normalization
    - Dimensionality reduction (PCA)
    - Non-linear embeddings (UMAP, t-SNE)
    - Clustering
    - Marker gene discovery
    - Advanced metrics (QC, batch effects, neighborhood diversity, cell cycle)
    """
    db: Session = SessionLocal()
    run = None
    try:
        run = db.query(AnalysisRun).filter(AnalysisRun.id == run_id).first()
        if run is None:
            logger.error(f"Run {run_id} not found")
            return

        params = run.parameters or {}
        dataset = run.dataset
        file_path = Path(dataset.file_path)
        
        if not file_path.exists():
            raise FileNotFoundError(f"Dataset file not found: {file_path}")

        # --- Start ---
        _update(db, run_id, status="running", progress=2, current_step="Loading data")
        _log(db, run_id, f"Loading dataset: {dataset.filename}")
        
        try:
            data = pd.read_csv(file_path, index_col=0)
        except Exception as e:
            raise ValueError(f"Failed to parse CSV file: {e}")
        
        data = data.fillna(0).select_dtypes(include=[np.number])
        
        if data.empty:
            raise ValueError("Data matrix is empty after parsing")
        
        _log(db, run_id, f"✓ Loaded matrix: {data.shape[0]} cells × {data.shape[1]} genes")

        # --- QC ---
        _update(db, run_id, progress=15, current_step="Quality control & normalization")
        _log(db, run_id, "Running quality control...")
        
        try:
            qc = run_qc(
                data,
                min_genes_per_cell=int(params.get("min_genes_per_cell", 150)),
                min_cells_per_gene=int(params.get("min_cells_per_gene", 3)),
            )
        except ValueError as e:
            raise ValueError(f"QC failed: {e}")
        
        qc_summary = qc.to_summary()
        
        # Add advanced QC metrics
        advanced_qc = compute_quality_metrics(qc.counts)
        qc_summary.update(advanced_qc)
        
        filtered_pct = (1 - qc.n_cells_out / qc.n_cells_in) * 100
        _log(db, run_id, f"✓ QC complete: {qc.n_cells_out}/{qc.n_cells_in} cells ({filtered_pct:.1f}% filtered)")
        _log(db, run_id, f"  Genes after filtering: {qc.n_genes_out}/{qc.n_genes_in}")

        # --- PCA ---
        _update(db, run_id, progress=35, current_step="PCA decomposition")
        _log(db, run_id, "Computing PCA...")
        
        try:
            pca = run_pca(qc.normalized, n_components=int(params.get("n_pca_components", 50)))
        except ValueError as e:
            raise ValueError(f"PCA failed: {e}")
        
        var_total = float(pca.cumulative_variance[-1] * 100)
        var_50 = float(pca.cumulative_variance[min(49, len(pca.cumulative_variance)-1)] * 100)
        _log(db, run_id, f"✓ PCA: {pca.n_components} components, {var_total:.1f}% total variance")
        _log(db, run_id, f"  Variance explained (first 50 PCs): {var_50:.1f}%")

        # --- UMAP ---
        _update(db, run_id, progress=55, current_step="UMAP projection")
        _log(db, run_id, "Computing UMAP embedding...")
        
        try:
            umap_res = run_umap(
                pca.components,
                n_neighbors=int(params.get("umap_n_neighbors", 15)),
                min_dist=float(params.get("umap_min_dist", 0.1)),
            )
        except Exception as e:
            _log(db, run_id, f"⚠ UMAP failed, continuing without UMAP", level="warn")
            umap_res = None
        else:
            _log(db, run_id, f"✓ UMAP projection complete ({umap_res.method})")

        # --- t-SNE ---
        _update(db, run_id, progress=70, current_step="t-SNE projection")
        _log(db, run_id, "Computing t-SNE embedding...")
        
        try:
            tsne_res = run_tsne(pca.components, perplexity=int(params.get("tsne_perplexity", 30)))
        except Exception as e:
            _log(db, run_id, f"⚠ t-SNE failed: {e}", level="warn")
            tsne_res = None
        else:
            _log(db, run_id, "✓ t-SNE projection complete")

        # --- Clustering ---
        _update(db, run_id, progress=82, current_step="Clustering")
        _log(db, run_id, "Performing clustering...")
        
        try:
            n_clusters_req = params.get("n_clusters")
            n_clusters_req = int(n_clusters_req) if n_clusters_req else None
            clusters = cluster_cells(pca.components, n_clusters=n_clusters_req)
        except ValueError as e:
            raise ValueError(f"Clustering failed: {e}")
        
        sil_str = f"silhouette={clusters.silhouette:.3f}" if clusters.silhouette else "silhouette=N/A"
        _log(db, run_id, f"✓ Clustering: {clusters.n_clusters} clusters ({sil_str})")

        # --- Markers ---
        _update(db, run_id, progress=92, current_step="Marker gene identification")
        _log(db, run_id, "Finding marker genes...")
        
        try:
            markers = find_markers(qc.counts, clusters.labels, top_n=int(params.get("n_marker_genes", 15)))
        except Exception as e:
            raise ValueError(f"Marker detection failed: {e}")
        
        n_marker_total = sum(len(v) for v in markers.values())
        _log(db, run_id, f"✓ Found {n_marker_total} marker genes across {clusters.n_clusters} clusters")

        # --- Advanced Analysis ---
        _update(db, run_id, progress=95, current_step="Advanced analysis")
        _log(db, run_id, "Computing advanced metrics...")
        
        advanced_metrics = {}
        
        try:
            # Batch effect detection
            batch_metrics = detect_batch_effects(qc.normalized)
            advanced_metrics["batch_effects"] = batch_metrics
            _log(db, run_id, f"✓ Batch effect analysis complete")
        except Exception as e:
            _log(db, run_id, f"⚠ Batch effect analysis failed: {e}", level="warn")
        
        try:
            # Neighborhood diversity
            if umap_res is not None:
                neighborhood = compute_neighborhood_diversity(umap_res.coords, clusters.labels)
                advanced_metrics["neighborhood_diversity"] = neighborhood
                _log(db, run_id, f"✓ Neighborhood diversity computed")
        except Exception as e:
            _log(db, run_id, f"⚠ Neighborhood analysis failed: {e}", level="warn")
        
        try:
            # Subpopulation structure
            subpop = estimate_subpopulation_structure(pca.components, clusters.labels)
            advanced_metrics["subpopulation_structure"] = subpop
        except Exception as e:
            _log(db, run_id, f"⚠ Subpopulation analysis failed: {e}", level="warn")
        
        try:
            # Gene expression specificity
            spec = gene_expression_specificity(qc.counts, clusters.labels)
            advanced_metrics["gene_specificity"] = spec
        except Exception as e:
            _log(db, run_id, f"⚠ Gene specificity analysis failed: {e}", level="warn")
        
        try:
            # Cell cycle phase estimation
            cell_phases = compute_cell_cycle_phase(qc.counts)
            advanced_metrics["cell_cycle_phases"] = {
                "G1": int((cell_phases == "G1").sum()),
                "S": int((cell_phases == "S").sum()),
                "G2/M": int((cell_phases == "G2/M").sum()),
            }
        except Exception as e:
            _log(db, run_id, f"⚠ Cell cycle analysis failed: {e}", level="warn")

        # --- Serialize results to disk ---
        _log(db, run_id, "Serializing results...")
        result_path = settings.storage_dir / f"run_{run_id}.json"
        payload = {
            "metadata": {
                "run_id": run_id,
                "run_name": run.name,
                "dataset": dataset.filename,
                "analysis_timestamp": datetime.utcnow().isoformat(),
                "parameters": params,
            },
            "qc": qc_summary,
            "pca": pca.to_dict(),
            "umap": umap_res.to_dict() if umap_res else None,
            "tsne": tsne_res.to_dict() if tsne_res else None,
            "clusters": clusters.to_dict(),
            "markers": markers,
            "advanced_metrics": advanced_metrics,
            "cell_ids": list(qc.counts.index),
            "gene_names": list(qc.counts.columns),
        }
        
        try:
            result_path.write_text(json.dumps(payload, default=str))
            _log(db, run_id, f"✓ Results saved to {result_path.name}")
        except Exception as e:
            raise IOError(f"Failed to save results: {e}")

        _update(
            db, run_id,
            status="completed",
            progress=100,
            current_step="Done",
            result_path=str(result_path),
            n_cells_qc=qc.n_cells_out,
            n_genes_qc=qc.n_genes_out,
            n_clusters=clusters.n_clusters,
            variance_explained=var_total,
            completed_at=datetime.utcnow(),
        )
        _log(db, run_id, "✓ Analysis complete! 🎉")

    except Exception as e:
        tb = traceback.format_exc()
        error_msg = f"{type(e).__name__}: {str(e)[:200]}"
        
        logger.error(f"Analysis {run_id} failed: {error_msg}\n{tb}")
        
        if run:
            _update(
                db, run_id,
                status="failed",
                progress=0,
                error_message=error_msg,
                completed_at=datetime.utcnow(),
            )
            _log(db, run_id, f"❌ ANALYSIS FAILED: {error_msg}", level="error")
            _log(db, run_id, f"Traceback:\n{tb}", level="error")
    finally:
        if db:
            db.close()
