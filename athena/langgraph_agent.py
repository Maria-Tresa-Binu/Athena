"""Optional LangChain/LangGraph agent host for Athena."""

import os
import json
import re
import sys
from typing import Any

from .mcp_config import server_config


class LangGraphUnavailable(RuntimeError):
    pass


class LangGraphAthena:
    """Lazy MCP-backed agent so the standard-library CLI remains usable."""

    def __init__(self, model: str = "llama3.2:latest", allow_writes: bool = False) -> None:
        self.model = model
        self.allow_writes = allow_writes
        self._agent: Any = None
        self._client: Any = None
        self._messages: list[Any] = []
        self._tools: dict[str, Any] = {}
        self._last_authorization_request_id: str | None = None

    async def _initialize(self) -> None:
        try:
            from langchain.agents import create_agent
            from langchain_mcp_adapters.client import MultiServerMCPClient
            from langchain_ollama import ChatOllama
        except ImportError as exc:
            raise LangGraphUnavailable(
                "LangGraph mode requires: pip install -r requirements-langgraph.txt"
            ) from exc

        configs = server_config()
        if not configs:
            raise LangGraphUnavailable(
                "No MCP server configured. Set ATHENA_MCP_URL or ATHENA_MCP_SERVERS_JSON."
            )
        self._client = MultiServerMCPClient(configs)
        try:
            tools = await self._client.get_tools()
        except BaseException as exc:
            raise LangGraphUnavailable(f"MCP server startup failed: {format_failure(exc)}") from exc
        if not self.allow_writes:
            tools = [tool for tool in tools if not _is_write_tool(tool)]
        self._tools = {getattr(tool, "name", ""): tool for tool in tools}
        llm = ChatOllama(
            model=self.model.removeprefix("ollama:"),
            base_url=__import__("os").getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
            temperature=0,
        )
        self._agent = create_agent(
            model=llm,
            tools=tools,
            system_prompt=(
                "You are Athena, a concise personal assistant. "
                "Use MCP tools for current or personal information. "
                "OAuth authorization for the user's explicitly requested Gmail or Google Calendar connection is an allowed setup action. "
                "For authorization, use the provided toolkit_authorize MCP tool; never invent a CLI command, redirect_uri parameter, access-token exchange, or user email as a userId. "
                "Tell the user to open the redirectUrl returned by the tool and then return to Athena. "
                "Never claim an action succeeded unless the tool confirms it. "
                "Write tools are disabled unless explicitly enabled by the host."
            ),
        )

    async def ask(self, text: str) -> str:
        if self._agent is None:
            await self._initialize()
        authorization = _requested_connector_authorization(text)
        if authorization:
            return await self._authorize_connector(authorization)
        if self._last_authorization_request_id:
            connection_result = await self._wait_for_connection()
            if connection_result.startswith("{") and '"error"' in connection_result:
                return connection_result
        self._messages.append({"role": "user", "content": text})
        result = await self._agent.ainvoke({"messages": self._messages})
        # Preserve the complete conversation, including MCP tool calls/results,
        # so follow-up questions can refer to fetched data.
        self._messages = result.get("messages", self._messages)
        return _last_text(result)

    async def _authorize_connector(self, connector: str) -> str:
        tool = self._tools.get("toolkit_authorize")
        if tool is None:
            return "The Toolkit authorization tool is not connected. Set TOOLKIT_API_KEY and rebuild the Toolkit bridge."
        result = await tool.ainvoke({
            "userId": os.getenv("TOOLKIT_USER_ID", "athena-user"),
            "connector": connector,
            "read": "all",
            "write": [],
        })
        text = _tool_result_text(result)
        try:
            payload = json.loads(text)
            self._last_authorization_request_id = payload.get("requestId")
            redirect_url = payload.get("redirectUrl")
            if redirect_url:
                print(f"[Athena] Toolkit redirectUrl received: {redirect_url}", file=sys.stderr, flush=True)
                print(f"[Athena] Toolkit requestId received: {self._last_authorization_request_id}", file=sys.stderr, flush=True)
            else:
                print(f"[Athena] Toolkit response did not contain redirectUrl: {text}", file=sys.stderr, flush=True)
        except (json.JSONDecodeError, AttributeError, TypeError):
            print(f"[Athena] Could not parse Toolkit authorization response: {text}", file=sys.stderr, flush=True)
        return text

    async def _wait_for_connection(self) -> str:
        tool = self._tools.get("toolkit_wait_for_connection")
        if tool is None or not self._last_authorization_request_id:
            return "There is no pending Toolkit authorization request."
        result = await tool.ainvoke({"requestId": self._last_authorization_request_id})
        self._last_authorization_request_id = None
        return _tool_result_text(result)

    def reset(self) -> None:
        """Start a fresh conversation without rebuilding the MCP client."""
        self._messages = []


def _is_write_tool(tool: Any) -> bool:
    name = getattr(tool, "name", "").lower()
    description = getattr(tool, "description", "").lower()
    write_words = ("create", "send", "delete", "update", "cancel", "complete", "archive", "write")
    return any(word in name or word in description for word in write_words)


def _requested_connector_authorization(text: str) -> str | None:
    lowered = text.lower()
    oauth_placeholder = "mcp.google.com" in lowered or "your_client_id" in lowered or "redirect_uri" in lowered
    if not oauth_placeholder and not re.search(r"\b(authenticate|athenticate|authorize|connect|link)\b", lowered):
        return None
    if "gmail" in lowered or "email" in lowered or oauth_placeholder:
        return "gmail"
    if "calendar" in lowered:
        return "google-calendar"
    return None


def _tool_result_text(result: Any) -> str:
    if isinstance(result, str):
        return result
    content = getattr(result, "content", None)
    if content is not None:
        return _tool_result_text(content)
    if isinstance(result, list):
        return "\n".join(_tool_result_text(item) for item in result)
    if isinstance(result, dict):
        return result.get("text") or str(result)
    return str(result)


def _last_text(result: dict[str, Any]) -> str:
    messages = result.get("messages", [])
    for message in reversed(messages):
        content = getattr(message, "content", None)
        if content is None and isinstance(message, dict):
            content = message.get("content")
        if isinstance(content, str) and content.strip():
            return content
        if isinstance(content, list):
            text = " ".join(block.get("text", "") for block in content if isinstance(block, dict))
            if text.strip():
                return text
    return "I completed the request but received no spoken response."


def format_failure(exc: BaseException) -> str:
    """Flatten Python 3.11 exception groups into useful user-facing diagnostics."""
    messages: list[str] = []

    def collect(error: BaseException) -> None:
        if isinstance(error, BaseExceptionGroup):
            for child in error.exceptions:
                collect(child)
            return
        message = str(error).strip()
        if message:
            messages.append(f"{type(error).__name__}: {message}")

    collect(exc)
    detail = " | ".join(dict.fromkeys(messages)) or type(exc).__name__
    lowered = detail.lower()
    if "11434" in lowered or "connection refused" in lowered:
        return f"Ollama is not reachable at OLLAMA_BASE_URL (start Ollama with 'ollama serve'). Details: {detail}"
    if "fastmcp" in lowered or "module not found" in lowered or "no module named" in lowered:
        return f"Install the LangGraph/MCP dependencies with 'pip install -r requirements-langgraph.txt'. Details: {detail}"
    return detail
