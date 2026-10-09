# User guide

This guide walks a researcher through using SingleCellX end-to-end, from registration to interpreting an analysis run.

## Who this is for

Anyone analysing single-cell RNA-seq data who wants reproducible, audit-logged results without setting up a Python environment, Jupyter, or remembering which preprocessing step came in which order. The interface assumes general familiarity with the scRNA-seq workflow (QC → normalization → embedding → clustering → markers) but no programming knowledge.

## Starting the server

Open a terminal in the project folder and run:

```bash
./run.sh
```

You should see Uvicorn report that it is listening on `http://0.0.0.0:8000`. Open that URL in a browser. The landing page describes the platform and offers Sign in and Create account buttons.

## Step 1 — Create an account

Click **Create account** on the landing page. The form asks for four fields:

- **Full name** — displayed in the top-right user pill on every page.
- **Username** — 3-32 characters, used for sign-in.
- **Email** — must be a valid email address; also accepted as a sign-in identifier.
- **Password** — minimum 8 characters; hashed with bcrypt on the server, never stored in plain text.

You will be signed in automatically and redirected to your empty dashboard.

## Step 2 — Create a project

A project is the unit of organisation. It groups related datasets and analysis runs. Most researchers will have one project per experiment.

From the dashboard, click **+ New project**. Give it a name (e.g. *PBMC benchmark*) and an optional description (the experimental question, the source of the data, anything that helps future-you). Click **Create**.

## Step 3 — Add a dataset

A project needs at least one dataset before you can launch an analysis. Two options:

### Option A: Upload a CSV

Click **↑ Upload CSV**. The file must be:

- **Cells in rows, genes in columns.** The first column may contain cell identifiers (it will be treated as an index).
- **Numeric counts.** Non-numeric columns are silently dropped at analysis time. NaN entries are treated as zero.
- **Under 100 MB.** Larger files are rejected; consider pre-filtering or downsampling externally.

The upload is streamed to disk in 1 MB chunks, so very large files will not exhaust server memory. While the upload is in progress the **Datasets** table is locked; it refreshes when the upload completes.

### Option B: Generate a synthetic dataset

Click **⚗ Generate demo dataset**. You will be prompted for:

- **Cells** — how many cells to simulate (default 300).
- **Genes** — how many genes (default 800).
- **Ground-truth clusters** — how many sub-populations to plant (default 4).

The server samples counts from a negative-binomial distribution and up-regulates a block of genes per cluster. The resulting dataset has clear cluster structure and is useful for benchmarking the pipeline without real data — recoverable clusters and clear marker genes mean you can validate that the pipeline is operating correctly.

## Step 4 — Launch an analysis

With at least one dataset in the project, **+ New analysis** lights up. Click it. You will see a modal with three parameter sections.

### Quality control

| Parameter            | Default | What it does                                                                |
| -------------------- | ------- | --------------------------------------------------------------------------- |
| Min genes / cell     | 150     | Drop cells expressing fewer than this many genes (low-quality cells, doublets, empty droplets) |
| Min cells / gene     | 3       | Drop genes detected in fewer than this many cells (technical noise, rare transcripts)         |

Raise these for noisier libraries; lower them for small datasets.

### Dimensionality reduction

| Parameter        | Default | What it does                                                              |
| ---------------- | ------- | ------------------------------------------------------------------------- |
| PCA components   | 50      | Number of principal components retained for denoising and downstream use  |
| UMAP neighbors   | 15      | Local neighbourhood size for UMAP (larger = more global structure)        |
| UMAP min_dist    | 0.1     | How tightly UMAP packs points; smaller = tighter clusters                 |
| t-SNE perplexity | 30      | Effective neighbour count for t-SNE (a rough lower bound is √n_cells)     |

If `umap-learn` is unavailable on the server, the UMAP embedding silently falls back to t-SNE with the same coordinate format; the chart title in the results will indicate "UMAP (t-SNE fallback)".

### Clustering & markers

| Parameter                 | Default | What it does                                                          |
| ------------------------- | ------- | --------------------------------------------------------------------- |
| Clusters (k)              | (auto)  | Force a specific K-Means k. Leave empty to use elbow-method auto-k.   |
| Marker genes per cluster  | 15      | How many top markers to retain per cluster after filtering            |

Auto-k computes WCSS (within-cluster sum of squares) for k=2..10, finds the elbow via the discrete second derivative, and falls back to k = max_k/2 if no clear elbow is found.

