# Toolkit MCP bridge

This server keeps `TOOLKIT_API_KEY` on the trusted Node side and exposes the hosted Zilobase Toolkit backend to Athena over local MCP stdio.

## Setup

```powershell
cd mcp_servers/toolkit
npm install
npm run build
```

Set `TOOLKIT_API_KEY` before starting Athena. Optionally set `TOOLKIT_BASE_URL` for a local Toolkit backend.

The bridge starts a local OAuth return page at `http://localhost:8765/toolkit/callback`. After Athena starts, ask it to authorize Gmail or Google Calendar. Open the returned authorization URL, approve access, and return to Athena.

The bridge exposes connector authorization, tool discovery/search, and one generic execute tool. Keep the execute tool read-only until Athena's approval flow is enabled for writes.
