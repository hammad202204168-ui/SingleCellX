# Architecture

This document describes how SingleCellX is structured, why each piece exists, and how data moves through the system from a user click to a rendered chart.

---

## 1. High-level view

```
                  ┌────────────────────────────────────────────┐
                  │              Browser (the user)            │
                  │  HTML pages + Plotly.js + vanilla JS       │
                  └─────────────────┬──────────────────────────┘
                                    │  HTTPS (or HTTP in dev)
                                    │  JSON over fetch()
                                    │  JWT in Authorization header
                                    ▼
                  ┌────────────────────────────────────────────┐
                  │                FastAPI app                 │
                  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  │
                  │  │  Auth    │  │ Projects │  │ Datasets │  │
                  │  │  router  │  │  router  │  │  router  │  │
                  │  └──────────┘  └──────────┘  └──────────┘  │
                  │  ┌──────────┐    ┌─────────────────────┐   │
                  │  │ Analysis │───►│  BackgroundTasks    │   │
                  │  │  router  │    │  (in-process queue) │   │
                  │  └──────────┘    └──────────┬──────────┘   │
                  └─────────┬─────────────────┬─┘              │
                            │                 │                 │
                            │ SQLAlchemy ORM  │ pure-Python     │
                            ▼                 ▼ pipeline calls  │
                  ┌──────────────────┐  ┌─────────────────────┐ │
                  │   SQLite DB      │  │ services/ package   │ │
                  │   5 tables       │  │  preprocessing      │ │
                  │   users          │  │  dimensionality     │ │
                  │   projects       │  │  clustering         │ │
                  │   datasets       │  │  markers            │ │
                  │   analysis_runs  │  │  demo_data          │ │
                  │   log_entries    │  │  runner             │ │
                  └──────────────────┘  └──────────┬──────────┘ │
                                                   │            │
                                                   ▼            │
                                            ┌──────────────┐    │
                                            │  storage/    │    │
                                            │  run_*.json  │◄───┘
                                            └──────────────┘
```

The entire system runs as a single FastAPI process. The browser talks to it for both static assets (HTML, CSS, JS, charts) and the JSON API — there is no separate frontend server. SQLite holds metadata; large result blobs are written to flat files on disk.

---

## 2. Layered design

The backend is organized into four layers, each with a clear job:

### Layer 1 — Configuration and infrastructure (`config.py`, `database.py`)

`config.py` holds a Pydantic `Settings` object that reads from environment variables with sensible defaults. Paths (uploads, storage, database), JWT secrets, and CORS origins live here. Nothing else in the code constructs paths or reads env vars directly — everything flows through `settings`.

`database.py` constructs the SQLAlchemy engine and a `SessionLocal` factory. It exposes a `get_db()` dependency that FastAPI injects into every route, ensuring sessions are opened per-request and closed in a `finally` block. `init_db()` creates all tables on startup.

### Layer 2 — Data model (`models.py`, `schemas.py`)

`models.py` defines five SQLAlchemy 2.0 ORM classes using the typed `Mapped[]` syntax:

- **User** — username, email, hashed_password, full_name, created_at. Owns projects.
- **Project** — name, description, owner_id. Owns datasets and runs.
- **Dataset** — filename, file_path, n_cells, n_genes, sparsity, file_size_bytes. Belongs to a project.
- **AnalysisRun** — name, parameters (JSON), status, progress, current_step, error_message, result_path, summary metrics (n_cells_qc, n_genes_qc, n_clusters, variance_explained), timestamps. Belongs to a project and a dataset.
- **LogEntry** — run_id, timestamp, level, message. Append-only audit trail per run.

All relationships use `cascade="all, delete-orphan"` so deleting a project cleans up its datasets and runs, and deleting a run cleans up its log entries.

`schemas.py` defines Pydantic models for every request and response, including the strict `AnalysisParameters` validator that bounds every parameter to a safe range (e.g. `n_pca_components` is `Field(50, ge=2, le=200)`).

### Layer 3 — Authentication and routing (`auth.py`, `routes/`)

`auth.py` exposes three functions: `hash_password` (bcrypt with explicit 72-byte truncation to avoid the well-known bcrypt limit), `verify_password`, `create_access_token` (JWT signed with HS256), `decode_token`, and the FastAPI dependency `get_current_user` which reads the bearer token and resolves the User row. Every protected route depends on `get_current_user`.

Each router module under `routes/` handles one resource:

- `routes/auth.py` — POST `/api/auth/register`, POST `/api/auth/login` (OAuth2PasswordRequestForm so the SwaggerUI authorize button works), GET `/api/auth/me`.
- `routes/projects.py` — full CRUD. Helper `_owned(project_id, db, user)` returns the Project or 404s if it doesn't belong to the current user, enforcing per-row authorization in one place.
- `routes/datasets.py` — POST upload (multipart, streaming to disk, 100 MB cap), POST demo-generate, GET list, GET single, DELETE.
- `routes/analysis.py` — POST create (queues to BackgroundTasks → `runner.execute_analysis`), GET list, GET single, GET logs, GET full results, DELETE.

### Layer 4 — Scientific pipeline (`services/`)

This is where the actual single-cell analysis happens. Each module is plain Python, takes typed inputs, returns a dataclass, and has no FastAPI or SQLAlchemy imports. That isolation means each module can be unit-tested, swapped, or reused from a Jupyter notebook with no web stack involvement.

- **`preprocessing.run_qc`** filters cells expressing fewer than `min_genes_per_cell` genes, drops genes detected in fewer than `min_cells_per_gene` cells, then library-size normalizes and applies `log1p`. Returns a `QCResult` carrying the cleaned count matrix, the normalized matrix, sparsity, and median statistics.

- **`dimensionality.run_pca`** runs scikit-learn `PCA` and returns the components, variance ratio, and cumulative variance. **`run_umap`** tries `umap-learn` and falls back to t-SNE if numba isn't available. **`run_tsne`** runs scikit-learn's t-SNE directly.

- **`clustering.cluster_cells`** does k-means on PCA components. If the caller passes `n_clusters=None`, `_find_optimal_k` runs k-means for k=2..10, computes WCSS, takes the discrete second derivative, and picks the elbow. Silhouette score is computed on a 2000-cell subsample for speed.

- **`markers.find_markers`** does per-cluster differential expression: for each gene, compute mean expression inside vs outside the cluster, log2 fold change, Welch's t-test p-value, and percentage of cells expressing in vs out. Genes are filtered by `log_fc > 0.5` and `p_value < 0.05` and sorted by fold change.

- **`demo_data.create_demo_data`** generates a synthetic dataset using a negative binomial distribution with cluster-specific upregulation (3× boost on a marker gene block per cluster), useful for benchmarking the pipeline without real data.

