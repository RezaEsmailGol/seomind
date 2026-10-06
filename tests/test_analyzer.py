from seomind.analyzer import analyze_opportunities, build_summary


def row(query, page, clicks, impressions, ctr, position):
    return {
        "keys": [query, page],
        "clicks": clicks,
        "impressions": impressions,
        "ctr": ctr,
        "position": position,
    }


def test_summary_deltas():
    result = build_summary(
        {"clicks": 120, "impressions": 1000, "ctr": 0.12, "position": 7},
        {"clicks": 100, "impressions": 800, "ctr": 0.125, "position": 8},
    )
    assert result["current"]["clicks"] == 120
    assert round(result["delta"]["clicks"], 2) == 20
    assert result["delta"]["position"] == 1


def test_opportunity_engine_detects_ctr_distance_and_decay():
    current = [row("odoo developer", "https://example.com/odoo", 10, 1000, 0.01, 8.4)]
    previous = [row("odoo developer", "https://example.com/odoo", 20, 900, 0.022, 7.9)]
    result = analyze_opportunities(current, previous)
    kinds = {item["kind"] for item in result}
    assert "low_ctr" in kinds
    assert "striking_distance" in kinds
    assert "decay" in kinds


def test_cannibalization_detector():
    current = [
        row("seo audit", "https://example.com/a", 5, 120, 0.04, 9),
        row("seo audit", "https://example.com/b", 4, 100, 0.04, 10),
    ]
    result = analyze_opportunities(current, [])
    assert any(item["kind"] == "cannibalization" for item in result)
