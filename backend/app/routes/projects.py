"""
Project endpoints — full CRUD scoped to the authenticated user.

- GET    /api/projects        : list user's projects
- POST   /api/projects        : create a project
- GET    /api/projects/{id}   : project detail
- PATCH  /api/projects/{id}   : update name/description
- DELETE /api/projects/{id}   : delete project and cascade datasets/runs
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import User, Project
from ..schemas import ProjectCreate, ProjectUpdate, ProjectOut, MessageResponse
from ..auth import get_current_user


router = APIRouter(prefix="/api/projects", tags=["projects"])


def _serialize(p: Project) -> ProjectOut:
    return ProjectOut(
        id=p.id, name=p.name, description=p.description, owner_id=p.owner_id,
        created_at=p.created_at, updated_at=p.updated_at,
        n_datasets=len(p.datasets), n_runs=len(p.runs),
    )


def _owned(project_id: int, db: Session, user: User) -> Project:
    project = db.query(Project).filter(Project.id == project_id).first()
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    if project.owner_id != user.id:
        raise HTTPException(status_code=403, detail="Not your project")
    return project


@router.get("", response_model=list[ProjectOut])
def list_projects(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    projects = db.query(Project).filter(Project.owner_id == user.id).order_by(Project.updated_at.desc()).all()
    return [_serialize(p) for p in projects]


@router.post("", response_model=ProjectOut, status_code=status.HTTP_201_CREATED)
def create_project(
    payload: ProjectCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    project = Project(name=payload.name, description=payload.description, owner_id=user.id)
    db.add(project)
    db.commit()
    db.refresh(project)
    return _serialize(project)


@router.get("/{project_id}", response_model=ProjectOut)
def get_project(project_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return _serialize(_owned(project_id, db, user))


@router.patch("/{project_id}", response_model=ProjectOut)
def update_project(
    project_id: int,
    payload: ProjectUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    project = _owned(project_id, db, user)
    if payload.name is not None:
        project.name = payload.name
    if payload.description is not None:
        project.description = payload.description
    db.commit()
    db.refresh(project)
    return _serialize(project)


@router.delete("/{project_id}", response_model=MessageResponse)
def delete_project(
    project_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    project = _owned(project_id, db, user)
    db.delete(project)
    db.commit()
    return MessageResponse(message=f"Project {project_id} deleted.")
