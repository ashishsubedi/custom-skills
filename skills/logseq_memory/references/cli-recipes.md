# Logseq CLI Recipes: Pure Skill Command Reference

This reference provides concrete `logseq` CLI commands for all memory operations.

> **Prerequisite**: The official `logseq-cli` skill is installed (`~/.agents/skills/logseq-cli`). All commands target `--graph "$GRAPH"`, resolved dynamically via `$LOGSEQ_GRAPH` or `~/.config/logseq_memory/graph` (fallback `~/.config/logseq-memory/graph`, configured during setup).

---

## 1. Context Discovery (Shell)

Discover project identity, branch slug, and target graph using portable commands:

```bash
# 1. Resolve active graph (configured during setup, e.g. logseq-sync or logseq-agent)
GRAPH="${LOGSEQ_GRAPH:-$(cat ~/.config/logseq_memory/graph 2>/dev/null || cat ~/.config/logseq-memory/graph 2>/dev/null || echo "logseq-sync")}"
CORE_PAGE="agent: core"

# 2. Detect Git repo vs Non-Git / .md-first Area
COMMON_DIR=$(git rev-parse --path-format=absolute --git-common-dir 2>/dev/null || true)
if [ -n "$COMMON_DIR" ]; then
  PROJECT=$(basename "$(dirname "$COMMON_DIR")")
  BRANCH_RAW=$(git branch --show-current 2>/dev/null || true)
  if [ -z "$BRANCH_RAW" ]; then
    BRANCH_SLUG=$(basename "$(git rev-parse --show-toplevel 2>/dev/null)")
  else
    BRANCH_SLUG=$(echo "$BRANCH_RAW" | tr '/' '-')
  fi
  PROJECT_PAGE="projects: $PROJECT"
  BRANCH_PAGE="$PROJECT: $BRANCH_SLUG"
  echo "Graph: $GRAPH | Mode: git | Project: $PROJECT_PAGE | Branch: $BRANCH_PAGE"
else
  AREA=$(basename "$PWD" | tr '[:upper:]' '[:lower:]')
  AREA_PAGE="area: $AREA"
  echo "Graph: $GRAPH | Mode: area | Page: $AREA_PAGE"
fi
```

---

## 2. Gate 1 — Orient & Bootstrap (Session Start)

Inspect relevant memory surfaces, scan for active agent tasks, and bootstrap missing/stub project pages.

### 2.1 Inspect Memory Surfaces
```bash
# Read global rules
logseq show --graph "$GRAPH" --page "agent: core"

# Read evergreen project knowledge
logseq show --graph "$GRAPH" --page "$PROJECT_PAGE"

# Read branch deep-dive
logseq show --graph "$GRAPH" --page "$BRANCH_PAGE"
```

### 2.2 Scan for Agent Tasks & Reviews (Targeted Datascript Query)
Scan for active tasks tagged `agent_task` across the graph:
```bash
logseq query --graph "$GRAPH" --query '[:find (pull ?b [:db/id :block/title :block/created-at :block/updated-at {:logseq.property/status [:block/title :db/ident]} {:block/tags [:block/title :block/name]} {:block/page [:block/title :block/name]} {:block/refs [:block/title :block/name]}]) :where [?t :block/name "agent_task"] [?b :block/tags ?t]]' --output json
```

> **Why Datascript over `list task`**: `list task` dumps hundreds of personal tasks (100+ KB) and omits tags and refs. Querying on `agent_task` returns only actionable agent tasks in milliseconds.

Check the query results for:
- Open reviews (`:logseq.property/status` = `"In Review"` or `"in-review"`).
- Late-answered reviews (status marked `done` by the human in Logseq): harvest decisions into the branch page and clean up the prompt block.
- Pending delegated tasks (`:logseq.property/status` = `"Todo"` or `"todo"`) matching `$BRANCH_PAGE` or `$PROJECT_PAGE`: claim with `--status doing`.

### 2.3 Bootstrap Invariant (Tech Lead Architecture & Runbook)
If `projects: $PROJECT` does not exist or has fewer than 6 structured sections, inspect the codebase and bootstrap the full Tech Lead System Architecture & Runbook using the template from [`page-templates.md`](page-templates.md).

