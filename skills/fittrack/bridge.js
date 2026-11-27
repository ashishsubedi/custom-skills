#!/usr/bin/env node
const fs = require('fs');
const path = require('path');
const readline = require('readline');

const ENDPOINT = process.env.FITTRACK_URL || getConfigVar("FITTRACK_URL") || "https://mcp.fitness.randomaiwebsite.com/mcp";

function getConfigVar(varName) {
  if (process.env[varName]) return process.env[varName].trim();

  // Fallback: check shell and gemini configuration files if not inherited in GUI environment
  const homedir = require('os').homedir();
  const candidates = [
    path.join(homedir, '.gemini', 'fittrack.env'),
    path.join(homedir, '.zshenv'),
    path.join(homedir, '.zprofile'),
    path.join(homedir, '.zshrc')
  ];

  const reExport = new RegExp(`export\\s+${varName}=["']?([^"'\\s\\n]+)["']?`);
  const rePlain = new RegExp(`${varName}=["']?([^"'\\s\\n]+)["']?`);

  for (const file of candidates) {
    try {
      if (fs.existsSync(file)) {
        const content = fs.readFileSync(file, 'utf8');
        const match = content.match(reExport) || content.match(rePlain);
        if (match && match[1]) {
          return match[1].trim();
        }
      }
    } catch (_) {}
  }
  return null;
}

function getApiKey() {
  return getConfigVar("FITTRACK_API_KEY") || getConfigVar("FITTRACK_AGENT_KEY");
}

const rl = readline.createInterface({
  input: process.stdin,
  output: process.stdout,
  terminal: false
});

rl.on('line', async (line) => {
  const trimmed = line.trim();
  if (!trimmed) return;

  let msg;
  try {
    msg = JSON.parse(trimmed);
  } catch (err) {
    process.stderr.write(`[fittrack-bridge] Invalid JSON: ${trimmed}\n`);
    return;
  }

  // Handle notifications (no response needed)
  if (msg.method && msg.method.startsWith("notifications/")) {
    return;
  }

  // Handle ping
  if (msg.method === "ping") {
    sendResponse({ jsonrpc: "2.0", id: msg.id, result: {} });
    return;
  }

  const apiKey = getApiKey();
  const headers = { "Content-Type": "application/json" };
  if (apiKey) {
    headers["Authorization"] = `Bearer ${apiKey}`;
    headers["x-fittrack-key"] = apiKey;
  }

  try {
    const res = await fetch(ENDPOINT, {
      method: "POST",
      headers,
      body: JSON.stringify(msg)
    });
    const data = await res.json();
    sendResponse(data);
  } catch (err) {
    sendResponse({
      jsonrpc: "2.0",
      id: msg.id,
      error: {
        code: -32603,
        message: `FitTrack bridge error: ${err.message}`
      }
    });
  }
});

function sendResponse(obj) {
  process.stdout.write(JSON.stringify(obj) + "\n");
}
