"""
Web scraper helpers for website search and fallback context.
"""
import logging
import threading
import time
from typing import Optional
from urllib.parse import urljoin, urlparse, urlunparse, parse_qs

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

DEFAULT_WEBSITE_URL = "https://ritzmediaworld.com"
DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )
}

REQUEST_TIMEOUT_SECONDS = 12
DEFAULT_MAX_PAGES = 5
CONTENT_CACHE_TTL_SECONDS = 900  # 15 minutes
SEARCH_CACHE_TTL_SECONDS = 300   # 5 minutes

_session = requests.Session()
_session.headers.update(DEFAULT_HEADERS)

_cache_lock = threading.Lock()
_website_content_cache: dict[str, tuple[float, str]] = {}
_search_cache: dict[tuple[str, str], tuple[float, str]] = {}
_external_search_cache: dict[str, tuple[float, str]] = {}


def _normalize_url(url: str) -> str:
    parsed = urlparse(url.strip())
    if not parsed.scheme:
        parsed = parsed._replace(scheme="https")
    normalized = parsed._replace(fragment="", query="")
    return urlunparse(normalized)


def is_valid_url(url: str) -> bool:
    parsed = urlparse(url)
    return bool(parsed.netloc and parsed.scheme)


def _is_cache_valid(ts: float, ttl_seconds: int) -> bool:
    return (time.time() - ts) <= ttl_seconds


def fetch_page_content(url: str, timeout: int = REQUEST_TIMEOUT_SECONDS) -> Optional[str]:
    try:
        response = _session.get(url, timeout=timeout)
        response.raise_for_status()

        soup = BeautifulSoup(response.content, "lxml")
        for element in soup(["script", "style", "nav", "footer", "header"]):
            element.decompose()

        text = soup.get_text(separator="\n")
        lines = [line.strip() for line in text.split("\n")]
        clean_text = "\n".join(line for line in lines if line)
        return clean_text

    except requests.exceptions.Timeout:
        logger.warning("Timeout fetching %s", url)
        return None
    except requests.exceptions.RequestException as exc:
        logger.warning("Request error fetching %s: %s", url, exc)
        return None
    except Exception as exc:
        logger.warning("Unexpected error fetching %s: %s", url, exc)
        return None


def get_all_links(base_url: str, max_pages: int = DEFAULT_MAX_PAGES) -> list[str]:
    visited = set()
    to_visit = [_normalize_url(base_url)]
    links: list[str] = []

    parsed_base = urlparse(base_url)
    base_domain = parsed_base.netloc

    while to_visit and len(visited) < max_pages:
        url = to_visit.pop(0)
        if url in visited:
            continue
        visited.add(url)
        links.append(url)

        try:
            response = _session.get(url, timeout=REQUEST_TIMEOUT_SECONDS)
            if response.status_code != 200:
                continue

            soup = BeautifulSoup(response.content, "lxml")
            for tag in soup.find_all("a", href=True):
                href = tag["href"]
                candidate = href if href.startswith("http") else urljoin(url, href)
                candidate = _normalize_url(candidate)
                parsed_candidate = urlparse(candidate)

                if parsed_candidate.netloc != base_domain:
                    continue
                if parsed_candidate.scheme not in {"http", "https"}:
                    continue
                if candidate in visited or candidate in to_visit:
                    continue
                if "#" in href or href.startswith("mailto:"):
                    continue

                to_visit.append(candidate)
        except Exception as exc:
            logger.debug("Error collecting links from %s: %s", url, exc)

    return links[:max_pages]


def scrape_website(url: str = DEFAULT_WEBSITE_URL, max_pages: int = DEFAULT_MAX_PAGES) -> str:
    url = _normalize_url(url)
    logger.info("Scraping website: %s", url)

    links = get_all_links(url, max_pages=max_pages)
    all_content: list[str] = []

    for index, link in enumerate(links, start=1):
        logger.info("Scraping page %d/%d: %s", index, len(links), link)
        content = fetch_page_content(link)
        if content and len(content) > 100:
            all_content.append(f"\n\n=== Page: {link} ===\n\n")
            all_content.append(content)

    combined = "\n".join(all_content)
    logger.info("Scraped %d pages, total content: %d chars", len(links), len(combined))
    return combined


def get_website_content(website_url: str = DEFAULT_WEBSITE_URL, force_refresh: bool = False) -> str:
    url = _normalize_url(website_url)
    now = time.time()

    with _cache_lock:
        entry = _website_content_cache.get(url)
        if entry and not force_refresh and _is_cache_valid(entry[0], CONTENT_CACHE_TTL_SECONDS):
            logger.info("Using cached website content for %s", url)
            return entry[1]

    logger.info("Refreshing website content cache for %s", url)
    content = scrape_website(url, max_pages=DEFAULT_MAX_PAGES)

    with _cache_lock:
        _website_content_cache[url] = (now, content)
    return content


