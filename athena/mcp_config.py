"""Configuration for Athena's MCP connections."""

import json
import os
from typing import Any


def server_config() -> dict[str, dict[str, Any]]:
    """Return MultiServerMCPClient configuration from environment variables.

    Configure remote servers with ATHENA_MCP_SERVERS_JSON, for example:
    {"calendar": {"transport": "http", "url": "http://localhost:8001/mcp"}}
    """
    raw = os.getenv("ATHENA_MCP_SERVERS_JSON", "").strip()
    if raw:
        value = json.loads(raw)
        if not isinstance(value, dict):
            raise ValueError("ATHENA_MCP_SERVERS_JSON must be a JSON object")
        return value

    url = os.getenv("ATHENA_MCP_URL", "").strip()
    if url:
        return {"athena_remote": {"transport": "http", "url": url}}
    return {}
