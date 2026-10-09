"""
Analysis endpoints.

- POST   /api/analysis                       : create + queue a new run
- GET    /api/projects/{pid}/analysis        : list runs for a project
- GET    /api/analysis/{run_id}              : run metadata + status
- GET    /api/analysis/{run_id}/logs         : live log tail
- GET    /api/analysis/{run_id}/results      : full results payload (when completed)
- DELETE /api/analysis/{run_id}              : delete a run
"""
import json
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, status
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import User, Project, Dataset, AnalysisRun, LogEntry
from ..schemas import (
    AnalysisCreate, AnalysisRunOut, LogEntryOut, AnalysisResultOut, MessageResponse,
)
from ..auth import get_current_user
from ..services.runner import execute_analysis


router = APIRouter(tags=["analysis"])


def _owned_run(run_id: int, db: Session, user: User) -> AnalysisRun:
    run = db.query(AnalysisRun).filter(AnalysisRun.id == run_id).first()
    if run is None:
        raise HTTPException(404, "Run not found")
    if run.project.owner_id != user.id:
        raise HTTPException(403, "Not your run")
    return run


@router.post("/api/analysis", response_model=AnalysisRunOut, status_code=status.HTTP_202_ACCEPTED)
def create_run(
    payload: AnalysisCreate,
    background: BackgroundTasks,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    dataset = db.query(Dataset).filter(Dataset.id == payload.dataset_id).first()
    if dataset is None:
        raise HTTPException(404, "Dataset not found")
    if dataset.project.owner_id != user.id:
        raise HTTPException(403, "Not your dataset")

    run = AnalysisRun(
        project_id=dataset.project_id,
        dataset_id=dataset.id,
        name=payload.name,
        parameters=payload.parameters.model_dump(),
        status="pending",
        progress=0,
        current_step="Queued",
    )
    db.add(run)
    db.commit()
    db.refresh(run)

    # Fire-and-forget; runner manages its own DB session
    background.add_task(execute_analysis, run.id)
    return AnalysisRunOut.model_validate(run)


@router.get("/api/projects/{project_id}/analysis", response_model=list[AnalysisRunOut])
def list_runs(project_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    project = db.query(Project).filter(Project.id == project_id).first()
    if project is None:
        raise HTTPException(404, "Project not found")
    if project.owner_id != user.id:
        raise HTTPException(403, "Not your project")
    runs = db.query(AnalysisRun).filter(AnalysisRun.project_id == project_id).order_by(AnalysisRun.created_at.desc()).all()
    return [AnalysisRunOut.model_validate(r) for r in runs]


@router.get("/api/analysis/{run_id}", response_model=AnalysisRunOut)
def get_run(run_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    run = _owned_run(run_id, db, user)
    return AnalysisRunOut.model_validate(run)


@router.get("/api/analysis/{run_id}/logs", response_model=list[LogEntryOut])
def get_logs(
    run_id: int,
    limit: int = 200,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    run = _owned_run(run_id, db, user)
    entries = (
        db.query(LogEntry)
        .filter(LogEntry.run_id == run.id)
        .order_by(LogEntry.id.asc())
        .limit(limit)
        .all()
    )
    return [LogEntryOut.model_validate(e) for e in entries]


@router.get("/api/analysis/{run_id}/results", response_model=AnalysisResultOut)
def get_results(run_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    run = _owned_run(run_id, db, user)
    if run.status != "completed" or not run.result_path:
        raise HTTPException(409, f"Run is not complete (status={run.status}).")

    path = Path(run.result_path)
    if not path.exists():
        raise HTTPException(410, "Result file missing on disk.")

    payload = json.loads(path.read_text())
    logs = (
        db.query(LogEntry)
        .filter(LogEntry.run_id == run.id)
        .order_by(LogEntry.id.asc())
        .all()
    )

    return AnalysisResultOut(
        run=AnalysisRunOut.model_validate(run),
        qc=payload["qc"],
        pca=payload["pca"],
        umap=payload["umap"],
        tsne=payload["tsne"],
        clusters=payload["clusters"],
        markers=payload["markers"],
        logs=[LogEntryOut.model_validate(e) for e in logs],
    )


@router.delete("/api/analysis/{run_id}", response_model=MessageResponse)
def delete_run(run_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    run = _owned_run(run_id, db, user)
    if run.result_path:
        try:
            Path(run.result_path).unlink(missing_ok=True)
        except Exception:
            pass
    db.delete(run)
    db.commit()
    return MessageResponse(message=f"Run {run_id} deleted.")
