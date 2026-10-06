from __future__ import annotations

import hashlib
from collections import defaultdict
from typing import Any


def _metric(row: dict[str, Any], name: str) -> float:
    try:
        return float(row.get(name, 0) or 0)
    except (TypeError, ValueError):
        return 0.0


def _delta(current: float, previous: float) -> float | None:
    if previous == 0:
        return None if current == 0 else 100.0
    return ((current - previous) / previous) * 100.0


def _key(row: dict[str, Any]) -> tuple[str, str]:
    keys = row.get("keys") or []
    query = str(keys[0]) if len(keys) > 0 else ""
    page = str(keys[1]) if len(keys) > 1 else ""
    return query, page


def totals(row: dict[str, Any] | None) -> dict[str, float]:
    row = row or {}
    return {
        "clicks": round(_metric(row, "clicks"), 2),
        "impressions": round(_metric(row, "impressions"), 2),
        "ctr": round(_metric(row, "ctr"), 6),
        "position": round(_metric(row, "position"), 2),
    }


def build_summary(current: dict[str, Any] | None, previous: dict[str, Any] | None) -> dict[str, Any]:
    now = totals(current)
    before = totals(previous)
    return {
        "current": now,
        "previous": before,
        "delta": {
            "clicks": _delta(now["clicks"], before["clicks"]),
            "impressions": _delta(now["impressions"], before["impressions"]),
            "ctr": _delta(now["ctr"], before["ctr"]),
            "position": (
                None
                if before["position"] == 0
                else round(before["position"] - now["position"], 2)
            ),
        },
    }


def trend_points(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    points: list[dict[str, Any]] = []
    for row in rows:
        keys = row.get("keys") or []
        if not keys:
            continue
        points.append(
            {
                "date": str(keys[0]),
                "clicks": round(_metric(row, "clicks"), 2),
                "impressions": round(_metric(row, "impressions"), 2),
                "ctr": round(_metric(row, "ctr"), 6),
                "position": round(_metric(row, "position"), 2),
            }
        )
    return sorted(points, key=lambda item: item["date"])


def _opportunity_id(kind: str, query: str, page: str) -> str:
    raw = f"{kind}|{query}|{page}".encode("utf-8")
    return hashlib.sha1(raw).hexdigest()[:12]


def analyze_opportunities(
    current_rows: list[dict[str, Any]],
    previous_rows: list[dict[str, Any]],
    *,
    limit: int = 24,
) -> list[dict[str, Any]]:
    previous = {_key(row): row for row in previous_rows}
    opportunities: list[dict[str, Any]] = []

    by_query: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in current_rows:
        query, page = _key(row)
        if not query or not page:
            continue
        by_query[query].append(row)
        impressions = _metric(row, "impressions")
        clicks = _metric(row, "clicks")
        ctr = _metric(row, "ctr")
        position = _metric(row, "position")

        if impressions >= 100 and 1 <= position <= 10 and ctr < 0.03:
            score = min(99, round(55 + min(impressions / 80, 25) + max(0, 10 - position) * 1.5))
            opportunities.append(
                {
                    "id": _opportunity_id("low_ctr", query, page),
                    "kind": "low_ctr",
                    "score": score,
                    "query": query,
                    "page": page,
                    "reason_code": "high_impressions_low_ctr",
                    "metrics": {
                        "clicks": clicks,
                        "impressions": impressions,
                        "ctr": ctr,
                        "position": position,
                    },
                }
            )

        if impressions >= 50 and 4 <= position <= 20:
            proximity = max(0, 20 - position) / 16
            score = min(98, round(48 + proximity * 32 + min(impressions / 150, 18)))
            opportunities.append(
                {
                    "id": _opportunity_id("striking_distance", query, page),
                    "kind": "striking_distance",
                    "score": score,
                    "query": query,
                    "page": page,
                    "reason_code": "ranking_striking_distance",
                    "metrics": {
                        "clicks": clicks,
                        "impressions": impressions,
                        "ctr": ctr,
                        "position": position,
                    },
                }
            )

        old = previous.get((query, page))
        if old:
            old_clicks = _metric(old, "clicks")
            old_impressions = _metric(old, "impressions")
            if old_clicks >= 5 and clicks <= old_clicks * 0.8:
                loss_pct = ((old_clicks - clicks) / old_clicks) * 100
                score = min(100, round(58 + min(loss_pct, 50) * 0.6 + min(old_clicks / 20, 12)))
                opportunities.append(
                    {
                        "id": _opportunity_id("decay", query, page),
                        "kind": "decay",
                        "score": score,
                        "query": query,
                        "page": page,
                        "reason_code": "click_decay",
                        "metrics": {
                            "clicks": clicks,
                            "impressions": impressions,
                            "ctr": ctr,
                            "position": position,
                            "previous_clicks": old_clicks,
                            "previous_impressions": old_impressions,
                            "click_loss_pct": round(loss_pct, 2),
                        },
                    }
                )

    for query, rows in by_query.items():
        if len(rows) < 2:
            continue
        ranked = sorted(rows, key=lambda item: _metric(item, "impressions"), reverse=True)
        top = [row for row in ranked[:3] if _metric(row, "impressions") >= 25]
        total_impressions = sum(_metric(row, "impressions") for row in top)
        if len(top) >= 2 and total_impressions >= 100:
            pages = [str((row.get("keys") or ["", ""])[1]) for row in top]
            score = min(95, round(60 + min(total_impressions / 150, 25)))
            opportunities.append(
                {
                    "id": _opportunity_id("cannibalization", query, "|".join(pages)),
                    "kind": "cannibalization",
                    "score": score,
                    "query": query,
                    "page": pages[0],
                    "pages": pages,
                    "reason_code": "multiple_pages_same_query",
                    "metrics": {"impressions": round(total_impressions, 2)},
                }
            )

    # Keep the highest-scoring record per id and return a compact action queue.
    unique: dict[str, dict[str, Any]] = {}
    for item in opportunities:
        current = unique.get(item["id"])
        if not current or item["score"] > current["score"]:
            unique[item["id"]] = item
    return sorted(unique.values(), key=lambda item: item["score"], reverse=True)[:limit]
