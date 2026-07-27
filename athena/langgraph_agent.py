"""Optional LangChain/LangGraph agent host for Athena."""

from typing import Any

from .mcp_config import server_config


class LangGraphUnavailable(RuntimeError):
    pass


class LangGraphAthena:
    """Lazy MCP-backed agent so the standard-library CLI remains usable."""

    def __init__(self, model: str = "openai:gpt-4o-mini", allow_writes: bool = False) -> None:
        self.model = model
        self.allow_writes = allow_writes
        self._agent: Any = None
        self._client: Any = None

    async def _initialize(self) -> None:
        try:
            from langchain.agents import create_agent
            from langchain_mcp_adapters.client import MultiServerMCPClient
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
        tools = await self._client.get_tools()
        if not self.allow_writes:
            tools = [tool for tool in tools if not _is_write_tool(tool)]
        self._agent = create_agent(
            model=self.model,
            tools=tools,
            system_prompt=(
                "You are Athena, a concise personal assistant. "
                "Use MCP tools for current or personal information. "
                "Never claim an action succeeded unless the tool confirms it. "
                "Write tools are disabled unless explicitly enabled by the host."
            ),
        )

    async def ask(self, text: str) -> str:
        if self._agent is None:
            await self._initialize()
        result = await self._agent.ainvoke({"messages": [{"role": "user", "content": text}]})
        return _last_text(result)


def _is_write_tool(tool: Any) -> bool:
    name = getattr(tool, "name", "").lower()
    description = getattr(tool, "description", "").lower()
    write_words = ("create", "send", "delete", "update", "cancel", "complete", "archive", "write")
    return any(word in name or word in description for word in write_words)


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