---

## 3. Gate 2 — Fast In-Place Section Updates & Staleness Check

### 3.1 Fast In-Place Multi-Section Update Script
Use this copy-pasteable bash function to replace any section's content in place without creating duplicate headings or dropping link metadata:

```bash
update_section_in_place() {
  local page="$1"
  local section_heading="$2" # e.g. "## 🏗️ Technical Design & End-to-End Flow"
  local content_file="$3"    # path to markdown file containing new children

  # 1. Fetch page outline at level 2
  local page_json
  page_json=$(logseq show --graph "$GRAPH" --page "$page" --level 2 --output json 2>/dev/null || true)

  # Check if page exists
  if [[ "$page_json" == *"page-not-found"* ]] || [ -z "$page_json" ]; then
    logseq upsert page --graph "$GRAPH" --name "$page" >/dev/null 2>&1 || true
    page_json=$(logseq show --graph "$GRAPH" --page "$page" --level 2 --output json 2>/dev/null || true)
  fi

  # 2. Extract block ID for target section
  local heading_id
  heading_id=$(echo "$page_json" | node -e '
    let input = "";
    process.stdin.on("data", d => input += d);
    process.stdin.on("end", () => {
      try {
        const data = JSON.parse(input);
        const children = data?.data?.root?.["block/children"] || [];
        const target = process.argv[1].trim();
        const found = children.find(c => (c["block/title"] || "").trim().includes(target));
        if (found) console.log(found["db/id"]);
      } catch {}
    });
  ' "$section_heading")

  # 3. If section does not exist, create it as top-level child of page
  if [ -z "$heading_id" ]; then
    local new_h_res
    new_h_res=$(logseq upsert block --graph "$GRAPH" \
      --target-page "$page" \
      --pos last-child \
      --blocks "- $section_heading" \
      --output json)
    heading_id=$(echo "$new_h_res" | jq -r '.data.result[0]' 2>/dev/null || echo "$new_h_res" | grep -o '"result":\[[0-9]*\]' | grep -o '[0-9]*')
  else
    # Extract existing children IDs
    local child_ids
    child_ids=$(echo "$page_json" | node -e '
      let input = "";
      process.stdin.on("data", d => input += d);
      process.stdin.on("end", () => {
        try {
          const data = JSON.parse(input);
          const children = data?.data?.root?.["block/children"] || [];
          const target = process.argv[1].trim();
          const found = children.find(c => (c["block/title"] || "").trim().includes(target));
          const ids = (found?.["block/children"] || []).map(ch => ch["db/id"]).filter(Boolean);
          if (ids.length > 0) console.log(JSON.stringify(ids));
        } catch {}
      });
    ' "$section_heading")

    # Remove obsolete child blocks
    if [ -n "$child_ids" ] && [ "$child_ids" != "[]" ]; then
      logseq remove block --graph "$GRAPH" --id "$child_ids" >/dev/null 2>&1 || true
    fi
  fi

  # 4. Insert new outline children under the heading
  if [ -n "$heading_id" ] && [ -f "$content_file" ]; then
    logseq upsert block --graph "$GRAPH" \
      --target-id "$heading_id" \
      --pos last-child \
      --blocks-file "$content_file" >/dev/null 2>&1
    echo "✅ Updated section '$section_heading' on '$page'"
  fi
}
```

### 3.2 Checking Page Staleness (Last Updated Timestamp)
To check if a branch page has been updated within the last 10 minutes:
```bash
check_branch_staleness() {
  local page="$1"
  local page_name
  page_name=$(echo "$page" | tr '[:upper:]' '[:lower:]')
  local query="[:find (max ?u) :in \$ ?name :where [?p :block/name ?name] [?b :block/page ?p] [?b :block/updated-at ?u]]"
  local res
  res=$("$LOGSEQ_BIN" query --graph "$GRAPH" --query "$query" --inputs "[\"$page_name\"]" --output json 2>/dev/null || true)
  local last_u
  last_u=$(echo "$res" | grep -oE '[0-9]{12,14}' | head -n 1 || true)

  local now_ms=$(( $(date +%s) * 1000 ))
  if [ -z "$last_u" ]; then
    echo "⚠️ Page '$page' does not exist or has no updated blocks."
    return 1
  fi
  local age_ms=$(( now_ms - last_u ))
  local age_min=$(( age_ms / 60000 ))
  echo "Page '$page' last updated ${age_min} minutes ago."
  if [ "$age_ms" -gt 600000 ]; then
    return 1 # stale (>10 min)
  fi
  return 0 # fresh (<=10 min)
}
```

