from __future__ import annotations

import asyncio
import ipaddress
import re
import socket
import time
from collections import deque
from typing import Any
from urllib import robotparser
from urllib.parse import urljoin, urlsplit, urlunsplit

import httpx
from bs4 import BeautifulSoup
from defusedxml import ElementTree

USER_AGENT = "SeoMindBot/0.3 (+https://github.com/RezaEsmailGol/seomind)"
MAX_RESPONSE_BYTES = 2_500_000
MAX_REDIRECTS = 5
MAX_SITEMAP_DOCS = 20
MAX_SITEMAP_URLS = 5000


class CrawlError(RuntimeError):
    pass


def _clean_url(url: str) -> str:
    parts = urlsplit(url.strip())
    return urlunsplit((parts.scheme.lower(), parts.netloc.lower(), parts.path or "/", parts.query, ""))


class PropertyScope:
    def __init__(self, property_url: str) -> None:
        self.property_url = property_url.strip()
        self.is_domain = self.property_url.startswith("sc-domain:")
        if self.is_domain:
            self.domain = self.property_url.split(":", 1)[1].strip().lower().rstrip(".")
            self.prefix = ""
            self.seed_url = f"https://{self.domain}/"
        else:
            parts = urlsplit(self.property_url)
            if parts.scheme not in {"http", "https"} or not parts.hostname:
                raise CrawlError("The selected Search Console property is not a crawlable web property.")
            self.domain = parts.hostname.lower().rstrip(".")
            self.prefix = _clean_url(self.property_url)
            self.seed_url = self.prefix

    def allows(self, url: str) -> bool:
        try:
            cleaned = _clean_url(url)
            parts = urlsplit(cleaned)
        except ValueError:
            return False
        if parts.scheme not in {"http", "https"} or not parts.hostname:
            return False
        host = parts.hostname.lower().rstrip(".")
        if self.is_domain:
            return host == self.domain or host.endswith(f".{self.domain}")
        return cleaned.startswith(self.prefix)

    def origin(self, url: str) -> str:
        parts = urlsplit(url)
        return f"{parts.scheme.lower()}://{parts.netloc.lower()}"


async def _host_is_public(hostname: str) -> bool:
    try:
        direct = ipaddress.ip_address(hostname)
        return direct.is_global
    except ValueError:
        pass

    try:
        infos = await asyncio.to_thread(socket.getaddrinfo, hostname, None, type=socket.SOCK_STREAM)
    except socket.gaierror:
        return False

    addresses = {item[4][0] for item in infos}
    if not addresses:
        return False
    for value in addresses:
        try:
            if not ipaddress.ip_address(value).is_global:
                return False
        except ValueError:
            return False
    return True


def _issue(code: str, severity: str, message: str, **extra: Any) -> dict[str, Any]:
    return {"code": code, "severity": severity, "message": message, **extra}


