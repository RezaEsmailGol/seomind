from fastapi import FastAPI

from seomind import __version__
from seomind.config import settings

settings.ensure_directories()

app = FastAPI(
    title="SeoMind API",
    version=__version__,
    description="Local-first AI SEO intelligence for Google Search Console.",
)


@app.get("/")
def root() -> dict[str, str]:
    return {
        "name": "SeoMind",
        "version": __version__,
        "status": "running",
        "docs": "/docs",
        "health": "/health",
    }


@app.get("/health")
def health() -> dict[str, str | bool]:
    return {
        "ok": True,
        "service": "seomind",
        "version": __version__,
    }


@app.get("/api/setup/status")
def setup_status() -> dict[str, object]:
    return {
        "ready": True,
        "steps": {
            "runtime": True,
            "local_storage": settings.data_dir.exists(),
            "google_oauth": False,
            "search_console": False,
            "ollama": False,
        },
        "next": "google_oauth",
    }
