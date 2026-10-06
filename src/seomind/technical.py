from __future__ import annotations

from collections import Counter, defaultdict
from datetime import date, timedelta
from typing import Any

from seomind.content_match import attach_query_matches
from seomind.crawler import CrawlError, PropertyScope, TechnicalCrawler
from seomind.gsc import GSCError, SearchConsoleClient, gsc
from seomind.storage import LocalStorage, storage


class TechnicalAuditError(RuntimeError):
    pass


def _seed_urls_from_gsc(site_url: str, rows: list[dict[str, Any]], max_pages: int) -> list[str]:
    scope = PropertyScope(site_url)
    impressions_by_page: dict[str, float] = defaultdict(float)
    for row in rows:
        keys = row.get("keys") or []
        if len(keys) < 2:
            continue
        page = str(keys[0])
        if scope.allows(page):
            impressions_by_page[page] += float(row.get("impressions", 0) or 0)
    ranked = sorted(impressions_by_page.items(), key=lambda item: item[1], reverse=True)
    return [url for url, _ in ranked[: max(max_pages * 2, 20)]]


def summarize_pages(pages: list[dict[str, Any]]) -> dict[str, Any]:
    issue_counts: Counter[str] = Counter()
    severity_counts: Counter[str] = Counter()
    scores = []
    html_pages = 0
    for page in pages:
        if "html" in str(page.get("content_type", "")).lower():
            html_pages += 1
        if isinstance(page.get("technical_score"), (int, float)):
            scores.append(float(page["technical_score"]))
        for issue in page.get("issues", []) or []:
            issue_counts[str(issue.get("code", "unknown"))] += 1
            severity_counts[str(issue.get("severity", "info"))] += 1

    return {
        "pages_crawled": len(pages),
        "html_pages": html_pages,
        "average_score": round(sum(scores) / len(scores), 1) if scores else 0,
        "healthy_pages": sum(1 for page in pages if float(page.get("technical_score", 0)) >= 85),
        "pages_with_errors": sum(
            1 for page in pages if any(issue.get("severity") == "error" for issue in page.get("issues", []))
        ),
        "pages_with_query_mismatch": issue_counts.get("query_content_mismatch", 0),
        "missing_title": issue_counts.get("missing_title", 0),
        "missing_h1": issue_counts.get("missing_h1", 0),
        "missing_canonical": issue_counts.get("missing_canonical", 0),
        "noindex": issue_counts.get("noindex", 0),
        "issue_counts": dict(issue_counts.most_common()),
        "severity_counts": dict(severity_counts),
    }


class TechnicalAuditService:
    def __init__(
        self,
        *,
        search_console: SearchConsoleClient = gsc,
        store: LocalStorage = storage,
    ) -> None:
        self.gsc = search_console
        self.store = store

    async def run(
        self,
        site_url: str,
        *,
        days: int = 28,
        max_pages: int = 50,
        gsc_max_rows: int = 50000,
    ) -> dict[str, Any]:
        end = date.today() - timedelta(days=2)
        start = end - timedelta(days=days - 1)

        try:
            gsc_rows = await self.gsc.query(
                site_url,
                start_date=start.isoformat(),
                end_date=end.isoformat(),
                dimensions=["page", "query"],
                row_limit=25000,
                max_rows=gsc_max_rows,
            )
            seed_urls = _seed_urls_from_gsc(site_url, gsc_rows, max_pages)
            crawler = TechnicalCrawler(site_url)
            crawl_result = await crawler.crawl(seed_urls=seed_urls, max_pages=max_pages)
        except (GSCError, CrawlError) as exc:
            raise TechnicalAuditError(str(exc)) from exc

        pages = attach_query_matches(crawl_result["pages"], gsc_rows)
        pages = sorted(
            pages,
            key=lambda page: (
                int(page.get("technical_score", 0)),
                -sum(float(item.get("impressions", 0)) for item in page.get("query_matches", [])),
            ),
        )

        result: dict[str, Any] = {
            "site_url": site_url,
            "period": {"start": start.isoformat(), "end": end.isoformat(), "days": days},
            "sitemaps": crawl_result["sitemaps"],
            "sitemap_url_count": crawl_result["sitemap_url_count"],
            "gsc_rows_analyzed": len(gsc_rows),
            "summary": summarize_pages(pages),
            "pages": pages,
        }
        audit_id = self.store.save_technical_audit(
            site_url=site_url,
            start_date=start.isoformat(),
            end_date=end.isoformat(),
            page_count=len(pages),
            payload=result,
        )
        result["technical_audit_id"] = audit_id
        return result


technical_auditor = TechnicalAuditService()
