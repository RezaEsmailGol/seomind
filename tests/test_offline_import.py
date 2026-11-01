import io
import zipfile

from openpyxl import Workbook

from seomind.offline_import import build_offline_audit, parse_upload


def test_parse_standard_search_console_csv():
    payload = (
        "Top queries,Clicks,Impressions,CTR,Position\n"
        "odoo developer,12,1200,1%,8.4\n"
        "python backend,20,500,4%,12.2\n"
    ).encode("utf-8")
    parsed = parse_upload("Queries.csv", payload)
    assert len(parsed["queries"]) == 2
    assert parsed["queries"][0]["query"] == "odoo developer"
    assert parsed["queries"][0]["ctr"] == 0.01

    audit = build_offline_audit("https://example.com/", parsed)
    assert audit["source"] == "offline_import"
    assert audit["import_capabilities"]["query_metrics"] is True
    assert any(item["kind"] == "low_ctr" for item in audit["opportunities"])


def test_parse_search_console_zip_with_dates_and_pages():
    queries = (
        "Top queries,Clicks,Impressions,CTR,Position\n"
        "seo audit,10,1000,1%,7\n"
    ).encode("utf-8")
    dates = (
        "Date,Clicks,Impressions,CTR,Position\n"
        "2026-10-01,5,500,1%,7\n"
        "2026-10-02,7,600,1.1667%,6.8\n"
    ).encode("utf-8")
    pages = (
        "Top pages,Clicks,Impressions,CTR,Position\n"
        "https://example.com/seo,12,1100,1.09%,7\n"
    ).encode("utf-8")

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("Queries.csv", queries)
        archive.writestr("Dates.csv", dates)
        archive.writestr("Pages.csv", pages)

    parsed = parse_upload("search-console.zip", buffer.getvalue())
    assert len(parsed["dates"]) == 2
    assert len(parsed["pages"]) == 1

    audit = build_offline_audit("https://example.com/", parsed)
    assert audit["summary"]["current"]["clicks"] == 12
    assert len(audit["trend"]) == 2
    assert audit["import_capabilities"]["page_metrics"] is True


def test_parse_xlsx_with_query_page_mapping():
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Detailed"
    sheet.append(["Query", "Page", "Clicks", "Impressions", "CTR", "Position"])
    sheet.append(["odoo developer", "https://example.com/odoo", 10, 1000, 0.01, 8.4])
    output = io.BytesIO()
    workbook.save(output)

    parsed = parse_upload("detailed.xlsx", output.getvalue())
    assert len(parsed["query_page"]) == 1

    audit = build_offline_audit("https://example.com/", parsed)
    assert audit["import_capabilities"]["query_page_mapping"] is True
    assert audit["opportunities"][0]["page"] == "https://example.com/odoo"