### 3.3 Collapsing Blocks by Default
To keep pages clean, collapse reference sections, leaving active branches expanded:
```bash
# Collapse a section heading block (e.g. Overview or Architecture)
logseq upsert block --graph "$GRAPH" \
  --id <HEADING_BLOCK_ID> \
  --update-properties '{:block/collapsed? true}'

# Keep active branches/worktrees expanded
logseq upsert block --graph "$GRAPH" \
  --id <ACTIVE_BRANCHES_HEADING_ID> \
  --update-properties '{:block/collapsed? false}'
```

---

## 4. Editing Blocks and the Link Invariant

> **CRITICAL CLI INVARIANT**:
> Editing an existing block with `upsert block --id <ID> --content '...'` **drops its `:block/refs` link metadata**, turning `[[links]]` into unlinked plain text.
>
> - **Plain text without links**: Safe to use `--id <ID> --content 'text'`.
> - **Content with `[[links]]`**: **Must remove and recreate**:
>   1. Note parent block ID and sibling position.
>   2. `logseq remove block --graph "$GRAPH" --id <ID>`
>   3. `logseq upsert block --graph "$GRAPH" --target-id <PARENT_ID> --pos last-child --blocks '[[links]]'`

---

## 5. Daily Journal Activity Pulse

The Daily Journal maintains a single-line pulse per branch under `🤖 [[Agent Activity]]` -> `[[projects: <PROJECT>]]`.

### 5.1 Format
```markdown
- [[<PROJECT>: <BRANCH_SLUG>]] — <status_icon> <one-sentence description> (<HH:MM>)
```
*Status icons*: 🔄 (in progress), ✅ (done/ready to merge), 🚨 (in review), ⏸️ (paused)

### 5.2 Pulse Update Procedure
1. Find or create `🤖 [[Agent Activity]]` on today's journal page:
   ```bash
   TODAY=$(date "+%b %d, %Y" | sed -E 's/ 0/ /; s/([0-9]+)/&th/; s/1th/1st/; s/2th/2nd/; s/3th/3rd/; s/11st/11th/; s/12nd/12th/; s/13rd/13th/')
   # or inspect today's journal directly
   logseq show --graph "$GRAPH" --page "$TODAY" --output json
   ```
2. Locate the project parent block `[[projects: <PROJECT>]]` under `🤖 [[Agent Activity]]`.
3. Locate existing pulse block for `[[<PROJECT>: <BRANCH_SLUG>]]`.
4. Remove the previous pulse block:
   ```bash
   logseq remove block --graph "$GRAPH" --id <OLD_PULSE_ID>
   ```
5. Insert new 1-line pulse:
   ```bash
   logseq upsert block --graph "$GRAPH" \
     --target-id <PROJECT_PARENT_ID> \
     --pos last-child \
     --blocks "- [[$BRANCH_PAGE]] — 🔄 Migrated session validation to pure skill commands ($(date +%H:%M))"
   ```

---

## 6. Ask (Dual-Channel Review Prompt)

When blocked or requesting human guidance, mirror to Logseq **and** ask in chat. Never block your CLI process waiting on Logseq.

