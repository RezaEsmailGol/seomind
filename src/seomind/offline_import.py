from __future__ import annotations

import csv
import io
import json
import re
import zipfile
from datetime import date
from pathlib import Path
from typing import Any

from openpyxl import load_workbook

from seomind.analyzer import build_summary, trend_points

MAX_UPLOAD_BYTES = 25 * 1024 * 1024

_PERSIAN_DIGITS = str.maketrans("۰۱۲۳۴۵۶۷۸۹", "0123456789")
_ARABIC_DIGITS = str.maketrans("٠١٢٣٤٥٦٧٨٩", "0123456789")


class OfflineImportError(RuntimeError):
    pass


def _normalize_header(value: Any) -> str:
    text = str(value or "").strip().lower().translate(_PERSIAN_DIGITS).translate(_ARABIC_DIGITS)
    text = re.sub(r"[_\-]+", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text


def _number(value: Any, *, percent: bool = False) -> float:
    if value is None or value == "":
        return 0.0
    if isinstance(value, (int, float)):
        number = float(value)
        return number / 100.0 if percent and number > 1 else number
    text = str(value).strip().translate(_PERSIAN_DIGITS).translate(_ARABIC_DIGITS)
    text = text.replace(",", "").replace("٬", "").replace("٫", ".")
    is_percent = "%" in text
    text = text.replace("%", "").strip()
    try:
        number = float(text)
    except ValueError:
        return 0.0
    if is_percent:
        return number / 100.0
    if percent:
        return number / 100.0 if number > 1 else number
    return number


def _field(headers: list[str], aliases: tuple[str, ...]) -> int | None:
    normalized = [_normalize_header(h) for h in headers]
    exact = {name: i for i, name in enumerate(normalized)}
    for alias in aliases:
        if alias in exact:
            return exact[alias]
    for i, name in enumerate(normalized):
        if any(alias in name for alias in aliases):
            return i
    return None


ALIASES = {
    "query": ("top queries", "query", "queries", "search query", "عبارت", "عبارت جستجو", "کوئری", "کلمه کلیدی"),
    "page": ("top pages", "page", "pages", "url", "landing page", "صفحه", "آدرس صفحه"),
    "date": ("date", "تاریخ"),
    "clicks": ("clicks", "click", "کلیک"),
    "impressions": ("impressions", "impression", "نمایش", "ایمپرشن"),
    "ctr": ("ctr", "نرخ کلیک"),
    "position": ("position", "average position", "avg position", "رتبه", "موقعیت"),
}


def _rows_from_matrix(name: str, matrix: list[list[Any]]) -> dict[str, Any] | None:
    if len(matrix) < 2:
        return None
    headers = [str(v or "").strip() for v in matrix[0]]
    indexes = {key: _field(headers, aliases) for key, aliases in ALIASES.items()}
    if indexes["clicks"] is None and indexes["impressions"] is None:
        return None

    kind = "unknown"
    if indexes["query"] is not None and indexes["page"] is not None:
        kind = "query_page"
    elif indexes["query"] is not None:
        kind = "queries"
    elif indexes["page"] is not None:
        kind = "pages"
    elif indexes["date"] is not None:
        kind = "dates"

    parsed: list[dict[str, Any]] = []
    for raw in matrix[1:]:
        if not any(v not in (None, "") for v in raw):
            continue

        def cell(index: int | None) -> Any:
            return raw[index] if index is not None and index < len(raw) else None

        item = {
            "clicks": _number(cell(indexes["clicks"])),
            "impressions": _number(cell(indexes["impressions"])),
            "ctr": _number(cell(indexes["ctr"]), percent=True),
            "position": _number(cell(indexes["position"])),
        }
        if kind == "query_page":
            item["query"] = str(cell(indexes["query"]) or "").strip()
            item["page"] = str(cell(indexes["page"]) or "").strip()
        elif kind == "queries":
            item["query"] = str(cell(indexes["query"]) or "").strip()
        elif kind == "pages":
            item["page"] = str(cell(indexes["page"]) or "").strip()
        elif kind == "dates":
            value = cell(indexes["date"])
            if hasattr(value, "isoformat"):
                value = value.isoformat()
            item["date"] = str(value or "").strip()

        if item.get("clicks") or item.get("impressions") or item.get("query") or item.get("page"):
            parsed.append(item)

    if not parsed:
        return None
    return {"name": name, "kind": kind, "rows": parsed, "headers": headers}


def _read_csv_bytes(name: str, payload: bytes) -> dict[str, Any] | None:
    text = None
    for encoding in ("utf-8-sig", "utf-8", "utf-16", "cp1256", "latin-1"):
        try:
            text = payload.decode(encoding)
            break
        except UnicodeDecodeError:
            continue
    if text is None:
        raise OfflineImportError(f"Could not decode CSV file: {name}")
    sample = text[:4096]
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=",;\t")
    except csv.Error:
        dialect = csv.excel
    matrix = [row for row in csv.reader(io.StringIO(text), dialect)]
    return _rows_from_matrix(name, matrix)


