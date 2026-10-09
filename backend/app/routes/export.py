"""
Export endpoints for analysis results.

Allows users to download analysis results in multiple formats:
- CSV (markers, embeddings, QC summary)
- JSON (complete results with metadata)
- Zip archive (complete package)
"""
import json
import io
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse, FileResponse
from sqlalchemy.orm import Session

from ..database import get_db
from ..config import settings
from ..models import User, AnalysisRun
from ..auth import get_current_user
from ..services.export import (
    export_markers_csv,
    export_embeddings_csv,
    export_pca_variance_csv,
    export_qc_summary_csv,
    export_cell_assignments_csv,
)


router = APIRouter(tags=["export"])


def _owned_run(run_id: int, db: Session, user: User) -> AnalysisRun:
    """Verify run ownership."""
    run = db.query(AnalysisRun).filter(AnalysisRun.id == run_id).first()
    if run is None:
        raise HTTPException(404, "Run not found")
    if run.project.owner_id != user.id:
        raise HTTPException(403, "Not your run")
    return run


def _load_results(run: AnalysisRun) -> dict:
    """Load results JSON from disk."""
    if not run.result_path:
        raise HTTPException(404, "Results not found")
    
    result_file = Path(run.result_path)
    if not result_file.exists():
        raise HTTPException(404, "Results file not found on disk")
    
    try:
        return json.loads(result_file.read_text())
    except Exception as e:
        raise HTTPException(500, f"Failed to load results: {e}")


@router.get("/api/analysis/{run_id}/export/markers.csv")
def export_markers(
    run_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Export marker genes as CSV."""
    run = _owned_run(run_id, db, user)
    if run.status != "completed":
        raise HTTPException(400, "Analysis not completed")
    
    results = _load_results(run)
    markers = results.get("markers", {})
    
    output = io.BytesIO()
    export_markers_csv(markers, output)
    output.seek(0)
    
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=markers_run_{run_id}.csv"},
    )


@router.get("/api/analysis/{run_id}/export/embeddings-umap.csv")
def export_umap_embedding(
    run_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Export UMAP coordinates as CSV."""
    run = _owned_run(run_id, db, user)
    if run.status != "completed":
        raise HTTPException(400, "Analysis not completed")
    
    results = _load_results(run)
    umap_data = results.get("umap")
    
    if not umap_data or not umap_data.get("coords"):
        raise HTTPException(404, "UMAP embedding not available")
    
    cell_ids = results.get("cell_ids", [])
    clusters = results.get("clusters", {}).get("labels")
    
    output = io.BytesIO()
    export_embeddings_csv("UMAP", umap_data["coords"], cell_ids, clusters, output)
    output.seek(0)
    
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=umap_run_{run_id}.csv"},
    )


@router.get("/api/analysis/{run_id}/export/embeddings-tsne.csv")
def export_tsne_embedding(
    run_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Export t-SNE coordinates as CSV."""
    run = _owned_run(run_id, db, user)
    if run.status != "completed":
        raise HTTPException(400, "Analysis not completed")
    
    results = _load_results(run)
    tsne_data = results.get("tsne")
    
    if not tsne_data or not tsne_data.get("coords"):
        raise HTTPException(404, "t-SNE embedding not available")
    
    cell_ids = results.get("cell_ids", [])
    clusters = results.get("clusters", {}).get("labels")
    
    output = io.BytesIO()
    export_embeddings_csv("tSNE", tsne_data["coords"], cell_ids, clusters, output)
    output.seek(0)
    
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=tsne_run_{run_id}.csv"},
    )


@router.get("/api/analysis/{run_id}/export/pca-variance.csv")
def export_pca_variance(
    run_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Export PCA variance explained per component."""
    run = _owned_run(run_id, db, user)
    if run.status != "completed":
        raise HTTPException(400, "Analysis not completed")
    
    results = _load_results(run)
    pca_data = results.get("pca", {})
    
    variance_ratio = pca_data.get("variance_ratio", [])
    cumulative = pca_data.get("cumulative_variance", [])
    
    if not variance_ratio:
        raise HTTPException(404, "PCA data not available")
    
    output = io.BytesIO()
    export_pca_variance_csv(variance_ratio, cumulative, output)
    output.seek(0)
    
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=pca_variance_run_{run_id}.csv"},
    )


@router.get("/api/analysis/{run_id}/export/cell-clusters.csv")
def export_cell_clusters(
    run_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Export cell cluster assignments."""
    run = _owned_run(run_id, db, user)
    if run.status != "completed":
        raise HTTPException(400, "Analysis not completed")
    
    results = _load_results(run)
    cell_ids = results.get("cell_ids", [])
    cluster_labels = results.get("clusters", {}).get("labels", [])
    
    if not cell_ids or not cluster_labels:
        raise HTTPException(404, "Cluster assignments not available")
    
    output = io.BytesIO()
    export_cell_assignments_csv(cell_ids, cluster_labels, output)
    output.seek(0)
    
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=clusters_run_{run_id}.csv"},
    )


@router.get("/api/analysis/{run_id}/export/qc-summary.csv")
def export_qc(
    run_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Export QC summary metrics."""
    run = _owned_run(run_id, db, user)
    if run.status != "completed":
        raise HTTPException(400, "Analysis not completed")
    
    results = _load_results(run)
    qc_data = results.get("qc", {})
    
    if not qc_data:
        raise HTTPException(404, "QC data not available")
    
    output = io.BytesIO()
    export_qc_summary_csv(qc_data, output)
    output.seek(0)
    
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=qc_run_{run_id}.csv"},
    )


@router.get("/api/analysis/{run_id}/export/results.json")
def export_full_results_json(
    run_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Export complete results as JSON."""
    run = _owned_run(run_id, db, user)
    if run.status != "completed":
        raise HTTPException(400, "Analysis not completed")
    
    results = _load_results(run)
    
    # Add run metadata
    results["run_metadata"] = {
        "run_id": run.id,
        "run_name": run.name,
        "dataset_filename": run.dataset.filename,
        "created_at": run.created_at.isoformat(),
        "completed_at": run.completed_at.isoformat() if run.completed_at else None,
    }
    
    json_str = json.dumps(results, indent=2, default=str)
    
    return StreamingResponse(
        iter([json_str.encode()]),
        media_type="application/json",
        headers={"Content-Disposition": f"attachment; filename=results_run_{run_id}.json"},
    )


@router.get("/api/analysis/{run_id}/export/manifest")
def get_export_manifest(
    run_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Get a manifest of available exports."""
    run = _owned_run(run_id, db, user)
    if run.status != "completed":
        raise HTTPException(400, "Analysis not completed")
    
    results = _load_results(run)
    
    manifest = {
        "run_id": run.id,
        "available_exports": {
            "markers": f"/api/analysis/{run_id}/export/markers.csv",
            "embeddings_umap": f"/api/analysis/{run_id}/export/embeddings-umap.csv",
            "embeddings_tsne": f"/api/analysis/{run_id}/export/embeddings-tsne.csv",
            "pca_variance": f"/api/analysis/{run_id}/export/pca-variance.csv",
            "cell_clusters": f"/api/analysis/{run_id}/export/cell-clusters.csv",
            "qc_summary": f"/api/analysis/{run_id}/export/qc-summary.csv",
            "complete_results": f"/api/analysis/{run_id}/export/results.json",
        },
        "advanced_metrics_available": bool(results.get("advanced_metrics")),
    }
    
    return manifest