### 6.1 Create In-Review Task in Logseq
```bash
# 1. Create task on today's journal
TASK_JSON=$(logseq upsert task --graph "$GRAPH" \
  --target-page "$TODAY" \
  --content "🚨 [In Review] \`$BRANCH_PAGE\`: How should we handle the storage format?" \
  --status in-review \
  --output json)
TASK_ID=$(echo "$TASK_JSON" | jq -r '.data.result[0]' 2>/dev/null || echo "$TASK_JSON" | grep -o '"result":\[[0-9]*\]' | grep -o '[0-9]*')

# 2. Pin to top of today's journal
logseq upsert block --graph "$GRAPH" \
  --id "$TASK_ID" \
  --target-page "$TODAY" \
  --pos first-child

# 3. Tag with both agent_task and needs-human
logseq upsert block --graph "$GRAPH" \
  --id "$TASK_ID" \
  --update-tags '["agent_task" "needs-human"]'

# 4. Add context and options as open child bullets
cat << 'EOF' > /tmp/ask-details.md
- **Why**: Choosing between SQLite and JSON files affects query latency.
- **Option A**: SQLite database (faster queries, binary file).
- **Option B**: Plain JSON (git friendly, slower on large graphs).
EOF

logseq upsert block --graph "$GRAPH" \
  --target-id "$TASK_ID" \
  --pos last-child \
  --blocks-file /tmp/ask-details.md

# 5. Optional desktop notification (Linux: notify-send, macOS: osascript)
if command -v notify-send >/dev/null 2>&1; then
  notify-send "Logseq Agent Memory" "Review needed for $BRANCH_PAGE" 2>/dev/null || true
elif command -v osascript >/dev/null 2>&1; then
  osascript -e "display notification \"Review needed for $BRANCH_PAGE\" with title \"Logseq Agent Memory\" sound name \"Glass\"" 2>/dev/null || true
fi
```

### 6.2 Prompt User in Chat
Immediately present the question, why, and options in your conversation response.

---

## 7. Resolve (Recording Decisions & Cleanup)

### 7.1 Human Responded in Chat
1. Append the recorded decision to `## ⚖️ Key Engineering Decisions & Trade-offs` on `$BRANCH_PAGE`.
2. Remove the temporary review prompt block from the journal:
   ```bash
   logseq remove block --graph "$GRAPH" --id "$TASK_ID"
   ```

### 7.2 Human Responded in Logseq
During `orient`, the agent inspects tasks tagged `needs-human`:
1. If the task is marked `done` or contains a child note from the human:
   - Extract the decision text.
   - Append to `## ⚖️ Key Engineering Decisions & Trade-offs` on `$BRANCH_PAGE`.
   - Remove the prompt block:
     ```bash
     logseq remove block --graph "$GRAPH" --id "$TASK_ID"
     ```
   - Inform the user in chat: `"Noticed you approved Option A in Logseq; recorded decision on branch page."`

---

## 8. Distill (Evergreen Knowledge Transfer)

When architectural patterns, permanent gotchas, or conventions stabilize:
1. Update `projects: <PROJECT>` under `## 🏗️ System Architecture & Module Map`, `## 📏 Engineering Conventions & Architectural Invariants`, or `## 🧠 Sharp Edges & Permanent Gotchas`.
2. When a branch merges or closes:
   - Move branch entry on `projects: <PROJECT>` from `## 🌿 Active Branches & Worktrees` to `## 🏁 Completed Branches & Architecture History`.

---

## 9. Extras

### 9.1 Agent Command Center Provisioning
Create or maintain the `Agent Command Center` page using native Logseq 2.0 DB `/Query` blocks:

