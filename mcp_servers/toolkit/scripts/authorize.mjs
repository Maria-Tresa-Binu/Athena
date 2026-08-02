import { readFileSync } from "node:fs";
import { Toolkit } from "@zilobase/toolkit";

function loadProjectEnv() {
  const values = {};
  const contents = readFileSync(new URL("../../../var_local.env", import.meta.url), "utf8");
  for (const rawLine of contents.split(/\r?\n/)) {
    const line = rawLine.trim();
    if (!line || line.startsWith("#") || !line.includes("=")) continue;
    const separator = line.indexOf("=");
    values[line.slice(0, separator).trim()] = line.slice(separator + 1).trim().replace(/^['"]|['"]$/g, "");
  }
  return values;
}

function argument(name, fallback) {
  const index = process.argv.indexOf(name);
  return index >= 0 ? process.argv[index + 1] : fallback;
}

const env = loadProjectEnv();
const connector = argument("--connector", "gmail");
const userId = argument("--user-id", env.TOOLKIT_USER_ID || "athena-user");
const returnUrl = argument("--return-url", process.env.TOOLKIT_RETURN_URL || "");

if (!env.TOOLKIT_API_KEY) throw new Error("TOOLKIT_API_KEY is missing from var_local.env");
if (!/^https:\/\//i.test(returnUrl)) {
  throw new Error("A public HTTPS return URL is required. Pass the current tunnel callback URL with --return-url.");
}

const toolkit = new Toolkit({ apiKey: env.TOOLKIT_API_KEY, baseUrl: env.TOOLKIT_BASE_URL });
const request = await toolkit.connectors.authorize(userId, connector, {
  returnUrl,
  read: "all",
  write: [],
});

console.log(`Toolkit authorization started for ${connector} (${userId}).`);
console.log(`Open this URL in your browser:\n${request.redirectUrl}`);
console.log("Waiting for the provider callback...");

const connection = await request.waitForConnection();
console.log("Toolkit connection completed:");
console.log(JSON.stringify(connection, null, 2));
