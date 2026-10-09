"""
SingleCellX FYP — FastAPI application entry point.

This module:
1. Instantiates the FastAPI app and configures CORS + static files.
2. Initializes the SQLite database on startup.
3. Mounts all API routers.
4. Serves the frontend single-page-application from /.
"""
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from fastapi.exceptions import RequestValidationError

from .config import settings
from .database import init_db
from .routes import auth as auth_routes
from .routes import projects as projects_routes
from .routes import datasets as datasets_routes
from .routes import analysis as analysis_routes
from .routes import export as export_routes


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description=(
        "REST API for single-cell RNA-seq analysis. Endpoints cover "
        "authentication, project management, dataset upload, and the full "
        "analysis pipeline (QC → PCA → UMAP/t-SNE → clustering → markers)."
    ),
)

# -----------------------------------------------------------
# CORS
# -----------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -----------------------------------------------------------
# Lifespan / startup
# -----------------------------------------------------------
@app.on_event("startup")
def on_startup() -> None:
    init_db()


# -----------------------------------------------------------
# API routers
# -----------------------------------------------------------
app.include_router(auth_routes.router)
app.include_router(projects_routes.router)
app.include_router(datasets_routes.router)
app.include_router(analysis_routes.router)
app.include_router(export_routes.router)


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok", "app": settings.app_name, "version": settings.app_version}


# -----------------------------------------------------------
# Frontend static hosting
# -----------------------------------------------------------
FRONTEND_DIR = Path(__file__).resolve().parent.parent.parent / "frontend"

if FRONTEND_DIR.exists():
    # Mount asset folders so the SPA can load CSS/JS
    app.mount("/css", StaticFiles(directory=FRONTEND_DIR / "css"), name="css")
    app.mount("/js", StaticFiles(directory=FRONTEND_DIR / "js"), name="js")
    app.mount("/pages", StaticFiles(directory=FRONTEND_DIR / "pages"), name="pages")

    @app.get("/", include_in_schema=False)
    def index():
        return FileResponse(FRONTEND_DIR / "index.html")

    @app.get("/{page_name}.html", include_in_schema=False)
    def page(page_name: str):
        # Serve any top-level page (login.html, dashboard.html, ...)
        candidate = FRONTEND_DIR / f"{page_name}.html"
        if candidate.exists():
            return FileResponse(candidate)
        return JSONResponse({"detail": "Not Found"}, status_code=404)
