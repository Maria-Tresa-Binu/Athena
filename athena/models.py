from dataclasses import dataclass
from datetime import datetime
from typing import Any, Callable


@dataclass(frozen=True)
class Tool:
    """MCP-style tool metadata plus a local callable implementation."""

    name: str
    description: str
    input_schema: dict[str, Any]
    risk: str
    handler: Callable[..., Any]


@dataclass(frozen=True)
class Reminder:
    id: int
    text: str
    remind_at: datetime
    completed: bool = False
