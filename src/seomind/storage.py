from __future__ import annotations

import json
import os
import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from seomind.config import settings


class LocalStorage:
    def __init__(self, data_dir: Path | None = None) -> None:
        self.data_dir = Path(data_dir or settings.data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.credentials_path = self.data_dir / "google_client_secret.json"
        self.token_path = self.data_dir / "google_token.json"
        self.oauth_state_path = self.data_dir / "oauth_state.json"
        self.db_path = self.data_dir / "seomind.db"
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS app_settings (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS audits (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    site_url TEXT NOT NULL,
                    start_date TEXT NOT NULL,
                    end_date TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    row_count INTEGER NOT NULL,
                    payload_json TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS technical_audits (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    site_url TEXT NOT NULL,
                    start_date TEXT NOT NULL,
                    end_date TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    page_count INTEGER NOT NULL,
                    payload_json TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS monitored_sites (
                    site_url TEXT PRIMARY KEY,
                    label TEXT NOT NULL DEFAULT '',
                    enabled INTEGER NOT NULL DEFAULT 1,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS assistant_reports (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    site_url TEXT NOT NULL,
                    report_date TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    health_score INTEGER NOT NULL,
                    status TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    UNIQUE(site_url, report_date)
                );

                CREATE INDEX IF NOT EXISTS idx_assistant_reports_site_date
                ON assistant_reports(site_url, report_date DESC);
                """
            )

    @staticmethod
    def _secure_write(path: Path, payload: dict[str, Any]) -> None:
        tmp = path.with_suffix(path.suffix + ".tmp")
        tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        os.replace(tmp, path)
        try:
            path.chmod(0o600)
        except OSError:
            pass

    @staticmethod
    def _read_json(path: Path) -> dict[str, Any] | None:
        if not path.exists():
            return None
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None
        return value if isinstance(value, dict) else None

    def save_google_credentials(self, payload: dict[str, Any]) -> None:
        self._secure_write(self.credentials_path, payload)

    def get_google_credentials(self) -> dict[str, Any] | None:
        return self._read_json(self.credentials_path)

    def save_google_token(self, payload: dict[str, Any]) -> None:
        current = self.get_google_token() or {}
        if not payload.get("refresh_token") and current.get("refresh_token"):
            payload["refresh_token"] = current["refresh_token"]
        self._secure_write(self.token_path, payload)

    def get_google_token(self) -> dict[str, Any] | None:
        return self._read_json(self.token_path)

    def clear_google(self) -> None:
        for path in (self.credentials_path, self.token_path, self.oauth_state_path):
            try:
                path.unlink(missing_ok=True)
            except OSError:
                pass
        self.set_setting("selected_property", "")

    def save_oauth_state(self, state: str) -> None:
        self._secure_write(
            self.oauth_state_path,
            {"state": state, "created_at": datetime.now(UTC).isoformat()},
        )

    def consume_oauth_state(self, state: str) -> bool:
        payload = self._read_json(self.oauth_state_path)
        try:
            self.oauth_state_path.unlink(missing_ok=True)
        except OSError:
            pass
        if not payload or payload.get("state") != state:
            return False
        try:
            created_at = datetime.fromisoformat(str(payload.get("created_at", "")))
            if created_at.tzinfo is None:
                created_at = created_at.replace(tzinfo=UTC)
            age = datetime.now(UTC) - created_at
            return age.total_seconds() <= 600
        except ValueError:
            return False

    def set_setting(self, key: str, value: str) -> None:
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO app_settings(key, value) VALUES (?, ?) "
                "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
                (key, value),
            )

    def get_setting(self, key: str, default: str | None = None) -> str | None:
        with self._connect() as conn:
            row = conn.execute("SELECT value FROM app_settings WHERE key = ?", (key,)).fetchone()
        return str(row["value"]) if row else default

    def upsert_monitored_site(self, site_url: str, label: str = "", enabled: bool = True) -> None:
        now = datetime.now(UTC).isoformat()
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO monitored_sites(site_url, label, enabled, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(site_url) DO UPDATE SET
                    label = CASE WHEN excluded.label != '' THEN excluded.label ELSE monitored_sites.label END,
                    enabled = excluded.enabled,
                    updated_at = excluded.updated_at
                """,
                (site_url, label, 1 if enabled else 0, now, now),
            )

    def list_monitored_sites(self, enabled_only: bool = False) -> list[dict[str, Any]]:
        sql = "SELECT site_url, label, enabled, created_at, updated_at FROM monitored_sites"
        if enabled_only:
            sql += " WHERE enabled = 1"
        sql += " ORDER BY created_at ASC"
        with self._connect() as conn:
            rows = conn.execute(sql).fetchall()
        return [
            {
                "site_url": row["site_url"],
                "label": row["label"],
                "enabled": bool(row["enabled"]),
                "created_at": row["created_at"],
                "updated_at": row["updated_at"],
            }
            for row in rows
        ]

    def set_site_enabled(self, site_url: str, enabled: bool) -> None:
        with self._connect() as conn:
            conn.execute(
                "UPDATE monitored_sites SET enabled = ?, updated_at = ? WHERE site_url = ?",
                (1 if enabled else 0, datetime.now(UTC).isoformat(), site_url),
            )

    def save_audit(self, *, site_url: str, start_date: str, end_date: str, row_count: int, payload: dict[str, Any]) -> int:
        with self._connect() as conn:
            cur = conn.execute(
                """
                INSERT INTO audits(site_url, start_date, end_date, created_at, row_count, payload_json)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (site_url, start_date, end_date, datetime.now(UTC).isoformat(), row_count, json.dumps(payload, ensure_ascii=False)),
            )
            return int(cur.lastrowid)

    def save_technical_audit(self, *, site_url: str, start_date: str, end_date: str, page_count: int, payload: dict[str, Any]) -> int:
        with self._connect() as conn:
            cur = conn.execute(
                """
                INSERT INTO technical_audits(site_url, start_date, end_date, created_at, page_count, payload_json)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (site_url, start_date, end_date, datetime.now(UTC).isoformat(), page_count, json.dumps(payload, ensure_ascii=False)),
            )
            return int(cur.lastrowid)

    def save_assistant_report(self, *, site_url: str, report_date: str, health_score: int, status: str, payload: dict[str, Any]) -> int:
        now = datetime.now(UTC).isoformat()
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO assistant_reports(site_url, report_date, created_at, health_score, status, payload_json)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(site_url, report_date) DO UPDATE SET
                    created_at = excluded.created_at,
                    health_score = excluded.health_score,
                    status = excluded.status,
                    payload_json = excluded.payload_json
                """,
                (site_url, report_date, now, health_score, status, json.dumps(payload, ensure_ascii=False)),
            )
            row = conn.execute(
                "SELECT id FROM assistant_reports WHERE site_url = ? AND report_date = ?",
                (site_url, report_date),
            ).fetchone()
            return int(row["id"])

    def _latest_payload(self, table: str, site_url: str | None) -> dict[str, Any] | None:
        if table not in {"audits", "technical_audits"}:
            raise ValueError("Unsupported audit table.")
        sql = f"SELECT * FROM {table}"
        params: tuple[Any, ...] = ()
        if site_url:
            sql += " WHERE site_url = ?"
            params = (site_url,)
        sql += " ORDER BY id DESC LIMIT 1"
        with self._connect() as conn:
            row = conn.execute(sql, params).fetchone()
        if not row:
            return None
        payload = json.loads(row["payload_json"])
        key = "audit_id" if table == "audits" else "technical_audit_id"
        payload[key] = row["id"]
        payload["created_at"] = row["created_at"]
        return payload

    def latest_audit(self, site_url: str | None = None) -> dict[str, Any] | None:
        return self._latest_payload("audits", site_url)

    def latest_technical_audit(self, site_url: str | None = None) -> dict[str, Any] | None:
        return self._latest_payload("technical_audits", site_url)

    def latest_assistant_report(self, site_url: str) -> dict[str, Any] | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM assistant_reports WHERE site_url = ? ORDER BY report_date DESC, id DESC LIMIT 1",
                (site_url,),
            ).fetchone()
        if not row:
            return None
        payload = json.loads(row["payload_json"])
        payload["report_id"] = row["id"]
        payload["created_at"] = row["created_at"]
        return payload

    def assistant_reports(self, limit_per_site: int = 1) -> list[dict[str, Any]]:
        sites = self.list_monitored_sites()
        reports: list[dict[str, Any]] = []
        for site in sites:
            with self._connect() as conn:
                rows = conn.execute(
                    """
                    SELECT * FROM assistant_reports
                    WHERE site_url = ?
                    ORDER BY report_date DESC, id DESC
                    LIMIT ?
                    """,
                    (site["site_url"], limit_per_site),
                ).fetchall()
            for row in rows:
                payload = json.loads(row["payload_json"])
                payload["report_id"] = row["id"]
                payload["created_at"] = row["created_at"]
                reports.append(payload)
        return reports


storage = LocalStorage()
