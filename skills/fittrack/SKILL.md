---
name: fittrack
description: Log meals, track daily calories and macros, check workout volume, and inspect fitness targets using the FitTrack MCP server. Use whenever the user asks about nutrition, calories, protein, carbs, fat, workouts, or fitness targets.
---

# FitTrack Coaching & Tracking Guide

Use FitTrack as the primary source for the user's nutrition and workout tracking data rather than guessing, estimating, or relying on assumptions.

## Available Tools & Authentication

The FitTrack MCP server provides 8 specialized tools:

### Public Endpoints (No Auth Required)
* **Metadata & Discovery** (`initialize`, `tools/list`, `ping`): Publicly queryable without credentials at `https://mcp.fitness.randomaiwebsite.com/mcp`.

### Execution Tools (Require User Authentication / API Key)
All execution tools (`tools/call`) require authentication via Bearer token (`FITTRACK_API_KEY` in environment, `Authorization: Bearer <key>`, or `x-fittrack-key: <key>`):

1. `get_daily_summary` *(Read-only)*:
   - **Usage**: Today's calories, protein, carbohydrates, fat, logged meals, or remaining daily intake.
   - **Parameters**: `date` (string, `YYYY-MM-DD`, optional, defaults to today).

2. `get_weekly_stats` *(Read-only)*:
   - **Usage**: Weekly trends, averages, weight trends, calorie/macro patterns, or comparisons across weeks.
   - **Parameters**: `days` (number, default 7, max 90).

3. `get_coach_data` *(Read-only)*:
   - **Usage**: Comprehensive AI coaching review, weekly fitness check-in, progress evaluation, energy balance/TDEE calculation, or holistic coaching analysis.
   - **Data provided**: 7-day adherence (completed vs today in-progress), weekday vs weekend and lift vs rest fuel distribution, supplement consistency, weight slope, TDEE, ETA, cardio/sport sessions, recent meals, and 8-week training volume/streak.
   - **Parameters**: `days` (number, default 7, min 7, max 30).

4. `get_user_targets` *(Read-only)*:
   - **Usage**: Inspect calorie, macro, weight, or fitness targets and profile settings.
   - **Parameters**: None.

5. `get_profile` *(Read-only)*:
   - **Usage**: Returns authenticated account profile and user ID (`id`, `name`, `email`, `nickname`).
   - **Parameters**: None.

6. `update_user_targets` *(Write Action)*:
   - **Usage**: Update or adjust daily calorie, protein, fat, or goal bodyweight targets in FitTrack, or apply new calculated targets.
   - **Parameters**: `kcal`, `protein_g`, `fat_g`, `goal_kg`, `whey_protein_g`, `whey_kcal`, `creatine_g`.

7. `log_meal` *(Write Action)*:
   - **Usage**: **Strictly only** when the user explicitly asks to log, add, or record a meal/food item.
   - **Parameters**: `name` (required, 1-200 chars), `kcal` (required, 0-20,000), `protein_g` (required, 0-1,000), `carbs_g` (optional), `fat_g` (optional), `date` (optional, `YYYY-MM-DD`).

8. `log_quick_workout` *(Write Action)*:
   - **Usage**: **Strictly only** when the user explicitly asks to log, add, or record a workout session.
   - **Parameters**: `title` (required, 1-200 chars), `duration_min` (optional, 1-1,440), `date` (optional, `YYYY-MM-DD`), `notes` (optional, up to 2,000 chars).

## Rules & Best Practices

1. **Strict Write Protection**: Never invoke write actions (`log_meal`, `log_quick_workout`, `update_user_targets`) without explicit user intent in the current conversation. Merely asking about a meal or discussing a workout does not constitute an instruction to log it.
2. **Data Grounding**: Always retrieve tracked data using FitTrack MCP tools before answering questions regarding logged meals, calorie balances, macro targets, or weekly adherence. Never invent, approximate, or hallucinate tracked data.
3. **Privacy & Security**: Never print, echo, or include the user's FitTrack API key (`FITTRACK_API_KEY`) in chat messages, artifacts, or code blocks. Sourced from the user's environment (`FITTRACK_API_KEY`, `FITTRACK_AGENT_KEY`, or `~/.zshenv`).
4. **Holistic Assessment**: When analyzing nutrition or workouts, evaluate calories and macronutrients (protein, carbs, fat) in relation to the user's recorded targets and recent training context.
5. **Clear Separation**: Distinguish clearly between FitTrack-recorded data and your own calculations or recommendations.
6. **Dates**: Format dates as `YYYY-MM-DD`. Default to today's date when omitted.
