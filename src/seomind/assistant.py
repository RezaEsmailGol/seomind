from __future__ import annotations

import asyncio
from datetime import date, datetime, timedelta
from typing import Any

from seomind.analyzer import analyze_opportunities, build_summary
from seomind.config import settings
from seomind.gsc import GSCError, SearchConsoleClient, gsc
from seomind.ollama import OllamaClient, ollama
from seomind.storage import LocalStorage, storage
from seomind.technical import TechnicalAuditError, TechnicalAuditService, technical_auditor


class AssistantError(RuntimeError):
    pass


def _pct(value: float | None) -> float:
    return round(float(value or 0), 1)


def _classify_health(summary: dict[str, Any], technical: dict[str, Any], opportunities: list[dict[str, Any]]) -> tuple[int, str]:
    score = 100
    click_delta = summary.get("delta", {}).get("clicks")
    impression_delta = summary.get("delta", {}).get("impressions")
    if click_delta is not None:
        if click_delta <= -30:
            score -= 30
        elif click_delta <= -15:
            score -= 20
        elif click_delta <= -7:
            score -= 10
        elif click_delta >= 15:
            score += 3

    if impression_delta is not None and impression_delta <= -20:
        score -= 10

    tech_summary = technical.get("summary", {})
    score -= min(25, int(tech_summary.get("pages_with_errors", 0)) * 5)
    score -= min(12, int(tech_summary.get("pages_with_query_mismatch", 0)) * 2)

    high_opportunities = sum(1 for item in opportunities if int(item.get("score", 0)) >= 80)
    score -= min(8, high_opportunities * 2)
    score = max(0, min(100, score))

    if score <= 45:
        status = "critical"
    elif score <= 70:
        status = "attention"
    elif (_pct(click_delta) >= 8 or _pct(impression_delta) >= 10) and int(tech_summary.get("pages_with_errors", 0)) == 0:
        status = "growing"
    else:
        status = "stable"
    return score, status


