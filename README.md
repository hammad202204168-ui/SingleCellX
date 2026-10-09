# SingleCellX

**A full-stack platform for single-cell RNA-seq analysis**

Final Year Project — BS Bioinformatics
Department of Bioinformatics & Biotechnology

---

## Overview

SingleCellX is a web-based platform that turns a complete single-cell RNA-seq analysis pipeline into a hosted, multi-user, reproducible research environment. Users register an account, organise their work into projects, upload (or synthesise) gene-expression matrices, and launch end-to-end analysis runs that execute asynchronously on the server. Every run is persisted, queryable, exportable, and reproducible from its stored parameters.

The platform was developed from a single-file Streamlit prototype and re-architected into a proper client/server application with separation of concerns, authentication, background processing, audit logging, and a custom front-end. The science is unchanged — the engineering is what is new.

## Pipeline

Each analysis run executes the canonical six-stage scRNA-seq workflow:

1. **Quality control** — filter low-detection cells and rare genes; report sparsity and library statistics.
2. **Normalization** — library-size scaling followed by `log1p` transformation.
3. **Principal Component Analysis** — linear denoising; reports per-component and cumulative variance.
4. **UMAP & t-SNE** — two complementary 2-D embeddings for visual cluster inspection; UMAP falls back to t-SNE if `umap-learn` is unavailable.
5. **K-Means clustering** — number of clusters either user-supplied or chosen automatically using the elbow method on within-cluster sum of squares; silhouette score reported.
6. **Marker-gene discovery** — per-cluster differential expression via Welch's t-test on log-fold change, filtered by p-value and effect size, ranked by effect size.

## Architecture

```
┌────────────────────────┐         ┌─────────────────────────────┐
│  Browser (vanilla JS)  │ ──────▶ │   FastAPI application       │
│  Plotly.js charts      │ ◀────── │   JWT auth · BackgroundTask │
└────────────────────────┘         │   SQLAlchemy 2.0 ORM        │
                                   └─────────────────────────────┘
                                                │
                              ┌─────────────────┴──────────────────┐
                              ▼                                    ▼
                       ┌─────────────┐                     ┌──────────────┐
                       │  SQLite DB  │                     │ Filesystem    │
                       │ (state)     │                     │ - uploads/    │
                       └─────────────┘                     │ - storage/    │
                                                           └──────────────┘
```

The database stores users, projects, datasets, run state, and audit logs. Large result blobs (embeddings, marker tables, log entries) are written to disk as JSON to keep the database lean and indexable. See `docs/ARCHITECTURE.md` for the full layout.

## Tech stack

| Layer       | Technology                                              |
| ----------- | ------------------------------------------------------- |
| API server  | FastAPI 0.115, Uvicorn                                  |
| ORM         | SQLAlchemy 2.0 (declarative, typed Mapped columns)      |
| Database    | SQLite (zero-config; portable to PostgreSQL unchanged)  |
| Auth        | JWT (`python-jose`) + bcrypt password hashing           |
| Async       | FastAPI BackgroundTasks (no Celery/Redis needed)        |
| Validation  | Pydantic v2                                             |
| Numerics    | NumPy, pandas, scikit-learn, scipy                      |
| Embeddings  | umap-learn (UMAP), scikit-learn (t-SNE)                 |
| Front-end   | Vanilla HTML / ES6 modules / Plotly.js (no build step)  |
| Styling     | Hand-written CSS design system, dark theme              |

## Quick start

```bash
# 1. Install Python dependencies (Python >= 3.10)
pip install -r backend/requirements.txt

# 2. Start the server (serves both API and frontend from same origin)
cd backend
uvicorn app.main:app --reload --port 8000

# 3. Open in browser
#    http://localhost:8000
```

Or use the helper:

```bash
chmod +x run.sh
./run.sh
```

Then register a new account at `/register.html`, create a project, generate a synthetic dataset (or upload a CSV with cells as rows and genes as columns), and launch your first analysis. Results appear within seconds.

## Project structure

```
singlecellx-fyp/
├── backend/
│   ├── app/
│   │   ├── main.py           # FastAPI app + frontend mount
│   │   ├── config.py         # Settings, paths
│   │   ├── database.py       # SQLAlchemy engine, session, init_db
│   │   ├── models.py         # User, Project, Dataset, AnalysisRun, LogEntry
│   │   ├── schemas.py        # Pydantic request/response models
│   │   ├── auth.py           # JWT + bcrypt
│   │   ├── routes/
│   │   │   ├── auth.py
│   │   │   ├── projects.py
│   │   │   ├── datasets.py
│   │   │   └── analysis.py
│   │   └── services/
│   │       ├── preprocessing.py   # QC + normalization
│   │       ├── dimensionality.py  # PCA, UMAP, t-SNE
│   │       ├── clustering.py      # K-Means + auto-k
│   │       ├── markers.py         # Welch t-test + log2FC
│   │       ├── demo_data.py       # Negative-binomial synthetic data
│   │       └── runner.py          # Orchestrator (BackgroundTask)
│   ├── data/                 # SQLite database (created on first run)
│   ├── uploads/              # User-uploaded CSVs (created on first run)
│   ├── storage/              # Result JSON blobs (created on first run)
│   └── requirements.txt
├── frontend/
│   ├── index.html            # Landing page
│   ├── login.html
│   ├── register.html
│   ├── dashboard.html        # Project list
│   ├── project.html          # Project detail (datasets + runs)
│   ├── analysis.html         # Run results (tabs + charts)
│   ├── css/styles.css
│   └── js/
│       ├── api.js            # Fetch wrapper, JWT injection, ApiError
│       └── charts.js         # Plotly renderers + Charts namespace
├── docs/
│   ├── ARCHITECTURE.md
│   ├── API.md
│   └── USER_GUIDE.md
├── run.sh                    # Convenience startup script
└── README.md                 # This file
```

## Highlights for evaluation

- **Separation of concerns.** Routes do HTTP, services do science, models do storage. Each service module is independently testable and importable without FastAPI.
- **Asynchronous execution.** Long-running pipelines are queued via `BackgroundTasks` and stream their progress through database polling — the UI shows live progress bars without blocking the request thread.
- **Audit trail.** Every step of every run writes a timestamped log entry, viewable per-run in the UI.
- **Reproducibility.** Every run stores its full parameter dictionary; re-running with the same parameters produces identical results (random seeds fixed).
- **Authorization.** Every protected endpoint validates that the requesting user owns the resource before responding — no IDOR vulnerabilities.
- **Graceful degradation.** UMAP gracefully falls back to t-SNE if `umap-learn` is missing; large files are streamed in 1 MB chunks with a hard 100 MB cap.
- **Type safety.** Pydantic v2 validates every request body; SQLAlchemy 2.0 `Mapped[]` columns provide static type information throughout the data layer.
- **Visual design.** Custom CSS design system with semantic colour tokens, a dark "scientific instrument" aesthetic distinct from the original Streamlit prototype, and a reusable Plotly theme.

## Further reading

- `docs/ARCHITECTURE.md` — system diagram, data flow, design decisions
- `docs/API.md` — complete reference for all HTTP endpoints
- `docs/USER_GUIDE.md` — researcher-facing walkthrough

## License

This codebase is submitted as academic coursework for the BS Bioinformatics Final Year Project. Redistribution outside the scope of evaluation is not granted.