def _read_xlsx(payload: bytes) -> list[dict[str, Any]]:
    try:
        workbook = load_workbook(io.BytesIO(payload), read_only=True, data_only=True)
    except Exception as exc:
        raise OfflineImportError(f"Could not read Excel file: {exc}") from exc
    datasets: list[dict[str, Any]] = []
    for sheet in workbook.worksheets:
        matrix = [list(row) for row in sheet.iter_rows(values_only=True)]
        parsed = _rows_from_matrix(sheet.title, matrix)
        if parsed:
            datasets.append(parsed)
    return datasets


def parse_upload(filename: str, payload: bytes) -> dict[str, Any]:
    if not payload:
        raise OfflineImportError("The uploaded file is empty.")
    if len(payload) > MAX_UPLOAD_BYTES:
        raise OfflineImportError("The uploaded file is larger than 25 MB.")

    lower = filename.lower()
    datasets: list[dict[str, Any]] = []
    if lower.endswith(".xlsx"):
        datasets.extend(_read_xlsx(payload))
    elif lower.endswith(".csv"):
        parsed = _read_csv_bytes(filename, payload)
        if parsed:
            datasets.append(parsed)
    elif lower.endswith(".zip"):
        try:
            with zipfile.ZipFile(io.BytesIO(payload)) as archive:
                for info in archive.infolist():
                    if info.is_dir() or not info.filename.lower().endswith(".csv"):
                        continue
                    if info.file_size > MAX_UPLOAD_BYTES:
                        continue
                    parsed = _read_csv_bytes(info.filename, archive.read(info))
                    if parsed:
                        datasets.append(parsed)
        except zipfile.BadZipFile as exc:
            raise OfflineImportError("The uploaded ZIP file is invalid.") from exc
    else:
        raise OfflineImportError("Supported formats: .csv, .xlsx, or Search Console .zip export.")

    if not datasets:
        raise OfflineImportError(
            "No Search Console performance table was detected. Expected Clicks/Impressions plus Query, Page, or Date columns."
        )

    result: dict[str, Any] = {
        "source_file": filename,
        "queries": [],
        "pages": [],
        "dates": [],
        "query_page": [],
        "datasets": [{"name": item["name"], "kind": item["kind"], "count": len(item["rows"])} for item in datasets],
    }
    for dataset in datasets:
        kind = dataset["kind"]
        if kind in result:
            result[kind].extend(dataset["rows"])
    return result


def _weighted_totals(rows: list[dict[str, Any]]) -> dict[str, float]:
    clicks = sum(float(row.get("clicks", 0) or 0) for row in rows)
    impressions = sum(float(row.get("impressions", 0) or 0) for row in rows)
    ctr = clicks / impressions if impressions else 0.0
    position_weight = sum(
        float(row.get("position", 0) or 0) * max(float(row.get("impressions", 0) or 0), 1.0)
        for row in rows
    )
    denominator = sum(max(float(row.get("impressions", 0) or 0), 1.0) for row in rows)
    position = position_weight / denominator if denominator else 0.0
    return {"clicks": clicks, "impressions": impressions, "ctr": ctr, "position": position}