def _deterministic_brief(
    *,
    site_url: str,
    summary: dict[str, Any],
    technical: dict[str, Any],
    opportunities: list[dict[str, Any]],
) -> dict[str, Any]:
    alerts: list[dict[str, str]] = []
    ideas: list[dict[str, str]] = []
    focus: list[str] = []

    delta = summary.get("delta", {})
    click_delta = delta.get("clicks")
    impression_delta = delta.get("impressions")
    if click_delta is not None and click_delta <= -10:
        alerts.append({
            "title": "Clicks declined",
            "evidence": f"Clicks changed {_pct(click_delta)}% versus the previous 7-day period.",
            "priority": "high" if click_delta <= -20 else "medium",
        })
        focus.append("Review the pages and queries responsible for the click decline.")
    if impression_delta is not None and impression_delta <= -10:
        alerts.append({
            "title": "Search visibility declined",
            "evidence": f"Impressions changed {_pct(impression_delta)}% versus the previous 7-day period.",
            "priority": "medium",
        })

    tech = technical.get("summary", {})
    errors = int(tech.get("pages_with_errors", 0))
    mismatch = int(tech.get("pages_with_query_mismatch", 0))
    if errors:
        alerts.append({
            "title": "Technical errors need attention",
            "evidence": f"{errors} crawled pages contain at least one technical error.",
            "priority": "high",
        })
        focus.append("Fix high-severity technical errors before lower-impact content changes.")
    if mismatch:
        alerts.append({
            "title": "Search intent and page content are misaligned",
            "evidence": f"{mismatch} pages have high-impression queries with weak Title/H1/body alignment.",
            "priority": "medium",
        })

    for item in opportunities[:5]:
        kind = item.get("kind")
        query = str(item.get("query", ""))
        page = str(item.get("page", ""))
        metrics = item.get("metrics", {})
        if kind == "low_ctr":
            ideas.append({
                "title": f"Improve CTR for: {query}",
                "evidence": f"Position {float(metrics.get('position', 0)):.1f}, CTR {float(metrics.get('ctr', 0)) * 100:.2f}%, impressions {int(metrics.get('impressions', 0))}.",
                "action": f"Rewrite the title/meta around the actual query intent on {page}.",
                "confidence": "high",
            })
        elif kind == "striking_distance":
            ideas.append({
                "title": f"Push a near-page-one query upward: {query}",
                "evidence": f"Average position {float(metrics.get('position', 0)):.1f} with {int(metrics.get('impressions', 0))} impressions.",
                "action": f"Strengthen the page section matching this query and add relevant internal links to {page}.",
                "confidence": "high",
            })
        elif kind == "decay":
            ideas.append({
                "title": f"Recover declining query: {query}",
                "evidence": f"Clicks fell about {float(metrics.get('click_loss_pct', 0)):.1f}% versus the prior period.",
                "action": f"Review freshness, SERP intent and lost query coverage on {page}.",
                "confidence": "medium",
            })
        elif kind == "cannibalization":
            ideas.append({
                "title": f"Review possible cannibalization: {query}",
                "evidence": "Multiple pages receive impressions for the same query.",
                "action": "Compare intent, consolidate overlap or clarify internal linking and page targeting.",
                "confidence": "medium",
            })

    for page in technical.get("pages", []):
        for match in page.get("query_matches", [])[:3]:
            if float(match.get("impressions", 0)) >= 100 and int(match.get("score", 100)) < 40:
                ideas.append({
                    "title": f"Align page content with: {match.get('query', '')}",
                    "evidence": f"{int(match.get('impressions', 0))} impressions but only {int(match.get('score', 0))}/100 content match.",
                    "action": f"Update Title/H1/relevant section on {page.get('url', '')} using the missing concepts naturally.",
                    "confidence": "high",
                })
                break
        if len(ideas) >= 5:
            break

    if not focus:
        focus.append("Review the top opportunity with the highest deterministic score.")
    if mismatch:
        focus.append("Improve one high-impression page with weak query-to-content alignment.")
    elif ideas:
        focus.append("Implement one evidence-backed growth idea and measure it in the next daily checks.")
    if len(focus) < 3:
        focus.append("Keep the selected site's technical errors at zero while monitoring 7-day Search Console trends.")

    headline = "Site needs attention" if alerts else "Site is stable; growth opportunities are available"
    return {
        "headline": headline,
        "summary": f"Daily SeoMind review for {site_url}. The brief is based on Search Console changes, the local technical crawl and deterministic opportunity rules.",
        "alerts": alerts[:5],
        "growth_ideas": ideas[:5],
        "focus_today": focus[:3],
        "source": "deterministic",
    }


