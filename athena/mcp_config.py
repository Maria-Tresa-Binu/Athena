"""Configuration for Athena's MCP connections."""

import json
import os
import sys
from pathlib import Path
from typing import Any


def server_config() -> dict[str, dict[str, Any]]:
    """Return MultiServerMCPClient configuration from environment variables.

    Configure remote servers with ATHENA_MCP_SERVERS_JSON, for example:
    {"calendar": {"transport": "http", "url": "http://localhost:8001/mcp"}}
    """
    _load_dotenv()
    raw = os.getenv("ATHENA_MCP_SERVERS_JSON", "").strip()
    if raw:
        value = json.loads(raw)
        if not isinstance(value, dict):
            raise ValueError("ATHENA_MCP_SERVERS_JSON must be a JSON object")
        return value

    url = os.getenv("ATHENA_MCP_URL", "").strip()
    configs = {"news": _local_news_server()}
    if url:
        configs["athena_remote"] = {"transport": "http", "url": url}
    if os.getenv("TOOLKIT_API_KEY", "").strip():
        configs["toolkit"] = _local_toolkit_server()
    return configs


def _load_dotenv() -> None:
    """Load simple KEY=VALUE entries from project var_local.env without overwriting the shell."""
    path = Path(__file__).resolve().parents[1] / "var_local.env"
    if not path.exists():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


def _local_news_server() -> dict[str, Any]:
    server = Path(__file__).resolve().parents[1] / "mcp_servers" / "news" / "server.py"
    return {
        "transport": "stdio",
        "command": sys.executable,
        "args": [str(server)],
    }


def _local_toolkit_server() -> dict[str, Any]:
    root = Path(__file__).resolve().parents[1] / "mcp_servers" / "toolkit"
    return {
        "transport": "stdio",
        "command": "node",
        "args": [str(root / "dist" / "server.js")],
        "cwd": str(root),
    }
