import re
from typing import Any

from .models import Tool


class Athena:
    def __init__(self, tools: list[Tool]) -> None:
        self.tools = {tool.name: tool for tool in tools}
        self.pending: tuple[Tool, dict[str, Any]] | None = None

    def handle(self, text: str) -> str:
        command = text.strip()
        if not command:
            return "I’m listening."
        if self.pending:
            if command.lower() in {"yes", "y", "confirm", "do it"}:
                tool, arguments = self.pending
                self.pending = None
                return self._execute(tool, arguments)
            self.pending = None
            return "Cancelled."
        lowered = command.lower()
        if lowered in {"help", "what can you do"}:
            return "I can manage tasks and reminders, and fetch technology news. Gmail and Calendar integrations are next."
        if lowered in {"quit", "exit", "goodbye"}:
            return "Goodbye."
        if "latest" in lowered and ("news" in lowered or "technology" in lowered):
            return self._execute(self.tools["news_latest"], {"limit": 5})
        if lowered in {"show my tasks", "list tasks", "my tasks"}:
            return self._execute(self.tools["tasks_list"], {})
        if lowered in {"show my reminders", "list reminders", "my reminders"}:
            return self._execute(self.tools["reminders_list"], {})
        match = re.match(r"add task (.+)", command, re.IGNORECASE)
        if match:
            return self._request_confirmation(self.tools["tasks_create"], {"title": match.group(1).strip()})
        match = re.match(r"remind me to (.+) in (\d+) minutes?", command, re.IGNORECASE)
        if match:
            return self._request_confirmation(self.tools["reminders_create"], {"text": match.group(1).strip(), "minutes": int(match.group(2))})
        return "I don’t know how to do that yet. Say ‘help’ to see what I can do."

    def _request_confirmation(self, tool: Tool, arguments: dict[str, Any]) -> str:
        self.pending = (tool, arguments)
        return f"Please confirm: run {tool.name} with {arguments}? Say yes or cancel."

    def _execute(self, tool: Tool, arguments: dict[str, Any]) -> str:
        try:
            result = tool.handler(**arguments)
        except Exception as exc:
            return f"That failed safely: {exc}"
        if tool.name == "news_latest":
            return "\n".join(f"{i}. {item['title']} — {item['source']} ({item['url']})" for i, item in enumerate(result, 1)) or "I couldn’t find any stories."
        if tool.name == "tasks_list":
            return "\n".join(f"{item['id']}. [{'x' if item['completed'] else ' '}] {item['title']}" for item in result) or "You have no tasks."
        if tool.name == "reminders_list":
            return "\n".join(f"{item['id']}. {item['text']} at {item['remind_at']}" for item in result) or "You have no reminders."
        return f"Done: {result}"
