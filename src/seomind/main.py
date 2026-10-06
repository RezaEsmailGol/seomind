from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager, suppress
from datetime import date, timedelta
from typing import Any
from urllib.parse import urlencode

import httpx
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse

from seomind import __version__
from seomind.analyzer import analyze_opportunities, build_summary, trend_points
from seomind.assistant import AssistantError, daily_assistant
from seomind.config import settings
from seomind.google_oauth import GoogleOAuthError, google_oauth
from seomind.gsc import GSCError, gsc
from seomind.ollama import ollama
from seomind.schemas import (
    AiExplainRequest,
    AssistantChatRequest,
    AssistantRunRequest,
    GoogleCredentialsPayload,
    ImportRequest,
    MonitoredSiteUpdate,
    PropertySelection,
    TechnicalAuditRequest,
    UrlInspectionRequest,
)
from seomind.storage import storage
from seomind.technical import TechnicalAuditError, technical_auditor

settings.ensure_directories()


@asynccontextmanager
async def lifespan(app: FastAPI):
    task = None
    if settings.daily_check_enabled:
        task = asyncio.create_task(daily_assistant.scheduler_loop())
    try:
        yield
    finally:
        if task:
            task.cancel()
            with suppress(asyncio.CancelledError):
                await task


app = FastAPI(
    title="SeoMind API",
    version=__version__,
    description="Local-first AI SEO intelligence for Google Search Console.",
    lifespan=lifespan,
)

