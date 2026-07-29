"""Local MCP server exposing current technology news from RSS feeds."""

import sys
from pathlib import Path

# Allow this stdio server to be launched directly from any working directory.
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from fastmcp import FastMCP

from athena.tools import _news, _scrape_technology_page


mcp = FastMCP("Athena News")


@mcp.tool()
def latest_technology_news(limit: int = 5) -> list[dict[str, str]]:
    """Fetch latest technology stories from RSS and configured public web pages."""
    return _news(limit=max(1, min(limit, 10)))


@mcp.tool()
def scrape_technology_page(url: str) -> dict[str, str]:
    """Scrape one public article page and return readable text and metadata."""
    return _scrape_technology_page(url)


if __name__ == "__main__":
    mcp.run(transport="stdio")