```bash
# 1. Create page if not present
logseq upsert page --graph "$GRAPH" --name "Agent Command Center"

# 2. Add sections and native /Query blocks (Needs Human Review on top!)
# Section 1: Needs Human Review
H1=$(logseq upsert block --graph "$GRAPH" --target-page "Agent Command Center" --pos last-child --blocks "- ## 🚨 Needs Human Review" --output json | grep -o '"result":\[[0-9]*\]' | grep -o '[0-9]*' || true)
Q1=$(logseq upsert block --graph "$GRAPH" --target-id "$H1" --pos sibling --content "" --update-tags '["Query"]' --output json | grep -o '"result":\[[0-9]*\]' | grep -o '[0-9]*' || true)
logseq upsert block --graph "$GRAPH" --id "$Q1" --update-properties '{:logseq.property/query "(and (task \"In Review\") (tags [[agent_task]]))"}'

# Section 2: Currently Running
H2=$(logseq upsert block --graph "$GRAPH" --target-id "$Q1" --pos sibling --blocks "- ## 🔄 Currently Running" --output json | grep -o '"result":\[[0-9]*\]' | grep -o '[0-9]*' || true)
Q2=$(logseq upsert block --graph "$GRAPH" --target-id "$H2" --pos sibling --content "" --update-tags '["Query"]' --output json | grep -o '"result":\[[0-9]*\]' | grep -o '[0-9]*' || true)
logseq upsert block --graph "$GRAPH" --id "$Q2" --update-properties '{:logseq.property/query "(and (task \"Doing\") (tags [[agent_task]]))"}'

# Section 3: Delegation Queue
H3=$(logseq upsert block --graph "$GRAPH" --target-id "$Q2" --pos sibling --blocks "- ## 📥 Delegation Queue" --output json | grep -o '"result":\[[0-9]*\]' | grep -o '[0-9]*' || true)
Q3=$(logseq upsert block --graph "$GRAPH" --target-id "$H3" --pos sibling --content "" --update-tags '["Query"]' --output json | grep -o '"result":\[[0-9]*\]' | grep -o '[0-9]*' || true)
logseq upsert block --graph "$GRAPH" --id "$Q3" --update-properties '{:logseq.property/query "(and (task \"Todo\") (tags [[agent_task]]))"}'
```

### 9.2 Delegation Queue Workflows (`#agent_task`)
When a human creates a `todo` task referencing a project/branch tagged `#agent_task`:
```bash
# Claim task (moves to 🔄 Currently Running in Command Center)
logseq upsert task --graph "$GRAPH" --id <TASK_ID> --status doing

# Straightforward completion (moves out of running)
logseq upsert task --graph "$GRAPH" --id <TASK_ID> --status done
logseq upsert block --graph "$GRAPH" \
  --target-id <TASK_ID> \
  --pos last-child \
  --blocks "- Verified: Implementation verified with tests."
```

### 9.3 Human Sign-Off Mode (`Doing` → `In Review` → `Done`)
When a delegated task finishes sensitive work requiring human verification:
```bash
# Transition to in-review and add #needs-human (moves to 🚨 Needs Human Review)
logseq upsert task --graph "$GRAPH" --id <TASK_ID> --status in-review
logseq upsert block --graph "$GRAPH" --id <TASK_ID> --update-tags '["agent_task" "needs-human"]'
logseq upsert block --graph "$GRAPH" \
  --target-id <TASK_ID> \
  --pos last-child \
  --blocks "- Summary: Implementation ready for human verification."
```

### 9.4 Agent-Queued Follow-Ups (`Todo` / `Backlog` + `#agent_task`)
When an agent spots out-of-scope debt or next milestones during a turn:
```bash
# Create follow-up task on today's journal or target branch page
TASK_JSON=$(logseq upsert task --graph "$GRAPH" \
  --target-page "$TODAY" \
  --content "Fix edge case in parser [[$BRANCH_PAGE]]" \
  --status todo \
  --output json)
TASK_ID=$(echo "$TASK_JSON" | grep -o '"result":\[[0-9]*\]' | grep -o '[0-9]*' || true)

# Tag with #agent_task (lands automatically in 📥 Delegation Queue)
logseq upsert block --graph "$GRAPH" --id "$TASK_ID" --update-tags '["agent_task"]'
```

### 9.5 Rough-Notes Co-Authoring
If the human writes rough bullet notes at the top of a branch page:
1. Read the rough notes via `logseq show`.
2. Integrate the concepts into the structured sections (`## 🏗️ Technical Design & End-to-End Flow`, `## ⚖️ Key Engineering Decisions & Trade-offs`).
3. Preserve or clean the raw notes according to human guidance. Never delete top-level human blocks without instructions.

### 9.6 Self-Updating `agent: core`
When the user specifies a global preference or rule across projects:
```bash
# Inspect agent: core
logseq show --graph "$GRAPH" --page "agent: core"

# Insert rule under ## 📐 Global Engineering Conventions
logseq upsert block --graph "$GRAPH" \
  --target-id <CORE_RULES_HEADING_ID> \
  --pos last-child \
  --blocks "- **Markdown Headings**: Always use H2/H3 for section headings in Logseq pages."
```
