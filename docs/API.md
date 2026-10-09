# HTTP API reference

Base URL: `http://localhost:8000`

Auto-generated interactive docs are available at `/docs` (Swagger UI) and `/redoc` while the server is running. This document is a hand-curated companion that explains semantics and gives concrete examples.

## Conventions

- All request and response bodies are JSON unless otherwise stated.
- Authenticated endpoints require an `Authorization: Bearer <token>` header.
- All timestamps are ISO 8601 strings in UTC.
- Error responses use `{ "detail": "..." }` (string) for simple errors or `{ "detail": [...] }` (Pydantic validation list) for malformed bodies.
- Resource ownership violations return **404 Not Found**, not 403, to avoid leaking which IDs exist.

## Endpoint summary

| Method   | Path                                            | Purpose                            | Auth |
| -------- | ----------------------------------------------- | ---------------------------------- | ---- |
| `GET`    | `/api/health`                                   | Liveness probe                     | no   |
| `POST`   | `/api/auth/register`                            | Create account + return token      | no   |
| `POST`   | `/api/auth/login`                               | Exchange credentials for token     | no   |
| `GET`    | `/api/auth/me`                                  | Current user info                  | yes  |
| `GET`    | `/api/projects`                                 | List my projects                   | yes  |
| `POST`   | `/api/projects`                                 | Create a project                   | yes  |
| `GET`    | `/api/projects/{id}`                            | Get a project                      | yes  |
| `PATCH`  | `/api/projects/{id}`                            | Rename / re-describe               | yes  |
| `DELETE` | `/api/projects/{id}`                            | Cascade-delete a project           | yes  |
| `GET`    | `/api/projects/{pid}/datasets`                  | List datasets in a project         | yes  |
| `POST`   | `/api/projects/{pid}/datasets/upload`           | Upload a CSV (multipart)           | yes  |
| `POST`   | `/api/projects/{pid}/datasets/demo`             | Generate a synthetic dataset       | yes  |
| `GET`    | `/api/datasets/{id}`                            | Get one dataset                    | yes  |
| `DELETE` | `/api/datasets/{id}`                            | Cascade-delete a dataset           | yes  |
| `POST`   | `/api/analysis`                                 | Queue a new analysis run           | yes  |
| `GET`    | `/api/projects/{pid}/analysis`                  | List runs in a project             | yes  |
| `GET`    | `/api/analysis/{run_id}`                        | Run status / progress              | yes  |
| `GET`    | `/api/analysis/{run_id}/logs`                   | Audit trail                        | yes  |
| `GET`    | `/api/analysis/{run_id}/results`                | Full pipeline output               | yes  |
| `DELETE` | `/api/analysis/{run_id}`                        | Delete a run                       | yes  |

---

## Authentication

### `POST /api/auth/register`

Register a new account. Returns a JWT immediately so the client does not need a second round-trip to log in.

**Request**
```json
{
  "username":  "alice",
  "email":     "alice@uni.edu.pk",
  "password":  "demo1234",
  "full_name": "Alice Researcher"
}
```

Constraints: `username` 3-32 chars, `password` minimum 8 chars, `email` must be a valid email.

