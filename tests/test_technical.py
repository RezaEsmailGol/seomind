from seomind.technical import summarize_pages


def test_technical_summary_counts_issues():
    pages = [
        {
            "content_type": "text/html",
            "technical_score": 92,
            "issues": [],
        },
        {
            "content_type": "text/html",
            "technical_score": 55,
            "issues": [
                {"code": "missing_title", "severity": "error"},
                {"code": "query_content_mismatch", "severity": "warning"},
            ],
        },
    ]
    result = summarize_pages(pages)
    assert result["pages_crawled"] == 2
    assert result["healthy_pages"] == 1
    assert result["pages_with_errors"] == 1
    assert result["missing_title"] == 1
    assert result["pages_with_query_mismatch"] == 1
