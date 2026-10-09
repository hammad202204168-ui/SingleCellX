"""
Batch analysis processing for running multiple analyses.

Supports:
- Running analyses across multiple datasets
- Parameter sweeps (testing different parameter combinations)
- Batch result aggregation
"""
from typing import List, Dict, Optional
from dataclasses import dataclass
from datetime import datetime
import json
from pathlib import Path
from sqlalchemy.orm import Session

from ..config import settings
from ..models import AnalysisRun, Project, Dataset
from ..database import SessionLocal


@dataclass
class BatchJob:
    """Represents a batch processing job."""
    id: str
    name: str
    created_at: datetime
    runs: List[int]  # Analysis run IDs
    total: int
    completed: int
    failed: int
    status: str  # pending, processing, completed, failed


class BatchProcessor:
    """Manages batch analysis operations."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def create_batch_from_datasets(
        self,
        project_id: int,
        dataset_ids: List[int],
        analysis_name_template: str = "Batch Analysis {i}",
        parameters: Optional[Dict] = None,
    ) -> BatchJob:
        """Create a batch analysis across multiple datasets.
        
        Parameters:
            project_id: The project ID
            dataset_ids: List of dataset IDs to analyze
            analysis_name_template: Template for run names
            parameters: Common analysis parameters
        
        Returns:
            BatchJob with created run IDs
        """
        project = self.db.query(Project).filter(Project.id == project_id).first()
        if not project:
            raise ValueError(f"Project {project_id} not found")
        
        run_ids = []
        for i, dataset_id in enumerate(dataset_ids):
            dataset = self.db.query(Dataset).filter(
                Dataset.id == dataset_id,
                Dataset.project_id == project_id
            ).first()
            
            if not dataset:
                continue
            
            run = AnalysisRun(
                project_id=project_id,
                dataset_id=dataset_id,
                name=analysis_name_template.format(i=i, dataset=dataset.filename),
                parameters=parameters or {},
                status="pending",
                progress=0,
                current_step="Queued",
            )
            self.db.add(run)
            self.db.flush()
            run_ids.append(run.id)
        
        self.db.commit()
        
        return BatchJob(
            id=f"batch_{project_id}_{datetime.utcnow().timestamp()}",
            name=analysis_name_template,
            created_at=datetime.utcnow(),
            runs=run_ids,
            total=len(run_ids),
            completed=0,
            failed=0,
            status="pending",
        )
    
    def create_parameter_sweep(
        self,
        project_id: int,
        dataset_id: int,
        param_combinations: List[Dict],
        name_prefix: str = "Parameter Sweep",
    ) -> BatchJob:
        """Create a batch analysis with different parameter combinations.
        
        Parameters:
            project_id: The project ID
            dataset_id: The dataset to analyze with different parameters
            param_combinations: List of parameter dicts
            name_prefix: Prefix for run names
        
        Returns:
            BatchJob with created run IDs
        """
        project = self.db.query(Project).filter(Project.id == project_id).first()
        if not project:
            raise ValueError(f"Project {project_id} not found")
        
        dataset = self.db.query(Dataset).filter(
            Dataset.id == dataset_id,
            Dataset.project_id == project_id
        ).first()
        if not dataset:
            raise ValueError(f"Dataset {dataset_id} not found in project")
        
        run_ids = []
        for i, params in enumerate(param_combinations):
            run = AnalysisRun(
                project_id=project_id,
                dataset_id=dataset_id,
                name=f"{name_prefix} {i+1}/{len(param_combinations)}",
                parameters=params,
                status="pending",
                progress=0,
                current_step="Queued",
            )
            self.db.add(run)
            self.db.flush()
            run_ids.append(run.id)
        
        self.db.commit()
        
        return BatchJob(
            id=f"sweep_{project_id}_{dataset_id}_{datetime.utcnow().timestamp()}",
            name=name_prefix,
            created_at=datetime.utcnow(),
            runs=run_ids,
            total=len(run_ids),
            completed=0,
            failed=0,
            status="pending",
        )
    
    def get_batch_status(self, batch_job: BatchJob) -> BatchJob:
        """Update and return the status of a batch job."""
        completed = 0
        failed = 0
        
        for run_id in batch_job.runs:
            run = self.db.query(AnalysisRun).filter(AnalysisRun.id == run_id).first()
            if not run:
                continue
            
            if run.status == "completed":
                completed += 1
            elif run.status == "failed":
                failed += 1
        
        batch_job.completed = completed
        batch_job.failed = failed
        
        if completed + failed == batch_job.total:
            batch_job.status = "completed"
        elif failed > 0 and completed + failed == batch_job.total:
            batch_job.status = "completed"
        elif completed > 0 or failed > 0:
            batch_job.status = "processing"
        
        return batch_job
    
    def aggregate_results(self, batch_job: BatchJob) -> Dict:
        """Aggregate results from all runs in the batch.
        
        Returns a summary with statistics across runs.
        """
        results_summary = {
            "batch_id": batch_job.id,
            "total_runs": batch_job.total,
            "completed": batch_job.completed,
            "failed": batch_job.failed,
            "created_at": batch_job.created_at.isoformat(),
            "runs": {},
        }
        
        cluster_counts = []
        variance_explained = []
        
        for run_id in batch_job.runs:
            run = self.db.query(AnalysisRun).filter(AnalysisRun.id == run_id).first()
            if not run:
                continue
            
            run_summary = {
                "id": run.id,
                "name": run.name,
                "status": run.status,
                "n_clusters": run.n_clusters,
                "variance_explained": run.variance_explained,
                "n_cells_qc": run.n_cells_qc,
                "n_genes_qc": run.n_genes_qc,
            }
            
            results_summary["runs"][str(run_id)] = run_summary
            
            if run.n_clusters:
                cluster_counts.append(run.n_clusters)
            if run.variance_explained:
                variance_explained.append(run.variance_explained)
        
        # Add aggregate statistics
        if cluster_counts:
            results_summary["cluster_stats"] = {
                "mean": sum(cluster_counts) / len(cluster_counts),
                "min": min(cluster_counts),
                "max": max(cluster_counts),
                "count": len(cluster_counts),
            }
        
        if variance_explained:
            results_summary["variance_stats"] = {
                "mean": sum(variance_explained) / len(variance_explained),
                "min": min(variance_explained),
                "max": max(variance_explained),
            }
        
        return results_summary


def create_common_parameter_sweeps() -> Dict[str, List[Dict]]:
    """Predefined parameter sweeps for common analyses."""
    return {
        "cluster_resolution": [
            {"n_clusters": k} for k in [2, 3, 5, 8, 10, 15]
        ],
        "pc_components": [
            {"n_pca_components": n} for n in [30, 50, 75, 100]
        ],
        "umap_neighborhood": [
            {"umap_n_neighbors": n, "umap_min_dist": d}
            for n in [5, 10, 15, 30]
            for d in [0.01, 0.1]
        ],
        "marker_count": [
            {"n_marker_genes": n} for n in [5, 10, 15, 20, 50]
        ],
    }