allowed_origins = {
    settings.frontend_url.rstrip("/"),
    "http://localhost:3000",
    "http://127.0.0.1:3000",
}
app.add_middleware(
    CORSMiddleware,
    allow_origins=sorted(allowed_origins),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _http_error(exc: Exception, status_code: int = 400) -> HTTPException:
    return HTTPException(status_code=status_code, detail=str(exc))


@app.get("/")
def root() -> dict[str, Any]:
    return {
        "name": "SeoMind",
        "version": __version__,
        "status": "running",
        "docs": "/docs",
        "health": "/health",
    }


@app.get("/health")
def health() -> dict[str, Any]:
    return {"ok": True, "service": "seomind", "version": __version__}


@app.get("/api/setup/status")
async def setup_status() -> dict[str, Any]:
    ollama_state = await ollama.status()
    selected_property = storage.get_setting("selected_property", "") or ""
    steps = {
        "runtime": True,
        "local_storage": storage.db_path.exists(),
        "google_credentials": storage.credentials_path.exists(),
        "google_oauth": storage.token_path.exists(),
        "search_console": bool(selected_property),
        "ollama": bool(ollama_state.get("available")),
    }
    if not steps["google_credentials"]:
        next_step = "google_credentials"
    elif not steps["google_oauth"]:
        next_step = "google_oauth"
    elif not steps["search_console"]:
        next_step = "property"
    else:
        next_step = "ready"
    return {
        "ready": all([steps["runtime"], steps["local_storage"], steps["google_oauth"], steps["search_console"]]),
        "steps": steps,
        "next": next_step,
        "selected_property": selected_property or None,
        "ollama": ollama_state,
    }


@app.post("/api/google/credentials")
def save_google_credentials(payload: GoogleCredentialsPayload) -> dict[str, Any]:
    try:
        validated = google_oauth.validate_credentials(payload.credentials)
    except GoogleOAuthError as exc:
        raise _http_error(exc) from exc
    storage.save_google_credentials(validated)
    return {
        "ok": True,
        "redirect_uri": settings.oauth_redirect_uri,
        "scope": "https://www.googleapis.com/auth/webmasters.readonly",
    }


@app.get("/api/google/oauth/start")
def google_oauth_start() -> RedirectResponse:
    try:
        url = google_oauth.authorization_url()
    except GoogleOAuthError as exc:
        raise _http_error(exc) from exc
    return RedirectResponse(url, status_code=302)


@app.get("/api/google/oauth/callback")
async def google_oauth_callback(
    code: str | None = Query(default=None),
    state: str | None = Query(default=None),
    error: str | None = Query(default=None),
) -> RedirectResponse:
    if error:
        params = urlencode({"google": "error", "message": error})
        return RedirectResponse(f"{settings.frontend_url}/?{params}")
    if not code or not state:
        raise HTTPException(status_code=400, detail="Google OAuth callback is missing code/state.")
    try:
        await google_oauth.exchange_code(code, state)
    except GoogleOAuthError as exc:
        params = urlencode({"google": "error", "message": str(exc)[:180]})
        return RedirectResponse(f"{settings.frontend_url}/?{params}")
    return RedirectResponse(f"{settings.frontend_url}/?google=connected")


@app.delete("/api/google/connection")
def disconnect_google() -> dict[str, bool]:
    storage.clear_google()
    return {"ok": True}


@app.get("/api/google/properties")
async def properties() -> dict[str, Any]:
    try:
        items = await gsc.list_properties()
    except (GoogleOAuthError, GSCError) as exc:
        raise _http_error(exc, status_code=401) from exc
    return {"items": items}


@app.post("/api/google/property")
def select_property(payload: PropertySelection) -> dict[str, str]:
    storage.set_setting("selected_property", payload.site_url)
    storage.upsert_monitored_site(payload.site_url)
    return {"site_url": payload.site_url}


@app.post("/api/import/search-console")
async def import_search_console(payload: ImportRequest) -> dict[str, Any]:
    site_url = storage.get_setting("selected_property")
    if not site_url:
        raise HTTPException(status_code=400, detail="Select a Search Console property first.")

    end = date.today() - timedelta(days=2)
    start = end - timedelta(days=payload.days - 1)
    previous_end = start - timedelta(days=1)
    previous_start = previous_end - timedelta(days=payload.days - 1)

    try:
        current_totals_rows = await gsc.query(
            site_url, start_date=start.isoformat(), end_date=end.isoformat(), max_rows=1
        )
        previous_totals_rows = await gsc.query(
            site_url,
            start_date=previous_start.isoformat(),
            end_date=previous_end.isoformat(),
            max_rows=1,
        )
        trend_rows = await gsc.query(
            site_url,
            start_date=start.isoformat(),
            end_date=end.isoformat(),
            dimensions=["date"],
            max_rows=max(payload.days * 2, 100),
        )
        current_rows = await gsc.query(
            site_url,
            start_date=start.isoformat(),
            end_date=end.isoformat(),
            dimensions=["query", "page"],
            row_limit=payload.row_limit,
            max_rows=payload.max_rows,
        )
        previous_rows = await gsc.query(
            site_url,
            start_date=previous_start.isoformat(),
            end_date=previous_end.isoformat(),
            dimensions=["query", "page"],
            row_limit=payload.row_limit,
            max_rows=payload.max_rows,
        )
    except (GoogleOAuthError, GSCError) as exc:
        raise _http_error(exc, status_code=502) from exc

    result: dict[str, Any] = {
        "site_url": site_url,
        "period": {"start": start.isoformat(), "end": end.isoformat(), "days": payload.days},
        "previous_period": {
            "start": previous_start.isoformat(),
            "end": previous_end.isoformat(),
        },
        "summary": build_summary(
            current_totals_rows[0] if current_totals_rows else None,
            previous_totals_rows[0] if previous_totals_rows else None,
        ),
        "trend": trend_points(trend_rows),
        "opportunities": analyze_opportunities(current_rows, previous_rows),
        "rows_analyzed": len(current_rows),
        "data_note": "Search Console API can return top rows rather than every possible row.",
    }
    audit_id = storage.save_audit(
        site_url=site_url,
        start_date=start.isoformat(),
        end_date=end.isoformat(),
        row_count=len(current_rows),
        payload=result,
    )
    result["audit_id"] = audit_id
    return result


@app.get("/api/audits/latest")
def latest_audit() -> dict[str, Any]:
    site_url = storage.get_setting("selected_property")
    audit = storage.latest_audit(site_url=site_url or None)
    if not audit:
        raise HTTPException(status_code=404, detail="No audit has been imported yet.")
    return audit


@app.post("/api/technical-audit")
async def run_technical_audit(payload: TechnicalAuditRequest) -> dict[str, Any]:
    site_url = storage.get_setting("selected_property")
    if not site_url:
        raise HTTPException(status_code=400, detail="Select a Search Console property first.")
    try:
        return await technical_auditor.run(
            site_url,
            days=payload.days,
            max_pages=payload.max_pages,
            gsc_max_rows=payload.gsc_max_rows,
        )
    except GoogleOAuthError as exc:
        raise _http_error(exc, status_code=401) from exc
    except (GSCError, TechnicalAuditError) as exc:
        raise _http_error(exc, status_code=502) from exc


@app.get("/api/technical-audits/latest")
def latest_technical_audit() -> dict[str, Any]:
    site_url = storage.get_setting("selected_property")
    audit = storage.latest_technical_audit(site_url=site_url or None)
    if not audit:
        raise HTTPException(status_code=404, detail="No technical audit has been run yet.")
    return audit


@app.get("/api/assistant/status")
def assistant_status() -> dict[str, Any]:
    return {
        "enabled": settings.daily_check_enabled,
        "daily_hour": settings.daily_check_hour,
        "daily_language": settings.daily_language,
        "daily_crawl_pages": settings.daily_crawl_pages,
        "sites": storage.list_monitored_sites(),
        "reports": daily_assistant.latest_reports(),
    }


@app.post("/api/assistant/sites")
def update_monitored_site(payload: MonitoredSiteUpdate) -> dict[str, Any]:
    storage.upsert_monitored_site(payload.site_url, label=payload.label, enabled=payload.enabled)
    return {"sites": storage.list_monitored_sites()}


@app.post("/api/assistant/run")
async def run_assistant(payload: AssistantRunRequest) -> dict[str, Any]:
    try:
        if payload.site_url:
            storage.upsert_monitored_site(payload.site_url)
            return {"reports": [await daily_assistant.check_site(payload.site_url, language=payload.language)]}
        return {"reports": await daily_assistant.check_all(language=payload.language)}
    except AssistantError as exc:
        raise _http_error(exc, status_code=502) from exc


@app.get("/api/assistant/reports")
def assistant_reports() -> dict[str, Any]:
    return {"reports": daily_assistant.latest_reports()}


@app.post("/api/assistant/chat")
async def assistant_chat(payload: AssistantChatRequest) -> dict[str, Any]:
    site_url = payload.site_url or storage.get_setting("selected_property")
    if not site_url:
        raise HTTPException(status_code=400, detail="Select a Search Console property first.")

    report = storage.latest_assistant_report(site_url)
    performance = storage.latest_audit(site_url)
    technical = storage.latest_technical_audit(site_url)
    if not report and not performance and not technical:
        raise HTTPException(status_code=400, detail="Run at least one SeoMind audit before asking the assistant.")

    technical_context: dict[str, Any] = {}
    if technical:
        technical_context = {
            "summary": technical.get("summary", {}),
            "worst_pages": [
                {
                    "url": page.get("url"),
                    "technical_score": page.get("technical_score"),
                    "content_match_score": page.get("content_match_score"),
                    "issues": page.get("issues", [])[:5],
                    "query_matches": page.get("query_matches", [])[:3],
                }
                for page in technical.get("pages", [])[:8]
            ],
        }

    context = {
        "site_url": site_url,
        "latest_daily_report": report,
        "performance": {
            "period": performance.get("period") if performance else None,
            "summary": performance.get("summary") if performance else None,
            "top_opportunities": performance.get("opportunities", [])[:8] if performance else [],
        },
        "technical": technical_context,
    }

    try:
        return await ollama.assistant_chat(
            context=context,
            question=payload.message,
            language=payload.language,
        )
    except (RuntimeError, httpx.HTTPError) as exc:
        raise _http_error(exc, status_code=502) from exc


@app.post("/api/url-inspection")
async def inspect_url(payload: UrlInspectionRequest) -> dict[str, Any]:
    site_url = storage.get_setting("selected_property")
    if not site_url:
        raise HTTPException(status_code=400, detail="Select a Search Console property first.")
    try:
        return await gsc.inspect_url(site_url, payload.url, payload.language)
    except (GoogleOAuthError, GSCError) as exc:
        raise _http_error(exc, status_code=502) from exc


@app.get("/api/ai/status")
async def ai_status() -> dict[str, Any]:
    return await ollama.status()


@app.post("/api/ai/explain")
async def ai_explain(payload: AiExplainRequest) -> dict[str, Any]:
    try:
        return await ollama.explain(payload.opportunity, payload.language, payload.model)
    except (RuntimeError, httpx.HTTPError) as exc:
        raise _http_error(exc, status_code=502) from exc
