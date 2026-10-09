"""
Dataset endpoints.

- POST   /api/projects/{pid}/datasets/upload : multipart CSV upload
- POST   /api/projects/{pid}/datasets/demo   : create a synthetic demo dataset
- GET    /api/projects/{pid}/datasets        : list datasets in project
- GET    /api/datasets/{did}                 : detail
- DELETE /api/datasets/{did}                 : delete (with cascade)
"""
import csv
import uuid
from pathlib import Path
import numpy as np
import pandas as pd
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.orm import Session

from ..config import settings
from ..database import get_db
from ..models import User, Project, Dataset
from ..schemas import DatasetOut, MessageResponse
from ..auth import get_current_user
from ..services.demo_data import create_demo_data


router = APIRouter(tags=["datasets"])


def _serialize(d: Dataset) -> DatasetOut:
    return DatasetOut.model_validate(d)


def _owned_project(pid: int, db: Session, user: User) -> Project:
    project = db.query(Project).filter(Project.id == pid).first()
    if project is None:
        raise HTTPException(404, "Project not found")
    if project.owner_id != user.id:
        raise HTTPException(403, "Not your project")
    return project


def _inspect_csv(path: Path) -> tuple[int, int, float]:
    """Cheap inspection — read once with pandas, return (cells, genes, sparsity%)."""
    df = pd.read_csv(path, index_col=0)
    df = df.fillna(0).select_dtypes(include=[np.number])
    cells, genes = df.shape
    sparsity = float((df == 0).sum().sum() / max(df.size, 1) * 100)
    return cells, genes, sparsity


@router.post("/api/projects/{project_id}/datasets/upload", response_model=DatasetOut)
async def upload_dataset(
    project_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    project = _owned_project(project_id, db, user)
    if not file.filename.lower().endswith(".csv"):
        raise HTTPException(400, "Only .csv files are accepted.")

    # Stream to disk with a unique name to avoid collisions
    safe_name = f"{uuid.uuid4().hex}_{Path(file.filename).name}"
    dest = settings.upload_dir / safe_name

    size = 0
    max_bytes = settings.max_upload_size_mb * 1024 * 1024
    with dest.open("wb") as f:
        while chunk := await file.read(1024 * 1024):
            size += len(chunk)
            if size > max_bytes:
                dest.unlink(missing_ok=True)
                raise HTTPException(413, f"File exceeds {settings.max_upload_size_mb} MB limit.")
            f.write(chunk)

    try:
        n_cells, n_genes, sparsity = _inspect_csv(dest)
    except Exception as e:
        dest.unlink(missing_ok=True)
        raise HTTPException(400, f"Could not parse CSV: {e}")

    if n_cells < 10 or n_genes < 10:
        dest.unlink(missing_ok=True)
        raise HTTPException(400, "Dataset too small (need >=10 cells × 10 genes).")

    ds = Dataset(
        project_id=project.id,
        filename=file.filename,
        file_path=str(dest),
        n_cells=n_cells,
        n_genes=n_genes,
        sparsity=sparsity,
        file_size_bytes=size,
    )
    db.add(ds)
    db.commit()
    db.refresh(ds)
    return _serialize(ds)


@router.post("/api/projects/{project_id}/datasets/demo", response_model=DatasetOut)
def create_demo_dataset(
    project_id: int,
    n_cells: int = 600,
    n_genes: int = 2500,
    n_clusters: int = 6,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    project = _owned_project(project_id, db, user)

    df = create_demo_data(n_cells=n_cells, n_genes=n_genes, n_clusters=n_clusters)
    safe_name = f"demo_{uuid.uuid4().hex}.csv"
    dest = settings.upload_dir / safe_name
    df.to_csv(dest)

    ds = Dataset(
        project_id=project.id,
        filename=f"Demo dataset ({n_cells} cells, {n_clusters} clusters)",
        file_path=str(dest),
        n_cells=n_cells,
        n_genes=n_genes,
        sparsity=float((df == 0).sum().sum() / df.size * 100),
        file_size_bytes=dest.stat().st_size,
    )
    db.add(ds)
    db.commit()
    db.refresh(ds)
    return _serialize(ds)


@router.get("/api/projects/{project_id}/datasets", response_model=list[DatasetOut])
def list_datasets(
    project_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    project = _owned_project(project_id, db, user)
    return [_serialize(d) for d in project.datasets]


@router.get("/api/datasets/{dataset_id}", response_model=DatasetOut)
def get_dataset(dataset_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    ds = db.query(Dataset).filter(Dataset.id == dataset_id).first()
    if ds is None:
        raise HTTPException(404, "Dataset not found")
    _owned_project(ds.project_id, db, user)
    return _serialize(ds)


@router.delete("/api/datasets/{dataset_id}", response_model=MessageResponse)
def delete_dataset(dataset_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    ds = db.query(Dataset).filter(Dataset.id == dataset_id).first()
    if ds is None:
        raise HTTPException(404, "Dataset not found")
    _owned_project(ds.project_id, db, user)
    # Best-effort delete of file
    try:
        Path(ds.file_path).unlink(missing_ok=True)
    except Exception:
        pass
    db.delete(ds)
    db.commit()
    return MessageResponse(message=f"Dataset {dataset_id} deleted.")
