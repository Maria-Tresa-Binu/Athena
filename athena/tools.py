import os
import re
from datetime import datetime, timedelta, timezone
from html import unescape
from urllib.parse import urlparse
from urllib.request import Request, urlopen
from xml.etree import ElementTree

from .models import Tool
from .storage import Storage


def _news(feeds: str | None = None, limit: int = 5) -> list[dict[str, str]]:
    urls = (feeds or os.getenv("ATHENA_NEWS_FEEDS", "https://feeds.arstechnica.com/arstechnica/technology-lab")).split(",")
    stories = []
    for url in urls:
        try:
            with urlopen(_request(url.strip()), timeout=8) as response:
                root = ElementTree.fromstring(response.read())
            channel = root.find("channel")
            source = channel.findtext("title", url) if channel is not None else url
            for entry in (channel.findall("item") if channel is not None else [])[:limit]:
                stories.append({"title": entry.findtext("title", "Untitled"), "url": entry.findtext("link", ""), "source": source})
        except Exception:
            continue

    scrape_urls = [url.strip() for url in os.getenv("ATHENA_NEWS_SCRAPE_URLS", "").split(",") if url.strip()]
    for url in scrape_urls:
        try:
            stories.extend(_scrape_url(url))
        except Exception:
            continue
    return _deduplicate(stories)[:limit]


def _request(url: str) -> Request:
    return Request(url, headers={"User-Agent": "Athena/0.1 technology-news-reader"})


def _scrape_url(url: str) -> list[dict[str, str]]:
    _validate_scrape_url(url)
    with urlopen(_request(url), timeout=10) as response:
        html = response.read(2_000_000).decode("utf-8", errors="replace")
    return [_extract_article(url, html)]


def _validate_scrape_url(url: str) -> None:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError("Only public HTTP(S) URLs can be scraped")
    allowed = [item.strip().lower() for item in os.getenv("ATHENA_ALLOWED_SCRAPE_DOMAINS", "").split(",") if item.strip()]
    if allowed and not any((parsed.hostname or "").lower().endswith(domain) for domain in allowed):
        raise ValueError("The URL domain is not in ATHENA_ALLOWED_SCRAPE_DOMAINS")


def _extract_article(url: str, html: str) -> dict[str, str]:
    title = "Untitled article"
    text = ""
    published = ""
    try:
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(html, "html.parser")
        title = (soup.find("meta", property="og:title") or soup.find("title"))
        title = title.get("content", "") if getattr(title, "name", "") == "meta" else title.get_text(" ", strip=True) if title else title
        published_tag = soup.find("meta", property="article:published_time") or soup.find("time")
        published = published_tag.get("content", "") if published_tag and published_tag.name == "meta" else published_tag.get_text(" ", strip=True) if published_tag else ""
        main = soup.find("article") or soup.find("main") or soup.find(attrs={"role": "main"}) or soup.body
        text = main.get_text(" ", strip=True) if main else ""
    except ImportError:
        title_match = re.search(r"<title[^>]*>(.*?)</title>", html, re.IGNORECASE | re.DOTALL)
        if title_match:
            title = re.sub(r"<[^>]+>", " ", unescape(title_match.group(1))).strip()
        paragraphs = re.findall(r"<p[^>]*>(.*?)</p>", html, re.IGNORECASE | re.DOTALL)
        text = " ".join(re.sub(r"<[^>]+>", " ", unescape(part)).strip() for part in paragraphs)
    return {"title": (title or "Untitled article")[:300], "url": url, "source": urlparse(url).netloc, "published": published, "text": text[:8000]}


def _deduplicate(stories: list[dict[str, str]]) -> list[dict[str, str]]:
    seen: set[str] = set()
    unique = []
    for story in stories:
        key = story.get("url", "") or story.get("title", "").lower()
        if key and key not in seen:
            seen.add(key)
            unique.append(story)
    return unique


def _scrape_technology_page(url: str) -> dict[str, str]:
    """Scrape one public article URL after applying the configured domain policy."""
    return _scrape_url(url)[0]


def build_tools(storage: Storage) -> list[Tool]:
    return [
        Tool("tasks_list", "List personal tasks.", {"type": "object"}, "read_only", storage.list_tasks),
        Tool("tasks_create", "Create a personal task.", {"type": "object", "properties": {"title": {"type": "string"}}, "required": ["title"]}, "write_requires_confirmation", storage.add_task),
        Tool("tasks_complete", "Complete a personal task.", {"type": "object", "properties": {"task_id": {"type": "integer"}}, "required": ["task_id"]}, "write_requires_confirmation", storage.complete_task),
        Tool("reminders_list", "List scheduled reminders.", {"type": "object"}, "read_only", storage.list_reminders),
        Tool("reminders_create", "Schedule a reminder.", {"type": "object", "properties": {"text": {"type": "string"}, "minutes": {"type": "integer"}}, "required": ["text", "minutes"]}, "write_requires_confirmation", lambda text, minutes: storage.add_reminder(text, datetime.now(timezone.utc) + timedelta(minutes=minutes))),
        Tool("news_latest", "Fetch latest technology stories from RSS feeds and configured public web pages.", {"type": "object", "properties": {"limit": {"type": "integer"}}}, "read_only", _news),
        Tool("news_scrape_page", "Scrape one public technology article page for its title and readable text.", {"type": "object", "properties": {"url": {"type": "string"}}, "required": ["url"]}, "read_only", _scrape_technology_page),
    ]
