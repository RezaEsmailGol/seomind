from __future__ import annotations

import json
import os
import socket
import subprocess
import sys
import threading
import time
import webbrowser
from pathlib import Path
from typing import Any

import httpx

from seomind.config import settings

DASHBOARD_URL = "http://127.0.0.1:3000"
API_URL = "http://127.0.0.1:8787"
LOCK_PORT = 48787


class TrayRuntime:
    def __init__(self) -> None:
        self.root = Path(__file__).resolve().parents[2]
        self.web_dir = self.root / "apps" / "web"
        self.children: list[subprocess.Popen[Any]] = []
        self.icon: Any = None
        self.last_report_ids: dict[str, int] = {}
        self._stop = threading.Event()
        self._lock_socket: socket.socket | None = None

    def _creationflags(self) -> int:
        return subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0

    def _is_up(self, url: str) -> bool:
        try:
            return httpx.get(url, timeout=1.0).is_success
        except httpx.HTTPError:
            return False

    def acquire_single_instance(self) -> bool:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            sock.bind(("127.0.0.1", LOCK_PORT))
            sock.listen(1)
        except OSError:
            sock.close()
            return False
        self._lock_socket = sock
        return True

    def start_services(self) -> None:
        if not self._is_up(f"{API_URL}/health"):
            process = subprocess.Popen(
                [
                    sys.executable,
                    "-m",
                    "uvicorn",
                    "seomind.main:app",
                    "--host",
                    settings.host,
                    "--port",
                    str(settings.port),
                    "--log-level",
                    settings.log_level,
                ],
                cwd=self.root,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=self._creationflags(),
            )
            self.children.append(process)

        npm = "npm.cmd" if os.name == "nt" else "npm"
        if not self._is_up(DASHBOARD_URL) and self.web_dir.exists():
            process = subprocess.Popen(
                [npm, "start"],
                cwd=self.web_dir,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=self._creationflags(),
            )
            self.children.append(process)

    def wait_until_ready(self) -> None:
        for _ in range(30):
            if self._is_up(f"{API_URL}/health"):
                return
            time.sleep(0.5)

    def open_dashboard(self, *_: Any) -> None:
        webbrowser.open(DASHBOARD_URL)

    def open_docs(self, *_: Any) -> None:
        webbrowser.open(f"{API_URL}/docs")

    def notify(self, title: str, message: str) -> None:
        if self.icon is None:
            return
        try:
            self.icon.notify(message, title)
        except Exception:
            pass

    def _assistant_status(self) -> dict[str, Any] | None:
        try:
            response = httpx.get(f"{API_URL}/api/assistant/status", timeout=5)
            if response.is_success:
                return response.json()
        except httpx.HTTPError:
            pass
        return None

    def run_check_now(self, *_: Any) -> None:
        def work() -> None:
            status = self._assistant_status() or {}
            language = status.get("daily_language", "en")
            try:
                response = httpx.post(
                    f"{API_URL}/api/assistant/run",
                    json={"site_url": None, "language": language if language in {"en", "fa"} else "en"},
                    timeout=600,
                )
                response.raise_for_status()
                reports = response.json().get("reports", [])
                if reports:
                    needs = sum(1 for item in reports if item.get("status") in {"attention", "critical", "error"})
                    if language == "fa":
                        message = f"{len(reports)} سایت بررسی شد؛ {needs} مورد نیازمند توجه است."
                    else:
                        message = f"Checked {len(reports)} site(s); {needs} need attention."
                    self.notify("SeoMind", message)
                else:
                    self.notify("SeoMind", "No monitored sites are configured yet.")
            except Exception as exc:
                self.notify("SeoMind", f"Daily check failed: {str(exc)[:160]}")

        threading.Thread(target=work, daemon=True).start()

    def _watch_reports(self) -> None:
        while not self._stop.wait(60):
            status = self._assistant_status()
            if not status:
                continue
            language = status.get("daily_language", "en")
            for report in status.get("reports", []):
                site = str(report.get("site_url", ""))
                report_id = int(report.get("report_id", 0) or 0)
                previous = self.last_report_ids.get(site)
                self.last_report_ids[site] = report_id
                if not report_id or previous is None or report_id == previous:
                    continue

                state = str(report.get("status", "stable"))
                health = int(report.get("health_score", 0) or 0)
                headline = str(report.get("brief", {}).get("headline", "SeoMind daily brief"))
                if language == "fa":
                    message = f"{site}\nامتیاز سلامت: {health}/100\n{headline}"
                else:
                    message = f"{site}\nHealth: {health}/100\n{headline}"
                self.notify("SeoMind · Daily SEO Brief", message)

    def exit(self, *_: Any) -> None:
        self._stop.set()
        for process in reversed(self.children):
            try:
                process.terminate()
            except OSError:
                pass
        if self._lock_socket:
            try:
                self._lock_socket.close()
            except OSError:
                pass
        if self.icon is not None:
            self.icon.stop()

    @staticmethod
    def create_icon_image() -> Any:
        from PIL import Image, ImageDraw

        size = 64
        image = Image.new("RGBA", (size, size), (7, 17, 31, 255))
        draw = ImageDraw.Draw(image)
        draw.rounded_rectangle((5, 5, 59, 59), radius=16, fill=(13, 28, 48, 255), outline=(56, 189, 248, 255), width=3)
        draw.ellipse((16, 15, 43, 42), outline=(167, 139, 250, 255), width=4)
        draw.line((38, 38, 50, 50), fill=(56, 189, 248, 255), width=5)
        draw.ellipse((25, 24, 34, 33), fill=(110, 231, 183, 255))
        return image

    def run(self) -> None:
        if os.name != "nt":
            raise RuntimeError("The SeoMind system-tray app currently targets Windows.")

        if not self.acquire_single_instance():
            self.open_dashboard()
            return

        try:
            import pystray
        except ImportError as exc:
            raise RuntimeError("Tray dependencies are not installed. Run setup.bat again.") from exc

        self.start_services()
        self.wait_until_ready()

        menu = pystray.Menu(
            pystray.MenuItem("Open SeoMind", self.open_dashboard, default=True),
            pystray.MenuItem("Check all sites now", self.run_check_now),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("API docs", self.open_docs),
            pystray.MenuItem("Exit SeoMind", self.exit),
        )
        self.icon = pystray.Icon("SeoMind", self.create_icon_image(), "SeoMind · Local SEO Assistant", menu)
        initial = self._assistant_status() or {}
        for report in initial.get("reports", []):
            site = str(report.get("site_url", ""))
            self.last_report_ids[site] = int(report.get("report_id", 0) or 0)

        threading.Thread(target=self._watch_reports, daemon=True).start()
        self.icon.run()


def main() -> None:
    TrayRuntime().run()


if __name__ == "__main__":
    main()