def _query_opportunities(rows: list[dict[str, Any]], site_url: str) -> list[dict[str, Any]]:
    opportunities: list[dict[str, Any]] = []
    for index, row in enumerate(rows):
        query = str(row.get("query", "")).strip()
        if not query:
            continue
        impressions = float(row.get("impressions", 0) or 0)
        clicks = float(row.get("clicks", 0) or 0)
        ctr = float(row.get("ctr", 0) or 0)
        position = float(row.get("position", 0) or 0)
        if impressions >= 100 and 1 <= position <= 10 and ctr < 0.03:
            score = min(99, round(55 + min(impressions / 80, 25) + max(0, 10 - position) * 1.5))
            opportunities.append({
                "id": f"offline-ctr-{index}",
                "kind": "low_ctr",
                "score": score,
                "query": query,
                "page": "",
                "reason_code": "high_impressions_low_ctr",
                "scope": "property",
                "metrics": {"clicks": clicks, "impressions": impressions, "ctr": ctr, "position": position},
            })
        if impressions >= 50 and 4 <= position <= 20:
            proximity = max(0, 20 - position) / 16
            score = min(98, round(48 + proximity * 32 + min(impressions / 150, 18)))
            opportunities.append({
                "id": f"offline-distance-{index}",
                "kind": "striking_distance",
                "score": score,
                "query": query,
                "page": "",
                "reason_code": "ranking_striking_distance",
                "scope": "property",
                "metrics": {"clicks": clicks, "impressions": impressions, "ctr": ctr, "position": position},
            })
    return sorted(opportunities, key=lambda item: item["score"], reverse=True)[:24]


def build_offline_audit(site_url: str, parsed: dict[str, Any]) -> dict[str, Any]:
    dates = parsed.get("dates", [])
    query_page = parsed.get("query_page", [])
    queries = parsed.get("queries", [])
    pages = parsed.get("pages", [])

    if dates:
        total_row = _weighted_totals(dates)
        trend = trend_points([
            {
                "keys": [str(row.get("date", ""))],
                "clicks": row.get("clicks", 0),
                "impressions": row.get("impressions", 0),
                "ctr": row.get("ctr", 0),
                "position": row.get("position", 0),
            }
            for row in dates
        ])
        start = min((str(row.get("date", "")) for row in dates if row.get("date")), default="")
        end = max((str(row.get("date", "")) for row in dates if row.get("date")), default="")
    else:
        source_rows = query_page or queries or pages
        total_row = _weighted_totals(source_rows)
        trend = []
        start = ""
        end = ""

    if query_page:
        normalized = [
            {
                "keys": [str(row.get("query", "")), str(row.get("page", ""))],
                "clicks": row.get("clicks", 0),
                "impressions": row.get("impressions", 0),
                "ctr": row.get("ctr", 0),
                "position": row.get("position", 0),
            }
            for row in query_page
        ]
        from seomind.analyzer import analyze_opportunities
        opportunities = analyze_opportunities(normalized, [])
    else:
        opportunities = _query_opportunities(queries, site_url)

    summary = build_summary(total_row, None)
    return {
        "site_url": site_url,
        "period": {"start": start, "end": end, "days": len(dates) if dates else 0},
        "previous_period": {"start": "", "end": ""},
        "summary": summary,
        "trend": trend,
        "opportunities": opportunities,
        "rows_analyzed": len(query_page or queries or pages),
        "data_note": "Privacy Mode: imported Search Console export. No Google OAuth connection is used.",
        "source": "offline_import",
        "import_capabilities": {
            "trend": bool(dates),
            "page_metrics": bool(pages or query_page),
            "query_metrics": bool(queries or query_page),
            "query_page_mapping": bool(query_page),
        },
        "datasets": parsed.get("datasets", []),
    }