class DailyAssistant:
    def __init__(
        self,
        *,
        search_console: SearchConsoleClient = gsc,
        technical: TechnicalAuditService = technical_auditor,
        local_ai: OllamaClient = ollama,
        store: LocalStorage = storage,
    ) -> None:
        self.gsc = search_console
        self.technical = technical
        self.ollama = local_ai
        self.store = store
        self._lock = asyncio.Lock()

    async def check_site(self, site_url: str, *, language: str = "en") -> dict[str, Any]:
        async with self._lock:
            end = date.today() - timedelta(days=2)
            start = end - timedelta(days=6)
            previous_end = start - timedelta(days=1)
            previous_start = previous_end - timedelta(days=6)

            try:
                current_total = await self.gsc.query(site_url, start_date=start.isoformat(), end_date=end.isoformat(), max_rows=1)
                previous_total = await self.gsc.query(site_url, start_date=previous_start.isoformat(), end_date=previous_end.isoformat(), max_rows=1)
                current_rows = await self.gsc.query(
                    site_url,
                    start_date=start.isoformat(),
                    end_date=end.isoformat(),
                    dimensions=["query", "page"],
                    row_limit=10000,
                    max_rows=20000,
                )
                previous_rows = await self.gsc.query(
                    site_url,
                    start_date=previous_start.isoformat(),
                    end_date=previous_end.isoformat(),
                    dimensions=["query", "page"],
                    row_limit=10000,
                    max_rows=20000,
                )
                technical = await self.technical.run(
                    site_url,
                    days=7,
                    max_pages=settings.daily_crawl_pages,
                    gsc_max_rows=20000,
                )
            except (GSCError, TechnicalAuditError) as exc:
                raise AssistantError(str(exc)) from exc

            summary = build_summary(
                current_total[0] if current_total else None,
                previous_total[0] if previous_total else None,
            )
            opportunities = analyze_opportunities(current_rows, previous_rows, limit=12)
            health_score, status = _classify_health(summary, technical, opportunities)

            facts = {
                "site_url": site_url,
                "period": {"start": start.isoformat(), "end": end.isoformat()},
                "previous_period": {"start": previous_start.isoformat(), "end": previous_end.isoformat()},
                "search_console": summary,
                "technical_summary": technical.get("summary", {}),
                "top_opportunities": opportunities[:8],
                "top_query_content_mismatches": [
                    {
                        "url": page.get("url"),
                        "score": page.get("content_match_score"),
                        "queries": page.get("query_matches", [])[:3],
                    }
                    for page in technical.get("pages", [])
                    if page.get("content_match_score") is not None and int(page.get("content_match_score", 100)) < 50
                ][:5],
                "health_score": health_score,
                "status": status,
            }

            brief = _deterministic_brief(
                site_url=site_url,
                summary=summary,
                technical=technical,
                opportunities=opportunities,
            )
            ai_state = await self.ollama.status()
            if ai_state.get("available") and ai_state.get("models"):
                try:
                    ai_brief = await self.ollama.daily_brief(facts, language=language)
                    if ai_brief.get("summary"):
                        brief = {**brief, **ai_brief, "source": "ollama"}
                except RuntimeError:
                    pass

            report = {
                "site_url": site_url,
                "report_date": date.today().isoformat(),
                "health_score": health_score,
                "status": status,
                "facts": facts,
                "brief": brief,
            }
            report_id = self.store.save_assistant_report(
                site_url=site_url,
                report_date=report["report_date"],
                health_score=health_score,
                status=status,
                payload=report,
            )
            report["report_id"] = report_id
            return report

    async def check_all(self, *, language: str = "en") -> list[dict[str, Any]]:
        sites = self.store.list_monitored_sites(enabled_only=True)
        reports = []
        for site in sites:
            try:
                reports.append(await self.check_site(site["site_url"], language=language))
            except AssistantError as exc:
                reports.append({
                    "site_url": site["site_url"],
                    "report_date": date.today().isoformat(),
                    "health_score": 0,
                    "status": "error",
                    "error": str(exc),
                    "brief": {
                        "headline": "Daily check failed",
                        "summary": str(exc),
                        "alerts": [],
                        "growth_ideas": [],
                        "focus_today": [],
                        "source": "system",
                    },
                })
        return reports

    def latest_reports(self) -> list[dict[str, Any]]:
        return self.store.assistant_reports(limit_per_site=1)

    async def scheduler_loop(self) -> None:
        while True:
            try:
                now = datetime.now().astimezone()
                if settings.daily_check_enabled and now.hour >= settings.daily_check_hour:
                    for site in self.store.list_monitored_sites(enabled_only=True):
                        latest = self.store.latest_assistant_report(site["site_url"])
                        if not latest or latest.get("report_date") != date.today().isoformat():
                            try:
                                await self.check_site(site["site_url"], language="en")
                            except AssistantError:
                                pass
            finally:
                await asyncio.sleep(max(5, settings.daily_check_interval_minutes) * 60)


daily_assistant = DailyAssistant()
