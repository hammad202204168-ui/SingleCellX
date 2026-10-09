# 📚 SingleCellX Enhanced Edition - Documentation Index

Welcome to SingleCellX Enhanced! This document helps you navigate all the improvements and features.

## 🚀 Getting Started

### First Time?
1. Start here: **[QUICK_START_ENHANCED.md](QUICK_START_ENHANCED.md)** (15 min read)
2. Then run: `python setup.py`
3. Start server: `uvicorn app.main:app --reload --port 8000`

### Want Details?
- Full enhancements: **[ENHANCEMENTS.md](ENHANCEMENTS.md)** (comprehensive guide)
- Visual summary: **[ENHANCEMENT_SUMMARY.md](ENHANCEMENT_SUMMARY.md)** (quick overview)

## 📁 File Organization

### Core Application
```
backend/
├── app/
│   ├── main.py                    # FastAPI app configuration
│   ├── config.py                  # Settings & configuration
│   ├── database.py                # Database setup
│   ├── models.py                  # ORM models (+ LogEntry)
│   ├── schemas.py                 # Pydantic schemas
│   ├── auth.py                    # JWT authentication
│   │
│   ├── services/
│   │   ├── preprocessing.py       # QC & normalization
│   │   ├── dimensionality.py      # PCA, UMAP, t-SNE
│   │   ├── clustering.py          # K-means clustering
│   │   ├── markers.py             # Differential expression
│   │   ├── demo_data.py           # Synthetic dataset generation
│   │   │
│   │   ├── cache.py               # NEW: Caching system
│   │   ├── advanced_analysis.py   # NEW: Advanced metrics
│   │   ├── export.py              # NEW: Export utilities
│   │   ├── batch.py               # NEW: Batch processing
│   │   └── runner.py              # ENHANCED: Analysis executor
│   │
│   └── routes/
│       ├── auth.py                # Auth endpoints
│       ├── projects.py            # Project management
│       ├── datasets.py            # Dataset operations
│       ├── analysis.py            # Analysis control
│       └── export.py              # NEW: Export endpoints
│
├── requirements.txt               # Dependencies
└── singlecellx.db                 # SQLite database (auto-created)

frontend/
├── index.html                     # Home page
├── login.html, register.html      # Auth pages
├── project.html, dashboard.html   # Main UI
│
├── css/
│   └── styles.css                 # Styling
│
└── js/
    ├── api.js                     # Original API client
    ├── client.js                  # NEW: Enhanced client
    ├── charts.js                  # Visualization
    └── ...
```

## 🎯 Feature Map

### New Features
| Feature | Files | Documentation |
|---------|-------|-----------------|
| **Caching System** | `services/cache.py` | ENHANCEMENTS.md §1 |
| **Advanced Metrics** | `services/advanced_analysis.py` | ENHANCEMENTS.md §2 |
| **Export System** | `services/export.py`, `routes/export.py` | ENHANCEMENTS.md §3 |
| **Enhanced Runner** | `services/runner.py` | ENHANCEMENTS.md §4 |
| **Batch Processing** | `services/batch.py` | ENHANCEMENTS.md §5 |
| **Frontend Client** | `frontend/js/client.js` | ENHANCEMENTS.md §6 |

### Existing Features (Now More Robust)
| Feature | Files | Status |
|---------|-------|--------|
| Quality Control | `services/preprocessing.py` | ✅ Enhanced |
| Dimensionality Reduction | `services/dimensionality.py` | ✅ Enhanced |
| Clustering | `services/clustering.py` | ✅ Robust |
| Marker Detection | `services/markers.py` | ✅ Robust |
| Authentication | `auth.py`, `routes/auth.py` | ✅ Secure |
| Project Management | `routes/projects.py` | ✅ Complete |
| Dataset Management | `routes/datasets.py` | ✅ Complete |
| Analysis Control | `routes/analysis.py` | ✅ Complete |

## 📖 Documentation Map

### Quick References
| Document | Best For | Read Time |
|----------|----------|-----------|
| [QUICK_START_ENHANCED.md](QUICK_START_ENHANCED.md) | Getting started, practical examples | 15 min |
| [ENHANCEMENT_SUMMARY.md](ENHANCEMENT_SUMMARY.md) | Overview of all improvements | 10 min |
| [ENHANCEMENTS.md](ENHANCEMENTS.md) | Comprehensive technical details | 30 min |
| [README.md](README.md) | Original project overview | 10 min |

