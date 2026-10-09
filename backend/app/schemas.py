"""
Pydantic schemas — the API contract layer.

These define the shape of JSON payloads coming in and going out of the
HTTP endpoints. They are kept distinct from ORM models so that internal
storage can evolve independently of the public API.
"""
from datetime import datetime
from typing import Optional, Any
from pydantic import BaseModel, EmailStr, Field, ConfigDict


# ============================================================
# AUTH
# ============================================================
class UserCreate(BaseModel):
    email: EmailStr
    username: str = Field(..., min_length=3, max_length=64)
    full_name: Optional[str] = Field(None, max_length=128)
    password: str = Field(..., min_length=6, max_length=128)


class UserLogin(BaseModel):
    username: str
    password: str


class UserOut(BaseModel):
    id: int
    email: EmailStr
    username: str
    full_name: Optional[str]
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


# ============================================================
# PROJECTS
# ============================================================
class ProjectCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=128)
    description: Optional[str] = None


class ProjectUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=128)
    description: Optional[str] = None


class ProjectOut(BaseModel):
    id: int
    name: str
    description: Optional[str]
    owner_id: int
    created_at: datetime
    updated_at: datetime
    n_datasets: int = 0
    n_runs: int = 0
    model_config = ConfigDict(from_attributes=True)


# ============================================================
# DATASETS
# ============================================================
class DatasetOut(BaseModel):
    id: int
    project_id: int
    filename: str
    n_cells: int
    n_genes: int
    sparsity: float
    file_size_bytes: int
    uploaded_at: datetime
    model_config = ConfigDict(from_attributes=True)


# ============================================================
# ANALYSIS PARAMETERS
# ============================================================
class AnalysisParameters(BaseModel):
    min_genes_per_cell: int = Field(150, ge=10, le=5000)
    min_cells_per_gene: int = Field(3, ge=1, le=500)
    n_pca_components: int = Field(50, ge=2, le=200)
    n_clusters: Optional[int] = Field(None, ge=2, le=30)  # None => auto
    umap_n_neighbors: int = Field(15, ge=2, le=200)
    umap_min_dist: float = Field(0.1, ge=0.001, le=1.0)
    tsne_perplexity: int = Field(30, ge=5, le=100)
    n_marker_genes: int = Field(15, ge=1, le=200)


class AnalysisCreate(BaseModel):
    dataset_id: int
    name: str = Field(..., min_length=1, max_length=128)
    parameters: AnalysisParameters = AnalysisParameters()


class LogEntryOut(BaseModel):
    timestamp: datetime
    level: str
    message: str
    model_config = ConfigDict(from_attributes=True)


class AnalysisRunOut(BaseModel):
    id: int
    project_id: int
    dataset_id: int
    name: str
    parameters: dict
    status: str
    progress: int
    current_step: Optional[str]
    error_message: Optional[str]
    n_cells_qc: Optional[int]
    n_genes_qc: Optional[int]
    n_clusters: Optional[int]
    variance_explained: Optional[float]
    created_at: datetime
    completed_at: Optional[datetime]
    model_config = ConfigDict(from_attributes=True)


class AnalysisResultOut(BaseModel):
    """Full results blob returned when the user opens a completed analysis."""
    run: AnalysisRunOut
    qc: dict
    pca: dict
    umap: dict
    tsne: dict
    clusters: dict
    markers: dict
    logs: list[LogEntryOut]


# ============================================================
# UTILITY
# ============================================================
class MessageResponse(BaseModel):
    message: str
    detail: Optional[Any] = None
