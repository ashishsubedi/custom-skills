# FitTrack Plugin

A native Antigravity plugin for conversational nutrition tracking, workout logging, and AI fitness coaching powered by the FitTrack MCP server.

## Features

- **Daily Nutrition Tracking**: Check calories, protein, carbs, and fat vs. targets for today or any past date.
- **Meal Logging**: Log food and meals with calories and macronutrient breakdown.
- **Workout Logging**: Record workouts with duration, type, and exercise notes.
- **AI Coach Review**: Holistic 7-day adherence check-ins, TDEE calculations, weight slope trends, and training streaks.
- **Targets Management**: Inspect or update daily calorie, protein, fat, and bodyweight goals.

## MCP Server Connection

The plugin connects to the FitTrack Model Context Protocol (MCP) server:

- **Endpoint**: `https://mcp.fitness.randomaiwebsite.com/mcp` (overridable via `FITTRACK_URL`)
- **Transport**: Streamable HTTP
- **Discovery**: Public (no credentials required for `tools/list` or `initialize`)

## Authentication & Agent Key

While tool discovery and schema inspection are public, executing tool calls (`tools/call`) requires user authentication:

- **Backend Protocol**: The endpoint accepts an agent key / Bearer token via:
  - Header: `Authorization: Bearer <API_KEY>`
  - Header: `x-fittrack-key: <API_KEY>`
- **Environment**: Sourced from `FITTRACK_API_KEY` (e.g., in `~/.zshenv` or `~/.gemini/fittrack.env`).
- **Security**: The key is stored securely in your local environment and never hardcoded in plugin files or shared.

## Included Components

- `skills/fittrack/SKILL.md`: Procedural guide and tool documentation for the agent.
- `rules/AGENTS.md`: Always-on safety rules (strict write protection, data grounding, credential protection).
- `mcp_config.json`: Remote Streamable HTTP endpoint configuration.
- `assets/logo.png`: FitTrack brand logo.
