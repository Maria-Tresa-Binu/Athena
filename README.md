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

Athena prefers the female `Microsoft Zira Desktop` voice and falls back to another installed female voice. Set `ATHENA_VOICE` to an installed Windows voice name to choose a different voice.

## LangChain and LangGraph mode

Install the optional agent stack:

```powershell
pip install -r requirements-langgraph.txt
ollama pull llama3.1
```

Make sure Ollama is running locally. Athena automatically starts its local News MCP server; configure additional MCP servers with `ATHENA_MCP_URL` or `ATHENA_MCP_SERVERS_JSON`, then run:

```powershell
python -m athena --langgraph
```

To bypass environment-variable issues, specify the model directly:

```powershell
python -m athena --langgraph --model llama3.2:latest
```

If Athena reports that Ollama is not reachable, start it first:

```powershell
ollama serve
```

Then verify the model is installed with `ollama list`. The model name in `ATHENA_LLM_MODEL` must match an installed model, such as `llama3.1` or `llama3.1:8b`.

LangGraph mode exposes read-only MCP tools by default. Use `--allow-writes` only after adding a real approval workflow for mail, calendar, and other mutating tools.

LangGraph mode keeps the conversation history—including MCP tool results—across turns, so you can ask follow-ups such as “summarize the second story” or “what does that article mean?”. Say `new chat` or `reset conversation` to clear the context. Every final answer is sent to Athena’s speech output.

### Web-scraped tech news

RSS remains the preferred source. To add public webpages as a fallback, configure URLs and optionally restrict domains:

```powershell
$env:ATHENA_NEWS_SCRAPE_URLS="https://example.com/technology/article"
$env:ATHENA_ALLOWED_SCRAPE_DOMAINS="example.com"
python -m athena --langgraph
```

Athena also exposes the `scrape_technology_page` MCP tool for one-off public article extraction. Use scraping only where the website permits it, keep request rates low, and do not scrape private or login-protected pages.

### Gmail and Google Calendar through Toolkit

The optional Node bridge in `mcp_servers/toolkit` connects Athena to the hosted Zilobase Toolkit backend. Build it with `npm install` and `npm run build`, then set `TOOLKIT_API_KEY`. Athena will automatically discover the bridge as a local MCP server; no `ATHENA_MCP_URL` is required.

Toolkit write actions are blocked by default. Keep `TOOLKIT_ALLOW_WRITES` unset while testing reads. Enable it only after adding explicit confirmation in the assistant flow.

The Toolkit bridge starts a local OAuth callback at `http://localhost:8765/toolkit/callback`. After starting Athena, say `authorize my Gmail account` or `authorize my Google Calendar account`, open the authorization link Athena provides, approve access, and return to the terminal.

## Web app for phone access

Install the web dependencies and start Athena's mobile UI:

```powershell
python -m pip install -r requirements-web.txt
python -m athena.web --host 0.0.0.0 --port 8080
```

On the same Wi-Fi network, find this computer's local IP with `ipconfig` and open `http://YOUR-PC-IP:8080` on your phone. The page supports chat, browser microphone input, and browser speech output. Keep this local-only until authentication and HTTPS are added; do not expose a personal Gmail/calendar assistant directly to the public internet.

Athena loads credentials from `var_local.env` as well as the shell environment. Copy `.env.example` to `var_local.env`, add your real Toolkit key there, and never commit `var_local.env`.

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