**Response (201)**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type":   "bearer",
  "user": {
    "id":         1,
    "username":   "alice",
    "email":      "alice@uni.edu.pk",
    "full_name":  "Alice Researcher",
    "created_at": "2026-06-01T12:00:00"
  }
}
```

### `POST /api/auth/login`

OAuth2 password grant. Body is `application/x-www-form-urlencoded`, not JSON.

**Form fields**
```
username=alice
password=demo1234
```

`username` may alternatively be the user's email address.

**Response (200)** — same `Token` shape as register.

### `GET /api/auth/me`

Returns the current user. Useful for the frontend to populate the avatar pill on every page load.

**Response (200)**
```json
{
  "id": 1,
  "username": "alice",
  "email": "alice@uni.edu.pk",
  "full_name": "Alice Researcher",
  "created_at": "2026-06-01T12:00:00"
}
```

---

## Projects

### `GET /api/projects`

Returns the calling user's projects ordered by `updated_at` descending. Each entry includes denormalised counts of attached datasets and runs.

**Response (200)**
```json
[
  {
    "id": 1,
    "name": "PBMC benchmark",
    "description": "K-Means baseline on 3k PBMCs",
    "owner_id": 1,
    "created_at": "2026-06-01T10:00:00",
    "updated_at": "2026-06-01T11:30:00",
    "n_datasets": 2,
    "n_runs": 4
  }
]
```

### `POST /api/projects`

**Request**
```json
{ "name": "PBMC benchmark", "description": "Optional text" }
```

**Response (201)** — single `ProjectOut`.

### `GET /api/projects/{id}`

Returns a single project. **404** if the project does not exist or is owned by another user.

### `PATCH /api/projects/{id}`

Partial update. Both fields are optional.

**Request**
```json
{ "name": "New name", "description": "New description" }
```

**Response (200)** — updated `ProjectOut`.

### `DELETE /api/projects/{id}`

Cascade-deletes the project, all its datasets, all their analysis runs, and all log entries.

**Response (200)** — `{ "message": "Project deleted" }`.

---

## Datasets

A dataset is a single gene-expression matrix stored on disk. There are two ways to create one: upload a CSV, or generate a synthetic dataset on the server.

### `GET /api/projects/{pid}/datasets`

**Response (200)**
```json
[
  {
    "id": 1,
    "project_id": 1,
    "filename": "pbmc_3k.csv",
    "n_cells": 2700,
    "n_genes": 13714,
    "sparsity": 0.92,
    "file_size_bytes": 38205441,
    "uploaded_at": "2026-06-01T10:15:00"
  }
]
```

### `POST /api/projects/{pid}/datasets/upload`

Multipart upload. The file is streamed to disk in 1 MB chunks; the upload is rejected with **413** if it exceeds 100 MB. CSV must have cells in rows and genes in columns. The first column may be a cell-id index; non-numeric columns are dropped at analysis time.

**Form fields**: `file=<binary>`

**Response (201)** — `DatasetOut`.

### `POST /api/projects/{pid}/datasets/demo`

Generates a synthetic dataset using a negative-binomial count model with planted cluster structure. Useful for benchmarking the pipeline.

**Query parameters** (all optional, with sensible defaults):

| Parameter    | Default | Range      | Meaning                              |
| ------------ | ------- | ---------- | ------------------------------------ |
| `n_cells`    | 300     | 50-10000   | Number of synthetic cells            |
| `n_genes`    | 800     | 50-20000   | Number of synthetic genes            |
| `n_clusters` | 4       | 2-20       | Number of planted ground-truth groups|

Example:
```
POST /api/projects/1/datasets/demo?n_cells=500&n_genes=1000&n_clusters=5
```

**Response (201)** — `DatasetOut`.

### `GET /api/datasets/{id}`

Returns one `DatasetOut`. 404 if not yours.

### `DELETE /api/datasets/{id}`

Cascade-deletes the dataset, its file on disk, and any analysis runs that reference it. 200 with `{ "message": "..." }`.

---

## Analysis

### `POST /api/analysis`

Queues a new analysis run. The endpoint returns immediately with **202 Accepted**; the work happens in a `BackgroundTask`.

**Request**
```json
{
  "dataset_id": 1,
  "name": "K-Means baseline",
  "parameters": {
    "min_genes_per_cell": 150,
    "min_cells_per_gene": 3,
    "n_pca_components":   50,
    "n_clusters":         null,
    "umap_n_neighbors":   15,
    "umap_min_dist":      0.1,
    "tsne_perplexity":    30,
    "n_marker_genes":     15
  }
}
```

Setting `n_clusters` to `null` triggers automatic elbow-method selection. All other parameters have safe defaults — the entire `parameters` block can be omitted.

**Response (202)** — `AnalysisRunOut` with `status: "pending"` (transitions to `"running"` within milliseconds).

### `GET /api/projects/{pid}/analysis`

List of `AnalysisRunOut` ordered by `created_at` descending. Each row includes denormalised summary metrics (n_cells_qc, n_clusters, variance_explained) once the run completes, allowing the list view to display them without loading the full result blob.

### `GET /api/analysis/{run_id}`

Single run. Poll this endpoint to watch `status` and `progress` change while the pipeline runs.

**Response (200)**
```json
{
  "id": 1,
  "project_id": 1,
  "dataset_id": 1,
  "name": "K-Means baseline",
  "parameters": { ... },
  "status": "running",
  "progress": 55,
  "current_step": "UMAP projection",
  "error_message": null,
  "n_cells_qc": null,
  "n_genes_qc": null,
  "n_clusters": null,
  "variance_explained": null,
  "created_at": "2026-06-01T10:30:00",
  "completed_at": null
}
```

Status transitions: `pending → running → (completed | failed)`. Summary fields populate when status becomes `completed`.

### `GET /api/analysis/{run_id}/logs?limit=200`

Returns the run's audit trail. `limit` is optional (default 200, max 1000).

**Response (200)**
```json
[
  { "timestamp": "2026-06-01T10:30:00.123",
    "level": "info",
    "message": "Loading dataset: pbmc_3k.csv" },
  { "timestamp": "2026-06-01T10:30:00.456",
    "level": "info",
    "message": "Loaded matrix: 2700 cells × 13714 genes" }
]
```

`level` is one of `"info"`, `"warn"`, `"error"`.

### `GET /api/analysis/{run_id}/results`

Full pipeline output. Only returns 200 once status is `completed`; returns 409 if the run is still in progress or has failed.

**Response (200)**
```json
{
  "run": { ...AnalysisRunOut... },
  "qc": {
    "cells_input": 2700,
    "cells_after_qc": 2638,
    "genes_input": 13714,
    "genes_after_qc": 1842,
    "cells_filtered": 62,
    "genes_filtered": 11872,
    "sparsity_pct": 92.4,
    "median_genes_per_cell": 882.0,
    "median_counts_per_cell": 2310.5
  },
  "pca": {
    "n_components": 50,
    "variance_ratio":     [0.082, 0.061, ...],
    "cumulative_variance":[0.082, 0.143, ...],
    "embedding_2d":       [[1.23, -0.45], ...]
  },
  "umap":    { "method": "UMAP",   "coords": [[x, y], ...] },
  "tsne":    { "method": "t-SNE",  "coords": [[x, y], ...] },
  "clusters": {
    "labels":       [0, 2, 1, 0, ...],
    "n_clusters":   5,
    "inertia":      4823.1,
    "silhouette":   0.42,
    "distribution": { "0": 612, "1": 580, "2": 491, "3": 470, "4": 485 }
  },
  "markers": {
    "Cluster_0": [
      { "gene": "MS4A1",
        "log_fc": 2.84,
        "p_value": 1.2e-45,
        "mean_in": 38.4, "mean_out": 5.3,
        "pct_in": 96.5,  "pct_out": 12.3,
        "trend": "increasing" },
      ...
    ],
    "Cluster_1": [ ... ]
  },
  "logs": [ {timestamp, level, message}, ... ]
}
```

### `DELETE /api/analysis/{run_id}`

Removes the run row, its log entries, and the result JSON file on disk.

---

## Error responses

| Status | Meaning                                                                 |
| ------ | ----------------------------------------------------------------------- |
| 400    | Logical / business rule failure (e.g. duplicate username)               |
| 401    | Missing or expired token                                                |
| 404    | Resource missing, **or** owned by someone else                          |
| 409    | Run not yet completed when results requested                            |
| 413    | Upload exceeded 100 MB                                                  |
| 422    | Pydantic validation failed (malformed body or out-of-range parameter)   |
| 500    | Unhandled server error (logged with traceback)                          |

A typical 422 looks like:
```json
{
  "detail": [
    {
      "type": "string_too_short",
      "loc": ["body", "password"],
      "msg": "String should have at least 8 characters",
      "input": "abc"
    }
  ]
}
```

## Try it

The interactive Swagger UI at `http://localhost:8000/docs` lets you authorise with a JWT (click the "Authorize" button, paste the token, submit) and then fire any request from the browser. ReDoc is also available at `/redoc` for a cleaner read-only view.