def search_website(
    query: str,
    website_url: str = DEFAULT_WEBSITE_URL,
    use_fallback: bool = True,
) -> str:
    query_clean = (query or "").strip()
    if not query_clean:
        return ""

    url = _normalize_url(website_url)
    cache_key = (url, query_clean.lower())

    with _cache_lock:
        search_entry = _search_cache.get(cache_key)
        if search_entry and _is_cache_valid(search_entry[0], SEARCH_CACHE_TTL_SECONDS):
            logger.info("Using cached website search for query: %s", query_clean[:60])
            return search_entry[1]

    logger.info("Searching website for query: %s", query_clean[:80])
    links = get_all_links(url, max_pages=DEFAULT_MAX_PAGES)
    relevant_content: list[str] = []

    for link in links:
        content = fetch_page_content(link)
        if not content:
            continue
        if query_clean.lower() not in content.lower():
            continue

        lines = content.split("\n")
        relevant_lines: list[str] = []
        for idx, line in enumerate(lines):
            if query_clean.lower() in line.lower():
                start = max(0, idx - 2)
                end = min(len(lines), idx + 3)
                relevant_lines.extend(lines[start:end])

        if relevant_lines:
            relevant_content.append(f"\n\n=== From: {link} ===\n\n")
            relevant_content.append("\n".join(relevant_lines))

    result = "\n".join(relevant_content) if relevant_content else ""
    if not result and use_fallback:
        logger.info("No direct match, falling back to full website content.")
        result = get_website_content(url)

    with _cache_lock:
        _search_cache[cache_key] = (time.time(), result)

    return result


def search_web_general(query: str, max_results: int = 5) -> str:
    """
    Lightweight general web search fallback (outside the target website).
    Used only when local doc + website context cannot answer sufficiently.
    """
    query_clean = (query or "").strip()
    if not query_clean:
        return ""

    cache_key = query_clean.lower()
    with _cache_lock:
        cached = _external_search_cache.get(cache_key)
        if cached and _is_cache_valid(cached[0], SEARCH_CACHE_TTL_SECONDS):
            logger.info("Using cached external web search for query: %s", query_clean[:80])
            return cached[1]

    try:
        url = "https://duckduckgo.com/html/"
        resp = _session.get(url, params={"q": query_clean}, timeout=REQUEST_TIMEOUT_SECONDS)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.content, "lxml")

        rows: list[str] = []
        for result in soup.select(".result")[:max_results]:
            a = result.select_one(".result__a")
            snippet = result.select_one(".result__snippet")
            if not a:
                continue
            title = a.get_text(" ", strip=True)
            href = a.get("href", "").strip()
            desc = snippet.get_text(" ", strip=True) if snippet else ""
            rows.append(f"- {title}\n  {desc}\n  Source: {href}")

        combined = "\n".join(rows)
        if not combined:
            # Fallback parser for Bing when DuckDuckGo markup or anti-bot blocks snippets.
            bing_url = "https://www.bing.com/search"
            bing_resp = _session.get(
                bing_url,
                params={"q": query_clean, "setlang": "en"},
                timeout=REQUEST_TIMEOUT_SECONDS,
            )
            bing_resp.raise_for_status()
            bing_soup = BeautifulSoup(bing_resp.content, "lxml")
            bing_rows: list[str] = []
            keep_keywords = (
                "agency", "agencies", "advertising", "media", "marketing",
                "digital", "companies", "india", "indian"
            )
            for item in bing_soup.select("li.b_algo")[:max_results]:
                a = item.select_one("h2 a")
                snippet_tag = item.select_one(".b_caption p")
                if not a:
                    continue
                title = a.get_text(" ", strip=True)
                href = a.get("href", "").strip()
                # Decode Bing redirect URL when possible.
                parsed_href = urlparse(href)
                if "bing.com" in parsed_href.netloc and parsed_href.path.startswith("/ck/a"):
                    qs = parse_qs(parsed_href.query)
                    target = qs.get("u", [""])[0]
                    if target.startswith("a1"):
                        try:
                            import base64
                            decoded = base64.b64decode(target[2:] + "===").decode("utf-8", errors="ignore")
                            if decoded.startswith("http"):
                                href = decoded
                        except Exception:
                            pass
                desc = snippet_tag.get_text(" ", strip=True) if snippet_tag else ""
                relevance_text = f"{title} {desc}".lower()
                if not any(k in relevance_text for k in keep_keywords):
                    continue
                bing_rows.append(f"- {title}\n  {desc}\n  Source: {href}")
            combined = "\n".join(bing_rows)

        with _cache_lock:
            _external_search_cache[cache_key] = (time.time(), combined)
        return combined
    except Exception as exc:
        logger.warning("External web search failed for '%s': %s", query_clean[:80], exc)
        return ""
