import os
from datetime import datetime, timedelta, timezone
from urllib.request import urlopen
from xml.etree import ElementTree

from .models import Tool
from .storage import Storage


def _news(feeds: str | None = None, limit: int = 5) -> list[dict[str, str]]:
    urls = (feeds or os.getenv("ATHENA_NEWS_FEEDS", "https://feeds.arstechnica.com/arstechnica/technology-lab")).split(",")
    stories = []
    for url in urls:
        with urlopen(url.strip(), timeout=8) as response:
            root = ElementTree.fromstring(response.read())
        channel = root.find("channel")
        source = channel.findtext("title", url) if channel is not None else url
        for entry in (channel.findall("item") if channel is not None else [])[:limit]:
            stories.append({"title": entry.findtext("title", "Untitled"), "url": entry.findtext("link", ""), "source": source})
    return stories[:limit]


def build_tools(storage: Storage) -> list[Tool]:
    return [
        Tool("tasks_list", "List personal tasks.", {"type": "object"}, "read_only", storage.list_tasks),
        Tool("tasks_create", "Create a personal task.", {"type": "object", "properties": {"title": {"type": "string"}}, "required": ["title"]}, "write_requires_confirmation", storage.add_task),
        Tool("tasks_complete", "Complete a personal task.", {"type": "object", "properties": {"task_id": {"type": "integer"}}, "required": ["task_id"]}, "write_requires_confirmation", storage.complete_task),
        Tool("reminders_list", "List scheduled reminders.", {"type": "object"}, "read_only", storage.list_reminders),
        Tool("reminders_create", "Schedule a reminder.", {"type": "object", "properties": {"text": {"type": "string"}, "minutes": {"type": "integer"}}, "required": ["text", "minutes"]}, "write_requires_confirmation", lambda text, minutes: storage.add_reminder(text, datetime.now(timezone.utc) + timedelta(minutes=minutes))),
        Tool("news_latest", "Fetch latest technology stories from RSS feeds.", {"type": "object", "properties": {"limit": {"type": "integer"}}}, "read_only", _news),
    ]
