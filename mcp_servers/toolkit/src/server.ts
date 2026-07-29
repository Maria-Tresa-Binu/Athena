import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { Toolkit } from "@zilobase/toolkit";
import { randomUUID } from "node:crypto";
import { createServer } from "node:http";
import { readFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { z } from "zod";

loadProjectEnv();

const apiKey = process.env.TOOLKIT_API_KEY;
if (!apiKey) {
  throw new Error("TOOLKIT_API_KEY is required to start the Toolkit MCP bridge");
}

const toolkit = new Toolkit({
  apiKey,
  baseUrl: process.env.TOOLKIT_BASE_URL,
});

const defaultUserId = process.env.TOOLKIT_USER_ID || "athena-user";
const callbackPort = Number(process.env.TOOLKIT_CALLBACK_PORT || "8765");
const callbackUrl = process.env.TOOLKIT_RETURN_URL || `http://localhost:${callbackPort}/toolkit/callback`;

function loadProjectEnv(): void {
  const envPath = resolve(dirname(fileURLToPath(import.meta.url)), "../../../var_local.env");
  try {
    const contents = readFileSync(envPath, "utf8");
    for (const rawLine of contents.split(/\r?\n/)) {
      const line = rawLine.trim();
      if (!line || line.startsWith("#") || !line.includes("=")) continue;
      const separator = line.indexOf("=");
      const key = line.slice(0, separator).trim();
      const value = line.slice(separator + 1).trim().replace(/^['"]|['"]$/g, "");
      if (key && !process.env[key]) process.env[key] = value;
    }
  } catch {
    // Shell environment variables remain the primary configuration path.
  }
}

const server = new McpServer({
  name: "athena-toolkit",
  version: "0.1.0",
});

const pendingAuthorizations = new Map<string, any>();

function json(value: unknown) {
  return { content: [{ type: "text" as const, text: JSON.stringify(value, null, 2) }] };
}

server.tool(
  "toolkit_list_connectors",
  "List connectors available from the Toolkit backend.",
  {},
  async () => json(await toolkit.connectors.list()),
);

server.tool(
  "toolkit_authorize",
  "Start OAuth authorization for Gmail or Google Calendar. Open the returned redirectUrl in a browser.",
  {
    userId: z.string().default(defaultUserId).describe("Stable Athena user identifier"),
    connector: z.enum(["gmail", "google-calendar"]),
    returnUrl: z.string().url().default(callbackUrl),
    read: z.literal("all").default("all"),
    write: z.array(z.string()).default([]),
  },
  async ({ userId, connector, returnUrl, read, write }) => {
    const request = await toolkit.connectors.authorize(userId, connector, { returnUrl, read, write });
    const requestId = randomUUID();
    pendingAuthorizations.set(requestId, request);
    return json({ requestId, redirectUrl: request.redirectUrl, message: "Open redirectUrl to authorize the connector, then ask Athena to check the request." });
  },
);

server.tool(
  "toolkit_wait_for_connection",
  "Wait for a previously started Toolkit OAuth authorization to finish.",
  { requestId: z.string() },
  async ({ requestId }) => {
    const request = pendingAuthorizations.get(requestId);
    if (!request) return json({ error: "Unknown or expired authorization request" });
    try {
      return json(await request.waitForConnection());
    } finally {
      pendingAuthorizations.delete(requestId);
    }
  },
);

server.tool(
  "toolkit_list_tools",
  "List available provider tools for a connected user. Use read='all' and write=[] for safe discovery.",
  {
    userId: z.string().default(defaultUserId),
    connectors: z.array(z.string()).default(["gmail", "google-calendar"]),
    read: z.literal("all").default("all"),
    write: z.array(z.string()).default([]),
  },
  async ({ userId, connectors, read, write }) => json(await toolkit.tools.list(userId, { connectors, read, write })),
);

server.tool(
  "toolkit_search",
  "Search the Toolkit catalog for the best Gmail or Google Calendar tool for a request.",
  {
    query: z.string(),
    userId: z.string().default(defaultUserId),
    connectors: z.array(z.string()).default(["gmail", "google-calendar"]),
  },
  async ({ query, userId, connectors }) => json(await toolkit.tools.search(query, { userId, connectors })),
);

server.tool(
  "toolkit_execute",
  "Execute one selected Toolkit tool. The bridge blocks write-capable actions unless TOOLKIT_ALLOW_WRITES=true.",
  {
    toolName: z.string(),
    userId: z.string().default(defaultUserId),
    arguments: z.record(z.string(), z.unknown()).default({}),
  },
  async ({ toolName, userId, arguments: toolArguments }) => {
    if (!process.env.TOOLKIT_ALLOW_WRITES && isLikelyWriteTool(toolName)) {
      return json({ error: "Write action blocked. Confirm the action and set TOOLKIT_ALLOW_WRITES=true in the trusted server environment." });
    }
    return json(await toolkit.tools.execute(toolName, { userId, arguments: toolArguments }));
  },
);

function isLikelyWriteTool(toolName: string): boolean {
  return /(^|[._-])(send|reply|create|update|delete|remove|trash|archive|mark_read|mark_unread|complete|cancel)([._-]|$)/i.test(toolName);
}

const transport = new StdioServerTransport();
await server.connect(transport);

const callbackServer = createServer((request, response) => {
  const requestUrl = new URL(request.url || "/", `http://${request.headers.host || "localhost"}`);
  if (requestUrl.pathname !== "/toolkit/callback") {
    response.writeHead(404, { "content-type": "text/plain; charset=utf-8" });
    response.end("Not found");
    return;
  }
  response.writeHead(200, { "content-type": "text/html; charset=utf-8" });
  response.end("<!doctype html><html><body><h1>Athena is connected</h1><p>You can close this tab and return to Athena.</p></body></html>");
});

callbackServer.on("error", (error) => {
  console.error(`Toolkit OAuth callback server failed on port ${callbackPort}:`, error);
});
callbackServer.listen(callbackPort, "127.0.0.1");
