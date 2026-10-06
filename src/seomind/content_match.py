from __future__ import annotations

import re
import unicodedata
from collections import defaultdict
from typing import Any
from urllib.parse import urlsplit, urlunsplit

_TOKEN_RE = re.compile(r"[^\W_]+", re.UNICODE)
_PERSIAN_MAP = str.maketrans({"ي": "ی", "ى": "ی", "ك": "ک", "ۀ": "ه", "ة": "ه"})
_STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "by", "for", "from", "how", "in", "is",
    "it", "of", "on", "or", "the", "this", "to", "what", "with", "your",
    "از", "با", "برای", "به", "در", "را", "که", "این", "آن", "و", "یا", "یک", "چی", "چطور",
}


def normalize_text(value: str) -> str:
    value = unicodedata.normalize("NFKC", value or "").translate(_PERSIAN_MAP).lower()
    value = "".join(ch for ch in value if unicodedata.category(ch) != "Mn")
    return re.sub(r"\s+", " ", value).strip()


def tokens(value: str) -> set[str]:
    return {token for token in _TOKEN_RE.findall(normalize_text(value)) if len(token) > 1 and token not in _STOPWORDS}


def normalize_page_url(value: str) -> str:
    parts = urlsplit(value.strip())
    return urlunsplit((parts.scheme.lower(), parts.netloc.lower(), parts.path or "/", parts.query, ""))


def _coverage(query_tokens: set[str], field_tokens: set[str]) -> float:
    if not query_tokens:
        return 0.0
    return len(query_tokens & field_tokens) / len(query_tokens)


def score_query_match(query: str, *, title: str, h1: str, body_text: str) -> dict[str, Any]:
    q_tokens = tokens(query)
    title_norm = normalize_text(title)
    h1_norm = normalize_text(h1)
    title_tokens = tokens(title)
    h1_tokens = tokens(h1)
    body_tokens = tokens(body_text)

    title_cov = _coverage(q_tokens, title_tokens)
    h1_cov = _coverage(q_tokens, h1_tokens)
    body_cov = _coverage(q_tokens, body_tokens)

    score = (title_cov * 0.50) + (h1_cov * 0.30) + (body_cov * 0.20)
    query_norm = normalize_text(query)
    if query_norm and query_norm in title_norm:
        score += 0.12
    if query_norm and query_norm in h1_norm:
        score += 0.08

    all_content = title_tokens | h1_tokens | body_tokens
    missing = sorted(q_tokens - all_content)
    matched_in = []
    if title_cov:
        matched_in.append("title")
    if h1_cov:
        matched_in.append("h1")
    if body_cov:
        matched_in.append("body")

    return {
        "score": min(100, round(score * 100)),
        "title_coverage": round(title_cov, 3),
        "h1_coverage": round(h1_cov, 3),
        "body_coverage": round(body_cov, 3),
        "matched_in": matched_in,
        "missing_terms": missing[:12],
    }


def attach_query_matches(
    pages: list[dict[str, Any]],
    gsc_rows: list[dict[str, Any]],
    *,
    max_queries_per_page: int = 8,
) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in gsc_rows:
        keys = row.get("keys") or []
        if len(keys) < 2:
            continue
        page_url, query = normalize_page_url(str(keys[0])), str(keys[1])
        grouped[page_url].append(
            {
                "query": query,
                "clicks": float(row.get("clicks", 0) or 0),
                "impressions": float(row.get("impressions", 0) or 0),
                "ctr": float(row.get("ctr", 0) or 0),
                "position": float(row.get("position", 0) or 0),
            }
        )

    output = []
    for page in pages:
        page = dict(page)
        candidates = sorted(
            grouped.get(normalize_page_url(str(page.get("url", ""))), []),
            key=lambda item: (item["impressions"], item["clicks"]),
            reverse=True,
        )[:max_queries_per_page]

        matches = []
        weighted_sum = 0.0
        total_weight = 0.0
        for item in candidates:
            match = score_query_match(
                item["query"],
                title=str(page.get("title", "")),
                h1=" ".join(page.get("h1", []) or []),
                body_text=str(page.get("body_text", "")),
            )
            merged = {**item, **match}
            matches.append(merged)
            weight = max(item["impressions"], 1.0)
            weighted_sum += match["score"] * weight
            total_weight += weight

        page["query_matches"] = matches
        page["content_match_score"] = round(weighted_sum / total_weight) if total_weight else None
        mismatch = [
            item for item in matches
            if item["impressions"] >= 50 and item["score"] < 40
        ]
        if mismatch:
            issues = list(page.get("issues", []))
            issues.append(
                {
                    "code": "query_content_mismatch",
                    "severity": "warning",
                    "message": "High-impression Search Console queries are weakly represented in the page title/H1/content.",
                    "count": len(mismatch),
                }
            )
            page["issues"] = issues
            page["technical_score"] = max(0, int(page.get("technical_score", 100)) - min(15, len(mismatch) * 5))

        page.pop("body_text", None)
        output.append(page)
    return output