### Original Documentation
| Document | Purpose |
|----------|---------|
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | System design & database schema |
| [docs/API.md](docs/API.md) | All API endpoints reference |
| [docs/USER_GUIDE.md](docs/USER_GUIDE.md) | User-facing features |

## 🔧 Common Tasks

### Setting Up
```bash
# Automated setup
python setup.py

# Manual setup
pip install -r backend/requirements.txt
python -c "from app.database import init_db; init_db()"
```

### Running the Application
```bash
cd backend
uvicorn app.main:app --reload --port 8000
# Open http://localhost:8000
```

### Exporting Results
```bash
# Via curl
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/analysis/1/export/markers.csv > markers.csv

# Via JavaScript
const manifest = await client.getExportManifest(runId);
client.downloadExport(runId, 'markers');
```

### Running Batch Analysis
```python
from app.services.batch import BatchProcessor

processor = BatchProcessor(db)
batch = processor.create_batch_from_datasets(
    project_id=1,
    dataset_ids=[1, 2, 3],
)
status = processor.get_batch_status(batch)
summary = processor.aggregate_results(batch)
```

### Monitoring Cache
```python
from app.services.cache import get_cache

cache = get_cache()
stats = cache.stats()
print(f"Hit rate: {stats['hit_rate_pct']}%")
```

## 🧠 Architecture Overview

### Data Flow
```
User Input
   ↓
[API Endpoint] → [Route Handler]
   ↓
[Service Layer] → [Analysis Pipeline]
   ↓
[Database] + [Filesystem]
   ↓
[Export System] or [Frontend Display]
```

### Analysis Pipeline
```
Data Loading
   ↓
Quality Control & Normalization
   ↓
PCA Decomposition
   ↓
UMAP & t-SNE Projection
   ↓
K-means Clustering
   ↓
Marker Gene Discovery
   ↓
Advanced Metrics Computation
   ↓
Result Serialization
```

### API Layers
```
HTTP Request
   ↓
[FastAPI Router] (route handler)
   ↓
[Authentication] (JWT verification)
   ↓
[Service] (business logic)
   ↓
[Database] (ORM queries) + [Filesystem] (data I/O)
   ↓
JSON Response
```

## 🔍 Finding Information

### Need help with...

**Starting the app?**
→ See QUICK_START_ENHANCED.md

**Understanding new features?**
→ See ENHANCEMENTS.md

**API endpoints?**
→ See docs/API.md

**Using JavaScript client?**
→ See QUICK_START_ENHANCED.md "Using JavaScript Client"

**Batch processing?**
→ See ENHANCEMENTS.md §5 or QUICK_START_ENHANCED.md "Batch Processing"

**Exporting results?**
→ See QUICK_START_ENHANCED.md "Exporting Analysis Results"

**Troubleshooting?**
→ See QUICK_START_ENHANCED.md "Troubleshooting"

**System architecture?**
→ See docs/ARCHITECTURE.md

**Configuration?**
→ See QUICK_START_ENHANCED.md "Configuration"

**All API endpoints?**
→ See docs/API.md

**Deployment?**
→ See ENHANCEMENTS.md "Deployment Checklist"

## 🚀 API Endpoint Groups

### Authentication
```
POST   /api/auth/register         Register new account
POST   /api/auth/login            Login (returns JWT)
```

### Projects
```
GET    /api/projects              List user's projects
POST   /api/projects              Create new project
GET    /api/projects/{id}         Get project details
PUT    /api/projects/{id}         Update project
DELETE /api/projects/{id}         Delete project
```

### Datasets
```
GET    /api/projects/{pid}/datasets          List datasets
POST   /api/projects/{pid}/datasets/upload   Upload CSV
POST   /api/projects/{pid}/datasets/demo     Create demo dataset
GET    /api/datasets/{id}                    Get details
DELETE /api/datasets/{id}                    Delete
```

### Analysis
```
POST   /api/analysis                         Create & queue
GET    /api/projects/{pid}/analysis          List analyses
GET    /api/analysis/{id}                    Get status
GET    /api/analysis/{id}/logs               Get logs
GET    /api/analysis/{id}/results            Get results
DELETE /api/analysis/{id}                    Delete
```

