from seomind.crawler import PropertyScope, TechnicalCrawler


def test_domain_property_allows_subdomains_and_protocols():
    scope = PropertyScope("sc-domain:example.com")
    assert scope.allows("https://example.com/a")
    assert scope.allows("http://www.example.com/b")
    assert scope.allows("https://docs.example.com/c")
    assert not scope.allows("https://example.org/")


def test_url_prefix_property_is_strict():
    scope = PropertyScope("https://example.com/docs/")
    assert scope.allows("https://example.com/docs/page")
    assert not scope.allows("http://example.com/docs/page")
    assert not scope.allows("https://www.example.com/docs/page")
    assert not scope.allows("https://example.com/blog/")


def test_html_extraction_finds_title_h1_and_canonical():
    crawler = TechnicalCrawler("https://example.com/")
    page = crawler._analyze_html({
        "url": "https://example.com/page",
        "status": 200,
        "response_time_ms": 80,
        "headers": {"content-type": "text/html; charset=utf-8"},
        "body": b"""
            <html><head>
              <title>Technical SEO Audit Guide</title>
              <meta name="description" content="A useful technical SEO guide.">
              <link rel="canonical" href="/page">
            </head><body>
              <h1>Technical SEO Audit</h1>
              <p>This page explains crawling, indexing, sitemaps, canonical tags and search optimization in enough detail to create meaningful indexable body text for a technical audit page.</p>
              <a href="/next">Next</a>
            </body></html>
        """,
    })
    assert page["title"] == "Technical SEO Audit Guide"
    assert page["h1"] == ["Technical SEO Audit"]
    assert page["canonical"] == "https://example.com/page"
    assert page["internal_links"] == 1
    assert not any(issue["code"] == "missing_title" for issue in page["issues"])
