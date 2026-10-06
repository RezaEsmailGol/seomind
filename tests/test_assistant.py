from pathlib import Path

from seomind.assistant import _classify_health, _deterministic_brief
from seomind.storage import LocalStorage


def test_health_classification_detects_attention():
    summary = {"delta": {"clicks": -22.0, "impressions": -12.0}}
    technical = {"summary": {"pages_with_errors": 2, "pages_with_query_mismatch": 1}}
    score, status = _classify_health(summary, technical, [])
    assert score < 71
    assert status in {"attention", "critical"}


def test_growth_brief_uses_evidence():
    summary = {"delta": {"clicks": -15.0, "impressions": 2.0}}
    technical = {"summary": {"pages_with_errors": 0, "pages_with_query_mismatch": 0}, "pages": []}
    opportunities = [{
        "kind": "low_ctr",
        "query": "odoo developer",
        "page": "https://example.com/odoo",
        "metrics": {"position": 8.4, "ctr": 0.012, "impressions": 4820},
    }]
    brief = _deterministic_brief(
        site_url="https://example.com/",
        summary=summary,
        technical=technical,
        opportunities=opportunities,
    )
    assert brief["alerts"]
    assert brief["growth_ideas"]
    assert "4820" in brief["growth_ideas"][0]["evidence"]


def test_monitored_sites_and_reports_are_persisted(tmp_path: Path):
    store = LocalStorage(tmp_path)
    store.upsert_monitored_site("https://example.com/", label="Example")
    sites = store.list_monitored_sites(enabled_only=True)
    assert sites[0]["label"] == "Example"

    store.save_assistant_report(
        site_url="https://example.com/",
        report_date="2026-10-06",
        health_score=88,
        status="stable",
        payload={
            "site_url": "https://example.com/",
            "report_date": "2026-10-06",
            "health_score": 88,
            "status": "stable",
            "brief": {"headline": "Stable"},
        },
    )
    latest = store.latest_assistant_report("https://example.com/")
    assert latest is not None
    assert latest["health_score"] == 88
    assert latest["brief"]["headline"] == "Stable"
