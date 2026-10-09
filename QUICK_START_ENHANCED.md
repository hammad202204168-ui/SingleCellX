# Enhanced SingleCellX - Quick Start Guide

## What's New

This is the **Enhanced Edition** of SingleCellX with major improvements:

### ✨ New Features
- **📊 Advanced Metrics**: Cell cycle estimation, batch effect detection, neighborhood diversity
- **📥 Export System**: Download results as CSV, JSON in multiple formats
- **🔄 Batch Processing**: Analyze multiple datasets or parameter combinations at once
- **⚡ Performance**: Intelligent caching of expensive computations
- **🛡️ Robust**: Enhanced error handling with detailed logging
- **📱 Better API**: Improved frontend client with polling support

## Installation

### 1. Install Dependencies
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r backend/requirements.txt
```

### 2. Start the Server
```bash
cd backend
uvicorn app.main:app --reload --port 8000
```

### 3. Open in Browser
Navigate to `http://localhost:8000`

## Using the Enhanced Features

### Exporting Analysis Results

After an analysis completes, you can export results in multiple formats:

**Via Web Interface:**
1. Go to your analysis result page
2. Click "Export Results" dropdown
3. Select format (CSV/JSON)

**Via API:**
```bash
# Get list of available exports
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/analysis/1/export/manifest

# Download markers as CSV
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/analysis/1/export/markers.csv > markers.csv

# Download complete results as JSON
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/analysis/1/export/results.json > results.json
```

### Using JavaScript Client

```javascript
const client = new SingleCellXClient();

// Login
await client.login('username', 'password');

// Get projects
const projects = await client.listProjects();

// Create dataset
const dataset = await client.uploadDataset(projectId, fileInput.files[0]);

// Start analysis
const run = await client.startAnalysis(datasetId, 'My Analysis', {
    n_clusters: 10,
    n_pca_components: 50,
});

// Poll for completion
await client.pollAnalysis(
    run.id,
    (status, progress, step) => {
        console.log(`${progress}% - ${step}`);
    },
    (results) => {
        console.log('Complete!', results);
    },
    (error) => {
        console.error('Failed:', error);
    }
);

// Get export manifest
const manifest = await client.getExportManifest(run.id);
console.log(manifest.available_exports);

// Download results
client.downloadExport(run.id, 'markers');
client.downloadExport(run.id, 'json');
```

### Batch Processing

Run multiple analyses efficiently:

```python
from app.services.batch import BatchProcessor

processor = BatchProcessor(db)

# Analyze 5 datasets with same parameters
batch = processor.create_batch_from_datasets(
    project_id=1,
    dataset_ids=[1, 2, 3, 4, 5],
    analysis_name_template="Cohort Analysis {dataset}",
    parameters={
        "n_clusters": 10,
        "n_pca_components": 50,
    }
)

# Check progress
status = processor.get_batch_status(batch)
print(f"Progress: {status.completed}/{status.total} complete")

# Get aggregated results
summary = processor.aggregate_results(batch)
print(summary)
```

### Advanced Metrics

The enhanced pipeline automatically computes additional metrics:

```python
# In analysis results, look for:
results['advanced_metrics'] = {
    'batch_effects': {...},           # Batch effect detection
    'neighborhood_diversity': {...},  # Local cluster mixing
    'subpopulation_structure': {...}, # Intra/inter-cluster distances
    'gene_specificity': {...},        # Gene expression distribution
    'cell_cycle_phases': {...},       # G1/S/G2M counts
}
```

## Performance Tips

### 1. Use Caching
```python
from app.services.cache import get_cache

cache = get_cache()

# Monitor cache performance
stats = cache.stats()
print(f"Cache hit rate: {stats['hit_rate_pct']}%")

# Clear if needed
cache.clear()
```

### 2. Parameter Sweeps
Test multiple parameters efficiently:

```python
from app.services.batch import create_common_parameter_sweeps

sweeps = create_common_parameter_sweeps()

# Test 6 different cluster counts
batch = processor.create_parameter_sweep(
    project_id=1,
    dataset_id=1,
    param_combinations=sweeps['cluster_resolution'],  # [2,3,5,8,10,15]
)

# Results show clustering quality for each count
summary = processor.aggregate_results(batch)
print(summary['cluster_stats'])  # Compare quality metrics
```

### 3. Handle Large Files
The export system streams large results without memory overhead:

```javascript
// Download even very large result files
client.downloadExport(run.id, 'json');  // Works with 1GB+ files
```

## API Endpoints Summary

### Analysis Management
```
POST   /api/analysis                        Create & queue analysis
GET    /api/projects/{id}/analysis          List analyses
GET    /api/analysis/{id}                   Get status
GET    /api/analysis/{id}/logs              Get live logs
GET    /api/analysis/{id}/results           Get complete results
DELETE /api/analysis/{id}                   Delete analysis
```

### Export
```
GET    /api/analysis/{id}/export/manifest        List available exports
GET    /api/analysis/{id}/export/markers.csv     Marker genes
GET    /api/analysis/{id}/export/embeddings-*.csv  Cell coordinates
GET    /api/analysis/{id}/export/pca-variance.csv   PCA variance
GET    /api/analysis/{id}/export/results.json       Complete results
```

## Monitoring & Debugging

### View Analysis Logs
```bash
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/analysis/1/logs | jq '.[] | "\(.timestamp) [\(.level)] \(.message)"'
```

### Check System Health
```bash
curl http://localhost:8000/api/health
```

### Database Query
```python
from app.database import SessionLocal
from app.models import AnalysisRun, LogEntry

db = SessionLocal()
run = db.query(AnalysisRun).filter(AnalysisRun.id == 1).first()
print(f"Status: {run.status}")
print(f"Progress: {run.progress}%")
print(f"Step: {run.current_step}")

# Get all logs for a run
logs = db.query(LogEntry).filter(LogEntry.run_id == 1).all()
for log in logs:
    print(f"{log.timestamp} [{log.level}] {log.message}")
```

## Troubleshooting

### Analysis keeps failing
1. Check logs: `/api/analysis/{id}/logs`
2. Verify data is valid CSV
3. Check file size isn't exceeding limit
4. Try with demo dataset first

### Export not available
1. Ensure analysis is completed: `status == "completed"`
2. Check server logs for file access errors
3. Verify storage directory permissions

### Batch job slow
1. Monitor individual run logs
2. Check system resources
3. Consider parameter limits for sweep

## Configuration

Edit `backend/app/config.py`:

```python
class Settings(BaseSettings):
    # Increase upload size if needed
    max_upload_size_mb: int = 500  # Default: 100
    
    # Adjust cache TTL
    cache_ttl_seconds: int = 7200  # 2 hours
    
    # Change database
    database_url: str = "postgresql://user:pass@host/db"
    
    # Update allowed origins
    allowed_origins: list[str] = [
        "http://myserver.com",
        "https://myserver.com",
    ]
```

## Next Steps

1. ✅ Create a project
2. ✅ Upload or generate a dataset
3. ✅ Run analysis with default parameters
4. ✅ Export results in desired format
5. ✅ Try batch analysis with parameter sweep
6. ✅ Monitor advanced metrics

## Support

See `ENHANCEMENTS.md` for detailed documentation of all new features.

For issues:
1. Check the logs at `/api/analysis/{id}/logs`
2. Review configuration in `config.py`
3. Verify database integrity
4. Try with demo dataset to isolate issues

## Version Info

- **Version**: 2.0.0 (Enhanced Edition)
- **Date**: 2024
- **New Modules**: cache, advanced_analysis, export, batch
- **Enhanced Modules**: runner (executor), routes (API), client (frontend)