Give the run a memorable name (e.g. *K-Means baseline*, *k=8 forced*, *strict QC*) and click **▶ Run pipeline**. The modal closes; the new run appears in the **Analysis runs** table with status `pending` and progress 0%.

## Step 5 — Watch progress

The project page polls the server every 2 seconds while any run is `pending` or `running`. You'll see the status pill change colour (amber → cyan → lime), the progress bar fill, and the current step text update from "Loading data" through "Quality control & normalization", "PCA", "UMAP projection", "t-SNE projection", "Clustering", "Marker gene identification" to "Done".

Synthetic datasets of a few hundred cells complete in 1-2 seconds. Real datasets of a few thousand cells typically complete in 10-60 seconds, dominated by UMAP and t-SNE.

You may navigate away — close the tab, sign out, restart the server even — and the run will continue (BackgroundTasks persist for the lifetime of the server process). Come back later and the run will show `completed` with full results available.

## Step 6 — Interpret the results

Click any completed run to open the results page. The header shows the summary metrics at a glance: cells retained after QC, clusters detected, total variance explained by PCA, silhouette score, marker count, and matrix sparsity. Below the header, five tabs organise the full output:

### Overview tab

- **PCA variance explained chart.** Bars show per-component variance (left axis, %); the line shows cumulative variance (right axis, %). A typical "elbow" indicates how many components capture most of the signal.
- **Cluster distribution bar chart.** Number of cells in each detected cluster. Highly unbalanced bars may indicate either real biological imbalance or a poorly chosen k.
- **QC table.** Side-by-side input vs. output cell and gene counts, sparsity, and median library statistics. Use this to verify the filters did roughly what you expected.

### Projections tab

- **UMAP and t-SNE scatter plots.** Each cell is one point, coloured by its assigned cluster. UMAP and t-SNE serve as visual cross-checks of each other — if both methods produce the same cluster structure, you can have more confidence in it. Plotly's pan, zoom, and hover are all available; hover shows the cell index and its 2-D coordinates.
- **Cluster legend.** Cluster id, swatch colour, and cell count.

### Marker genes tab

- **Volcano plot.** Each point is one gene-cluster combination, positioned by log₂ fold change (x) and −log₁₀(p-value) (y). Dashed lines show the significance thresholds: p = 0.05 (horizontal) and |log₂ FC| = 0.5 (vertical). Hover any point to see the gene name. Genes in the upper-right corner are highly significant and strongly upregulated — these are the strongest candidate markers.
- **Per-cluster marker tables.** For each cluster, the top markers ranked by log₂ FC. Columns: gene, log₂ FC, p-value (scientific notation when very small), percent of in-cluster cells expressing the gene, percent of out-cluster cells expressing the gene, and a coarse "trend" tag (increasing / decreasing / stable based on within-cluster sorted expression correlation).

### Logs tab

The complete server-side log for the run, with timestamps and severity colour-coding. Useful for diagnosing failed runs and for satisfying audit requirements ("can you prove which preprocessing your figure used?").

### Parameters tab

The exact parameter dictionary that was used. Copy these into a new run to reproduce the result, or share them with a collaborator who wants to replicate your analysis.

## Step 7 — Export

The **↓ Export JSON** button on the results page downloads the entire result payload — embeddings, marker tables, logs, parameters — as a single JSON file. This is the same payload returned by `GET /api/analysis/{id}/results`; it is suitable for ingesting into a Jupyter notebook, an R script, or a supplementary file for a paper.

## Tips and gotchas

- **The first analysis after a fresh install is slow.** This is `numba` JIT-compiling parts of `umap-learn`. Subsequent runs reuse the compiled code and are much faster.
- **Auto-k stops at k = 10.** If your data has more than ten populations, set k manually.
- **The silhouette score is computed on a sample.** For datasets larger than 2,000 cells it uses a random 2,000-cell subsample for tractability; the value is therefore approximate.
- **Genes filtered out of QC never appear as markers.** A high "min cells per gene" can silently drop genuine rare-cell markers.
- **CSV upload assumes counts.** If you upload an already-normalised matrix, the second normalization step inside the pipeline will distort it. Re-run the analysis on raw counts instead.
- **Deleting a project is permanent.** It cascades to every dataset and run inside; there is no soft-delete or undo.

## Getting help

The interactive API reference at `http://localhost:8000/docs` (Swagger UI) lets you inspect every endpoint and try calls live. For internal architecture see `docs/ARCHITECTURE.md`; for endpoint contracts see `docs/API.md`.
