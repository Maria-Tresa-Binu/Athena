# Athena

Personal voice assistant built around an MCP-style tool architecture.

## Current MVP

- Text CLI that is ready to sit behind a wake-word and voice adapter.
- MCP-inspired tool registry with names, descriptions, schemas, and safety metadata.
- Local tasks and reminders stored in SQLite.
- Technology news lookup through RSS feeds.
- Confirmation gates for write and destructive operations.

## Run

Requires Python 3.11+.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m athena
```

The default database is in-memory for a permission-safe demo. Set `ATHENA_DB_PATH` to a writable file path to persist tasks and reminders between runs.

On Windows, Athena speaks responses using the built-in System.Speech voice engine. Use `python -m athena --text-only` to disable speech for tests or silent environments. This is the response/audio layer; microphone input, wake-word detection, and full speech-to-speech sessions will be added separately.

## LangChain and LangGraph mode

Install the optional agent stack:

```powershell
pip install -r requirements-langgraph.txt
```

Configure at least one MCP server using `ATHENA_MCP_URL` or `ATHENA_MCP_SERVERS_JSON`, then run:

```powershell
python -m athena --langgraph
```

LangGraph mode exposes read-only MCP tools by default. Use `--allow-writes` only after adding a real approval workflow for mail, calendar, and other mutating tools.

Try commands such as:

```text
show my tasks
add task Prepare Athena demo
remind me to stretch in 30 minutes
what is the latest technology news?
help
quit
```

The current interface is intentionally text-based so the core assistant can be tested before adding microphone, wake-word, and speech-to-speech concerns. Integrations for Gmail and Google Calendar will use OAuth and will be added behind separate MCP servers.

## Layout

```text
athena/       application host, routing, storage, and tool registry
mcp_servers/  integration boundaries for future remote/local MCP servers
tests/        automated checks
```

Never commit OAuth credentials, refresh tokens, or `.env` files.