- **`runner.execute_analysis(run_id)`** is the orchestrator. It opens its own DB session (it runs in a BackgroundTask so it can't reuse the request session), loads the run row and dataset, then walks through the pipeline. After every step it calls `_update(progress=…, current_step=…)` and `_log(message=…)` so the frontend's polling sees progress in real time. The final results dict (qc summary, pca, umap, tsne, clusters, markers, cell IDs, gene names) is written to `storage/run_{id}.json` and the run row is patched to `status="completed"`. On any exception the run is marked `failed` with the traceback in `error_message` and a corresponding log entry.

---

## 3. Frontend architecture

The frontend deliberately uses no build step. Every page is a hand-written HTML file that links the shared stylesheet and one or two JS files. The reasoning:

- **Auditability.** The supervisor can open any file in a browser, view source, and read what runs. No webpack, no transpilation.
- **Zero install.** No `npm install`, no `node_modules`, no version conflicts.
- **Speed.** The whole frontend is ~50 KB; cold-loads instantly.

Three shared modules live under `frontend/js/`:

- **`api.js`** — Thin fetch wrapper. Defines `Storage` for JWT/user in localStorage, an `ApiError` class, a single `request(method, path, opts)` function that injects the Authorization header and redirects to `/login.html` on 401, and the `Api` object exposing one method per endpoint. Also exports `requireAuth()`, `logout()`, and a `toast(msg, type)` helper.

- **`charts.js`** — Plotly renderers. Defines `CLUSTER_COLORS` (10 distinct scientific colors), a shared `DARK_LAYOUT` Plotly theme, and the rendering primitives (`renderScatter2D`, `renderClusterBar`, `renderVariance`, `renderVolcano`). The `Charts` namespace at the bottom is a thin adapter that takes the raw API result objects and unpacks them into the primitive renderers, so page code stays one-liner.

- **(no framework)** — All page state lives in a few module-level variables per page. The two long-running pages (`project.html`, `analysis.html`) use `setInterval` polling against the analysis status endpoint to surface progress.

The design system is a single CSS file using CSS custom properties for the palette (cobalt background, lime + cyan accents) and three custom font families loaded from Google Fonts. Components are BEM-ish: `.card`, `.card-title`, `.card-sub`; `.btn`, `.btn-primary`, `.btn-ghost`, `.btn-danger`, `.btn-sm`, `.btn-icon`; `.pill`, `.pill-cyan`, `.pill-lime`, `.pill-amber`, `.pill-red`, `.pill-pulse`; etc.

---

## 4. Data flow: a complete analysis run

This is what happens, step by step, when a user clicks **▶ Run pipeline**:

1. **Browser** — `project.html` validates the form, builds a JSON payload with `dataset_id`, `name`, and a `parameters` object containing all eight pipeline parameters, then calls `Api.createAnalysis(payload)`.

2. **Network** — `fetch('POST /api/analysis')` with the JWT bearer token.

3. **FastAPI router** (`routes/analysis.py`) — `get_current_user` decodes the token, looks up the User. The handler validates the payload against `AnalysisCreate` (which itself contains the bounded `AnalysisParameters` schema). It checks that the dataset belongs to a project the user owns. It inserts an `AnalysisRun` row with `status="pending"`, `progress=0`. It schedules `runner.execute_analysis(run.id)` on `BackgroundTasks`. It returns the row immediately with HTTP 202.

4. **Browser** — closes the modal, refreshes the runs table. The new row appears with status *pending*.

5. **BackgroundTask** (`runner.execute_analysis`) — opens its own DB session via `SessionLocal()`. Sets `status="running"`, `progress=2`, `current_step="Loading data"`. Reads the dataset CSV from `dataset.file_path` with pandas.

6. **QC** — calls `run_qc(...)` with the user's filter parameters. Updates `progress=15`, logs the filtered shape.

7. **PCA** — calls `run_pca(qc.normalized, n_components=...)`. Updates `progress=35`, logs the variance captured.

8. **UMAP** — calls `run_umap(pca.components, n_neighbors=..., min_dist=...)`. Updates `progress=55`. Falls back to t-SNE-as-UMAP if `umap-learn` isn't usable.

9. **t-SNE** — calls `run_tsne(pca.components, perplexity=...)`. Updates `progress=70`.

10. **Clustering** — calls `cluster_cells(pca.components, n_clusters=...)`. If `n_clusters` is None, `_find_optimal_k` runs first. Updates `progress=82`, logs silhouette score.

11. **Markers** — calls `find_markers(qc.counts, clusters.labels, top_n=...)`. Updates `progress=92`, logs total marker count.

12. **Persist** — serializes the full result dict to `settings.storage_dir / f"run_{run.id}.json"`. Updates the run row with `status="completed"`, `progress=100`, `result_path`, and all summary metrics. Logs `"Analysis complete"`.

13. **Browser polling** — meanwhile, every 2.5 seconds `project.html` has been calling `Api.listAnalyses(projectId)` because it sees an active row. When status flips to *completed*, the row gains an **Open →** link.

14. **User opens results** — clicks the row. `analysis.html` loads, calls `Api.getAnalysis(runId)`. Status is *completed*, so it calls `Api.getAnalysisResults(runId)`. The backend reads the JSON blob from disk and returns it. The frontend renders six summary cards, all charts, marker tables, and the log viewer.

The total wall-clock time on the default 300-cell synthetic demo is about 5–15 seconds depending on machine.

---

## 5. Security model

- **Passwords** are hashed with bcrypt 4.2 directly (not via passlib, which had a bug with bcrypt ≥ 4.1). Inputs longer than 72 bytes are explicitly truncated before hashing or verification.
- **JWTs** are signed with HS256 using a secret loaded from `SECRET_KEY` env var (with a development default). The token contains the user ID and expiry. There is no refresh-token flow — tokens expire after 7 days by default and the user re-logs in.
- **Authorization** is per-row. Every endpoint that touches a Project, Dataset, or AnalysisRun calls a `_owned(...)` helper that returns the row only if it belongs to the current user; otherwise 404 (never 403, to avoid leaking existence).
- **File uploads** are streamed in chunks with a hard 100 MB cap. Filenames are sanitized and the actual on-disk name uses a UUID, so users can't path-traverse.
- **CORS** is open in development. For a production deployment, restrict `allowed_origins` in `config.py`.

---

## 6. Where to extend

If you wanted to take this past FYP scope, here's where each extension would slot in cleanly:

- **Replace SQLite with Postgres** — change one line in `config.py`, install `psycopg2-binary`.
- **Replace BackgroundTasks with Celery** — change `runner.execute_analysis` from a function called by `background_tasks.add_task(...)` to a `@celery.task`. The pipeline code itself doesn't change.
- **Add Leiden clustering** — drop a new function in `services/clustering.py`, expose it via a new parameter on `AnalysisParameters`, branch in `runner.execute_analysis`.
- **Add `.h5ad` ingestion** — add a new branch in `routes/datasets.py` that detects the file extension and uses `anndata` to read it before persisting.
- **Add batch correction** — new module `services/batch_correction.py`, new parameter on `AnalysisParameters`, new step in `runner.execute_analysis` between QC and PCA.

The layered design makes each of these a localized change rather than a rewrite — which is the entire point of the architecture.
