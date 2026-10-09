"""
ORM models — the persistence layer.

Five tables:
- users        : researchers using the platform
- projects     : a project groups multiple datasets and analyses
- datasets     : raw uploaded expression matrices (path on disk)
- analysis_runs: an executed analysis (status, params, links to results)
- results      : serialized analysis output (JSON blob on disk + summary in DB)
"""
from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Float, DateTime, ForeignKey, Text, JSON, Boolean
)
from sqlalchemy.orm import relationship, Mapped, mapped_column
from typing import Optional

from .database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    username: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    full_name: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    projects = relationship("Project", back_populates="owner", cascade="all, delete-orphan")


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    owner = relationship("User", back_populates="projects")
    datasets = relationship("Dataset", back_populates="project", cascade="all, delete-orphan")
    runs = relationship("AnalysisRun", back_populates="project", cascade="all, delete-orphan")


class Dataset(Base):
    __tablename__ = "datasets"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), nullable=False)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    file_path: Mapped[str] = mapped_column(String(512), nullable=False)
    n_cells: Mapped[int] = mapped_column(Integer, default=0)
    n_genes: Mapped[int] = mapped_column(Integer, default=0)
    sparsity: Mapped[float] = mapped_column(Float, default=0.0)
    file_size_bytes: Mapped[int] = mapped_column(Integer, default=0)
    uploaded_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    project = relationship("Project", back_populates="datasets")
    runs = relationship("AnalysisRun", back_populates="dataset", cascade="all, delete-orphan")


class AnalysisRun(Base):
    __tablename__ = "analysis_runs"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), nullable=False)
    dataset_id: Mapped[int] = mapped_column(ForeignKey("datasets.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(128), nullable=False)

    # Parameters chosen for this run (JSON for flexibility)
    parameters: Mapped[dict] = mapped_column(JSON, default=dict)

    # Lifecycle
    status: Mapped[str] = mapped_column(String(32), default="pending")
    # pending | running | completed | failed
    progress: Mapped[int] = mapped_column(Integer, default=0)  # 0-100
    current_step: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Results pointer
    result_path: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)

    # Summary metrics (denormalized for fast list views)
    n_cells_qc: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    n_genes_qc: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    n_clusters: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    variance_explained: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    project = relationship("Project", back_populates="runs")
    dataset = relationship("Dataset", back_populates="runs")
    log_entries = relationship("LogEntry", back_populates="run", cascade="all, delete-orphan")


class LogEntry(Base):
    """Per-step log lines — useful for the live progress panel."""
    __tablename__ = "log_entries"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    run_id: Mapped[int] = mapped_column(ForeignKey("analysis_runs.id"), nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    level: Mapped[str] = mapped_column(String(16), default="info")  # info|warn|error
    message: Mapped[str] = mapped_column(Text, nullable=False)

    run = relationship("AnalysisRun", back_populates="log_entries")