class TechnicalCrawler:
    def __init__(self, property_url: str, *, concurrency: int = 6) -> None:
        self.scope = PropertyScope(property_url)
        self.concurrency = max(1, min(concurrency, 10))
        self._robots: dict[str, robotparser.RobotFileParser] = {}
        self._robots_sitemaps: dict[str, list[str]] = {}
        self._sem = asyncio.Semaphore(self.concurrency)

    async def _fetch(
        self,
        client: httpx.AsyncClient,
        url: str,
        *,
        max_bytes: int = MAX_RESPONSE_BYTES,
    ) -> dict[str, Any]:
        current = _clean_url(url)
        for _ in range(MAX_REDIRECTS + 1):
            if not self.scope.allows(current):
                raise CrawlError("Crawler refused a URL outside the selected Search Console property.")
            host = urlsplit(current).hostname
            if not host or not await _host_is_public(host):
                raise CrawlError("Crawler refused a private, loopback, reserved, or unresolved address.")

            started = time.perf_counter()
            async with client.stream(
                "GET",
                current,
                headers={"User-Agent": USER_AGENT, "Accept": "text/html,application/xhtml+xml,application/xml,text/xml,*/*;q=0.5"},
                follow_redirects=False,
            ) as response:
                elapsed_ms = round((time.perf_counter() - started) * 1000)
                if response.status_code in {301, 302, 303, 307, 308}:
                    location = response.headers.get("location")
                    if not location:
                        break
                    current = _clean_url(urljoin(current, location))
                    continue

                length = response.headers.get("content-length")
                if length and length.isdigit() and int(length) > max_bytes:
                    raise CrawlError(f"Response is larger than the {max_bytes} byte crawl limit.")

                body = bytearray()
                async for chunk in response.aiter_bytes():
                    body.extend(chunk)
                    if len(body) > max_bytes:
                        raise CrawlError(f"Response exceeded the {max_bytes} byte crawl limit.")
                return {
                    "url": current,
                    "status": response.status_code,
                    "headers": dict(response.headers),
                    "body": bytes(body),
                    "response_time_ms": elapsed_ms,
                }
        raise CrawlError("Too many redirects.")

    async def _load_robots(self, client: httpx.AsyncClient, origin: str) -> None:
        if origin in self._robots:
            return
        parser = robotparser.RobotFileParser()
        robots_url = f"{origin.rstrip('/')}/robots.txt"
        sitemaps: list[str] = []
        try:
            fetched = await self._fetch(client, robots_url, max_bytes=500_000)
            if fetched["status"] == 200:
                text = fetched["body"].decode("utf-8", errors="replace")
                parser.set_url(robots_url)
                parser.parse(text.splitlines())
                for line in text.splitlines():
                    if line.lower().startswith("sitemap:"):
                        value = line.split(":", 1)[1].strip()
                        if value and self.scope.allows(value):
                            sitemaps.append(_clean_url(value))
            else:
                parser.parse([])
        except CrawlError:
            parser.parse([])
        self._robots[origin] = parser
        self._robots_sitemaps[origin] = list(dict.fromkeys(sitemaps))

    async def _allowed_by_robots(self, client: httpx.AsyncClient, url: str) -> bool:
        origin = self.scope.origin(url)
        await self._load_robots(client, origin)
        parser = self._robots[origin]
        return parser.can_fetch(USER_AGENT, url)

    async def discover_sitemaps(
        self,
        client: httpx.AsyncClient,
        origins: list[str],
    ) -> tuple[list[str], list[str]]:
        sitemap_queue: deque[str] = deque()
        sitemap_docs: list[str] = []
        urls: list[str] = []
        seen_docs: set[str] = set()

        for origin in origins[:4]:
            await self._load_robots(client, origin)
            for item in self._robots_sitemaps.get(origin, []):
                sitemap_queue.append(item)
            sitemap_queue.append(f"{origin.rstrip('/')}/sitemap.xml")
            sitemap_queue.append(f"{origin.rstrip('/')}/sitemap_index.xml")

        while sitemap_queue and len(seen_docs) < MAX_SITEMAP_DOCS and len(urls) < MAX_SITEMAP_URLS:
            sitemap_url = _clean_url(sitemap_queue.popleft())
            if sitemap_url in seen_docs or not self.scope.allows(sitemap_url):
                continue
            seen_docs.add(sitemap_url)
            try:
                fetched = await self._fetch(client, sitemap_url, max_bytes=5_000_000)
            except CrawlError:
                continue
            if fetched["status"] != 200 or not fetched["body"]:
                continue
            try:
                root = ElementTree.fromstring(fetched["body"])
            except Exception:
                continue

            tag = root.tag.rsplit("}", 1)[-1].lower()
            locs = []
            for element in root.iter():
                if element.tag.rsplit("}", 1)[-1].lower() == "loc" and element.text:
                    locs.append(element.text.strip())

            sitemap_docs.append(sitemap_url)
            if tag == "sitemapindex":
                for loc in locs:
                    if self.scope.allows(loc):
                        sitemap_queue.append(_clean_url(loc))
            elif tag == "urlset":
                for loc in locs:
                    if self.scope.allows(loc):
                        urls.append(_clean_url(loc))
                        if len(urls) >= MAX_SITEMAP_URLS:
                            break

        return list(dict.fromkeys(sitemap_docs)), list(dict.fromkeys(urls))

    def _analyze_html(self, fetched: dict[str, Any]) -> dict[str, Any]:
        url = fetched["url"]
        status = int(fetched["status"])
        headers = fetched["headers"]
        content_type = str(headers.get("content-type", "")).lower()
        base = {
            "url": url,
            "status": status,
            "response_time_ms": fetched["response_time_ms"],
            "content_type": content_type,
            "title": "",
            "title_length": 0,
            "meta_description": "",
            "meta_description_length": 0,
            "h1": [],
            "h1_count": 0,
            "canonical": None,
            "meta_robots": "",
            "noindex": False,
            "word_count": 0,
            "internal_links": 0,
            "technical_score": 100,
            "issues": [],
            "body_text": "",
            "_links": [],
        }
        issues: list[dict[str, Any]] = base["issues"]
        score = 100

        if status < 200 or status >= 300:
            issues.append(_issue("http_status", "error", f"Page returned HTTP {status}."))
            score -= 45

        if "html" not in content_type and "xhtml" not in content_type:
            issues.append(_issue("non_html", "info", "URL did not return HTML content."))
            base["technical_score"] = max(0, score - 10)
            return base

        soup = BeautifulSoup(fetched["body"], "html.parser")
        title = " ".join(soup.title.stripped_strings) if soup.title else ""
        h1_values = [" ".join(node.stripped_strings) for node in soup.find_all("h1")]
        h1_values = [value for value in h1_values if value]

        canonical = None
        canonical_node = soup.find("link", rel=lambda value: value and "canonical" in [str(x).lower() for x in (value if isinstance(value, list) else [value])])
        if canonical_node and canonical_node.get("href"):
            canonical = _clean_url(urljoin(url, str(canonical_node.get("href"))))

        description = ""
        desc_node = soup.find("meta", attrs={"name": re.compile(r"^description$", re.I)})
        if desc_node and desc_node.get("content"):
            description = " ".join(str(desc_node.get("content")).split())

        robots_values = []
        for node in soup.find_all("meta"):
            name = str(node.get("name", "")).lower()
            if name in {"robots", "googlebot"} and node.get("content"):
                robots_values.append(str(node.get("content")))
        meta_robots = ", ".join(robots_values)
        noindex = "noindex" in meta_robots.lower()

        links: list[str] = []
        for node in soup.find_all("a", href=True):
            href = str(node.get("href", "")).strip()
            if not href or href.startswith(("#", "mailto:", "tel:", "javascript:")):
                continue
            absolute = _clean_url(urljoin(url, href))
            if self.scope.allows(absolute):
                links.append(absolute)

        for node in soup(["script", "style", "noscript", "svg", "template"]):
            node.decompose()
        body_text = " ".join(soup.stripped_strings)
        word_count = len(re.findall(r"[^\W_]+", body_text, re.UNICODE))

        if not title:
            issues.append(_issue("missing_title", "error", "Page is missing a <title>."))
            score -= 20
        elif len(title) < 25:
            issues.append(_issue("short_title", "warning", "Title is unusually short."))
            score -= 5
        elif len(title) > 65:
            issues.append(_issue("long_title", "warning", "Title is longer than the typical search-result range."))
            score -= 5

        if not h1_values:
            issues.append(_issue("missing_h1", "error", "Page has no H1 heading."))
            score -= 15
        elif len(h1_values) > 1:
            issues.append(_issue("multiple_h1", "warning", "Page has multiple H1 headings.", count=len(h1_values)))
            score -= 5

        if not canonical:
            issues.append(_issue("missing_canonical", "warning", "Page has no canonical link."))
            score -= 10
        elif not self.scope.allows(canonical):
            issues.append(_issue("canonical_outside_property", "warning", "Canonical points outside the selected property."))
            score -= 12
        elif _clean_url(canonical) != _clean_url(url):
            issues.append(_issue("canonical_points_elsewhere", "info", "Canonical points to another URL in the property."))
            score -= 3

        if noindex:
            issues.append(_issue("noindex", "warning", "Page contains a noindex directive."))
            score -= 20
        if not description:
            issues.append(_issue("missing_meta_description", "info", "Page has no meta description."))
            score -= 4
        if word_count < 120:
            issues.append(_issue("thin_content", "info", "Page contains very little indexable text.", word_count=word_count))
            score -= 4

        base.update(
            {
                "title": title,
                "title_length": len(title),
                "meta_description": description,
                "meta_description_length": len(description),
                "h1": h1_values[:5],
                "h1_count": len(h1_values),
                "canonical": canonical,
                "meta_robots": meta_robots,
                "noindex": noindex,
                "word_count": word_count,
                "internal_links": len(set(links)),
                "technical_score": max(0, score),
                "body_text": body_text[:250_000],
                "_links": list(dict.fromkeys(links)),
            }
        )
        return base

    async def crawl_page(self, client: httpx.AsyncClient, url: str) -> dict[str, Any]:
        async with self._sem:
            cleaned = _clean_url(url)
            if not self.scope.allows(cleaned):
                return {
                    "url": cleaned,
                    "status": None,
                    "technical_score": 0,
                    "issues": [_issue("outside_scope", "error", "URL is outside the selected property.")],
                    "_links": [],
                    "body_text": "",
                }
            if not await self._allowed_by_robots(client, cleaned):
                return {
                    "url": cleaned,
                    "status": None,
                    "technical_score": 70,
                    "issues": [_issue("robots_blocked", "info", "robots.txt disallows SeoMindBot from crawling this URL.")],
                    "_links": [],
                    "body_text": "",
                }
            try:
                fetched = await self._fetch(client, cleaned)
            except (CrawlError, httpx.HTTPError) as exc:
                return {
                    "url": cleaned,
                    "status": None,
                    "technical_score": 30,
                    "issues": [_issue("crawl_error", "error", str(exc))],
                    "_links": [],
                    "body_text": "",
                }
            return self._analyze_html(fetched)

    async def crawl(
        self,
        *,
        seed_urls: list[str],
        max_pages: int = 50,
    ) -> dict[str, Any]:
        max_pages = max(1, min(max_pages, 200))
        safe_seeds = [_clean_url(url) for url in seed_urls if self.scope.allows(url)]
        if not safe_seeds:
            safe_seeds = [self.scope.seed_url]

        origins = list(dict.fromkeys(self.scope.origin(url) for url in safe_seeds))[:4]
        timeout = httpx.Timeout(connect=8, read=15, write=10, pool=10)
        limits = httpx.Limits(max_connections=self.concurrency + 2, max_keepalive_connections=self.concurrency)

        async with httpx.AsyncClient(timeout=timeout, limits=limits) as client:
            sitemap_docs, sitemap_urls = await self.discover_sitemaps(client, origins)

            queue: deque[str] = deque()
            for url in [*safe_seeds, *sitemap_urls, self.scope.seed_url]:
                if self.scope.allows(url):
                    queue.append(_clean_url(url))

            seen: set[str] = set()
            results: list[dict[str, Any]] = []
            while queue and len(results) < max_pages:
                batch: list[str] = []
                while queue and len(batch) < self.concurrency and len(results) + len(batch) < max_pages:
                    candidate = queue.popleft()
                    if candidate in seen:
                        continue
                    seen.add(candidate)
                    batch.append(candidate)
                if not batch:
                    continue

                crawled = await asyncio.gather(*(self.crawl_page(client, url) for url in batch))
                for page in crawled:
                    results.append(page)
                    for link in page.get("_links", [])[:100]:
                        if link not in seen and self.scope.allows(link):
                            queue.append(link)

        for page in results:
            page.pop("_links", None)

        return {
            "sitemaps": sitemap_docs,
            "sitemap_url_count": len(sitemap_urls),
            "pages": results,
        }