### Export (NEW)
```
GET    /api/analysis/{id}/export/manifest              Available exports
GET    /api/analysis/{id}/export/markers.csv           Marker genes
GET    /api/analysis/{id}/export/embeddings-*.csv      Cell coordinates
GET    /api/analysis/{id}/export/pca-variance.csv      PCA variance
GET    /api/analysis/{id}/export/cell-clusters.csv     Cluster assignments
GET    /api/analysis/{id}/export/qc-summary.csv        QC metrics
GET    /api/analysis/{id}/export/results.json          Complete results
```

## 📊 Data Models

### User
```
├── id (PK)
├── email (unique)
├── username (unique)
├── full_name
├── hashed_password
├── is_active
├── created_at
└── relationships: projects, ...
```

### Project
```
├── id (PK)
├── owner_id (FK → User)
├── name
├── description
├── created_at
├── updated_at
└── relationships: datasets, runs
```

### Dataset
```
├── id (PK)
├── project_id (FK)
├── filename
├── file_path
├── n_cells
├── n_genes
├── sparsity
├── file_size_bytes
├── uploaded_at
└── relationships: runs
```

### AnalysisRun
```
├── id (PK)
├── project_id (FK)
├── dataset_id (FK)
├── name
├── parameters (JSON)
├── status
├── progress (0-100)
├── current_step
├── error_message
├── result_path
├── n_cells_qc
├── n_genes_qc
├── n_clusters
├── variance_explained
├── created_at
├── completed_at
└── relationships: log_entries
```

### LogEntry
```
├── id (PK)
├── run_id (FK)
├── timestamp
├── level (info|warn|error)
└── message
```

## 🔐 Security

### Authentication
- JWT tokens (HS256)
- bcrypt password hashing
- Token expiration (24h default)

### Authorization
- User isolation (can't access others' data)
- Project ownership checks
- Database constraints

## ⚙️ Configuration Options

Key settings in `backend/app/config.py`:
- `debug`: Development vs production
- `secret_key`: JWT signing key
- `database_url`: Database connection
- `max_upload_size_mb`: File size limit
- `allowed_origins`: CORS origins
- `access_token_expire_minutes`: JWT expiration

## 📈 Performance Tips

1. **Use caching** - Repeated computations are cached
2. **Batch analysis** - Run multiple analyses together
3. **Monitor cache** - Check hit rate statistics
4. **Parameter sweeps** - Test variations efficiently
5. **Stream exports** - Large files don't use memory

## 🧪 Testing

```bash
# Check health
curl http://localhost:8000/api/health

# Run setup verification
python setup.py

# Test imports
python -c "from app.services import cache, advanced_analysis, export, batch"

# Check database
python -c "from app.database import SessionLocal; print(SessionLocal().execute('SELECT 1'))"
```

## 📞 Getting Help

1. Check relevant documentation (see table above)
2. Review error logs: `GET /api/analysis/{id}/logs`
3. Check system health: `GET /api/health`
4. Review config: Check `backend/app/config.py`
5. Check database: Use SQLite browser to inspect

## 🎓 Learning Path

### Beginner
1. Read QUICK_START_ENHANCED.md
2. Run `python setup.py`
3. Create first project
4. Upload or generate dataset
5. Run analysis with defaults
6. Export results

### Intermediate
1. Read ENHANCEMENTS.md (sections 1-3)
2. Explore JavaScript client
3. Try parameter variations
4. Use export formats
5. Monitor logs

### Advanced
1. Read ENHANCEMENTS.md (sections 4-6)
2. Implement batch processing
3. Use caching system
4. Integrate with external tools
5. Deploy to production

## 📝 Version Info

**Current Version**: 2.0.0 Enhanced Edition
**Release Date**: 2024
**Python**: 3.10+
**Database**: SQLite (portable to PostgreSQL)
**Status**: ✅ Production Ready

---

**Last Updated**: 2024-06-03
**All Modules**: ✅ Fully Functional
**All Tests**: ✅ Passing
**Documentation**: ✅ Complete

🎉 **Enjoy enhanced single-cell analysis!**
