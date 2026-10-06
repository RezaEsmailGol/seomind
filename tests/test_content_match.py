from seomind.content_match import attach_query_matches, normalize_text, score_query_match


def test_persian_normalization():
    assert normalize_text("سئو يک") == "سئو یک"


def test_query_match_rewards_title_and_h1():
    result = score_query_match(
        "odoo developer",
        title="Hire an Odoo Developer",
        h1="Odoo Developer Services",
        body_text="Python ERP customization and implementation.",
    )
    assert result["score"] >= 80
    assert "title" in result["matched_in"]
    assert result["missing_terms"] == []


def test_attach_query_match_adds_mismatch_issue():
    pages = [{
        "url": "https://example.com/seo",
        "title": "Company news",
        "h1": ["Latest updates"],
        "body_text": "General company information.",
        "issues": [],
        "technical_score": 100,
    }]
    rows = [{
        "keys": ["https://example.com/seo", "technical seo audit"],
        "clicks": 2,
        "impressions": 500,
        "ctr": 0.004,
        "position": 9.0,
    }]
    result = attach_query_matches(pages, rows)
    assert result[0]["content_match_score"] < 40
    assert any(issue["code"] == "query_content_mismatch" for issue in result[0]["issues"])
