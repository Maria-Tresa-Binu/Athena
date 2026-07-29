# MCP server boundaries

The application host currently uses local tool implementations so the core behavior can be tested without credentials. These folders are reserved for independently deployable MCP servers:

- `news`: RSS/news provider tools
- `gmail`: Google OAuth-backed read and draft/send tools
- `calendar`: Google Calendar tools
- `tasks`: task provider tools
- `reminders`: reminder CRUD tools

Each server should expose narrow tools and declare read-only versus write behavior in its metadata. The host must keep confirmation and authorization decisions outside the tool implementation.

The local News MCP server is implemented at `news/server.py` and is loaded automatically by LangGraph mode.
