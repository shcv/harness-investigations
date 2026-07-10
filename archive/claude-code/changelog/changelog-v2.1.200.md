# Changelog for version 2.1.200

## Summary

This release introduces observer agents — background agents that silently watch a session and can report back via a new `ObserverReport` tool — along with a `set_cwd` headless API for SDK hosts, a configurable question auto-continue timeout, and remote workflow script execution for server-launched sessions. Numerous improvements land across memory sync error handling, the diff panel, mTLS certificate reloading, and the permission mode naming.


## New Features


### Observer Agents (Experimental)

What: Agent definitions can now declare a background observer — a second agent type that automatically spawns, watches each turn of the primary agent, and can send advisory reports via a new `ObserverReport` tool.

Usage:
```yaml
# In your agent's frontmatter (e.g. AGENTS.md or via SDK)
observer: my-reviewer-agent
observerMessage: "Focus on security issues only."
```

Details:
- The observer runs silently after each turn; it receives a read-only activity digest (wrapped in `<agent-activity>` tags) describing what the observed agent said and did.
- The observer must use the new `ObserverReport` tool to send anything back — `SendMessage` is not available to observers.
- Observer reports are advisory only. The observed agent is explicitly instructed never to treat an observer report as user consent for any action.
- Observer chaining is intentionally blocked: observers cannot themselves declare observers.
- Enabled only when `CLAUDE_CODE_EXPERIMENTAL_OBSERVER_AGENTS=1` is set **and** the `tengu_observer_agents_enabled` feature flag is on.

Evidence: Observer system (search for `"ObserverReport"`, `"[agentObserver]"`, `tengu_observer_agents_enabled`)


### `set_cwd` — Headless Working Directory Change for SDK Hosts

What: A new internal `set_cwd` control-plane request lets SDK hosts like Claude Desktop move a session's working directory programmatically, without an interactive terminal prompt.

Details:
- Runs the same validation, `Cd(...)` permission rules, and trust latch as the interactive `/cd` command.
- When the target directory requires trust, `set_cwd` responds with `status: "needs_trust"` and the canonical directory path so the host can show its own dialog and re-send with `trust_accepted: true`.
- Rejected while a turn is in progress; the session must be idle.
- Path safety check rejects directories whose canonical path contains invisible or non-printing characters (control, format, zero-width, narrow no-break space, etc.).

Evidence: Headless cd tool (search for `"@internal Moves the session to a new working directory"`, `"set_cwd: invalid request"`)


### Question Auto-Continue Timeout

What: A new `askUserQuestionTimeout` setting automatically continues paused `AskUserQuestion` prompts after a configurable delay, using whatever answers have been selected so far.

Usage:
```bash
# Set via /config or in settings.json:
# "askUserQuestionTimeout": "60s"   # or "5m", "10m", "never"
```

Details:
- Available values: `"60s"`, `"5m"`, `"10m"`, `"never"` (default).
- With `"never"` (the default), no auto-continue ever runs — behaviour is unchanged for existing users.
- Useful for automated or semi-attended workflows where stalled questions should not block indefinitely.
- Configurable per-user in the settings UI under the new "Question auto-continue timeout" option.

Evidence: Setting definition (search for `"Idle time before Claude's questions auto-continue"`, `"askUserQuestionTimeout"`)


### Remote Workflow Script Execution

What: Server-launched (CCR) sessions can now receive a workflow script via environment variables and execute it immediately on session start via the hidden `__remote-workflow` command.

Details:
- `CLAUDE_REMOTE_WORKFLOW_SCRIPT` — the workflow script body delivered by the server.
- `CLAUDE_REMOTE_WORKFLOW_ARGS` — optional JSON args passed to the script.
- `CLAUDE_WORKFLOW_NAME_ONLY` — restricts the Workflow tool to named (bundled) workflows only; dynamic scripts are then disallowed.
- The command validates the script for determinism (forbids `Date.now()`, `Math.random()`, `new Date()`), compiles it, and runs it inside the normal Workflow engine.
- Only callable inside a remote session (`CLAUDE_CODE_REMOTE` must be set); has no interactive use.

Evidence: Remote workflow entry point (search for `"CLAUDE_REMOTE_WORKFLOW_SCRIPT"`, `"this command only runs inside a remote (CCR) session"`, `"__remote-workflow"`)


## Improvements


### Permission Mode Renamed to "Manual Mode"

The default interactive permission mode was previously labelled "default mode" in UI text and keybinding hints. It is now called "manual mode" throughout the interface.

The string `"manual"` is now also accepted as an alias anywhere the mode name is parsed, so existing settings using `"default"` continue to work.

Evidence: Mode alias (search for `"manual is accepted as an alias for default"`, `"to cycle between manual mode"`)


### Diff Panel: Pre-Session Changes Toggle and Base Cycling

Two new keyboard actions are available in the diff panel:

- `app:toggleDiffPreSession` — show or hide changes that existed before the current session started. Lets you see exactly what the session itself modified, without noise from pre-existing edits.
- `app:cycleDiffBase` — cycle between available diff bases (branch merge-base, HEAD, working tree) directly from the panel.

Evidence: New actions (search for `"show/hide pre-session changes in diff panel"`, `"app:cycleDiffBase"`, `"app:toggleDiffPreSession"`)


### Diff Panel Works on Repos With No Commits

The diff sidebar previously required at least one commit to show staged changes. It now handles brand-new repositories (no commits yet), correctly computing a diff against the empty tree when `git rev-parse HEAD` returns exit code 1.

Evidence: No-commits branch (search for `"no commits yet"`, `"--cached"` in diff computation)


### mTLS Certificates Now Support Hot Reload

The mTLS client certificate loading was refactored to use async file reading with change detection. Certificates are now reloaded when `CLAUDE_CODE_CLIENT_CERT` or `CLAUDE_CODE_CLIENT_KEY` paths or contents change, without restarting the session.

Previously, a static singleton loaded certificates once at startup. The new implementation tracks path and content, emitting a refresh when either changes.

Evidence: mTLS async loader (search for `"client certificate from CLAUDE_CODE_CLIENT_CERT"`, `"mTLS: Creating HTTPS agent with custom certificates"`)


### Memory Sync: Richer Error Types and User Notifications

Memory sync failures now map to distinct error codes with specific user-facing messages:

- `store_full` — store has reached its memory or size limit.
- `content_too_large` — a single file exceeds 100 KB.
- `content_secret` — the file appears to contain a credential or API key (write blocked; rotate if real).
- `invalid_path` — path is too long, too deep, contains `.`/`..` segments, control characters, or is not NFC-normalized.
- `store_archived` — the store has been archived server-side and no longer accepts writes.

Recovery notifications are also improved: when a paused store resumes, the UI reports how many pending local changes were pushed, or confirms that sync is running normally again.

Evidence: Error map (search for `"memory store has reached its memory limit"`, `"memory content appears to contain a credential"`, `"Memory sync recovered"`)


### Plan Approval Grants 15-Minute Write Permission

When you approve a plan (via the plan-mode dialog), Claude is now also granted write and delete access to exactly the paths listed in that plan for up to 15 minutes — without another prompt per operation. Any other path still asks normally.

This is explained to the user in the approval dialog: "Approving also lets writes and deletes to exactly these paths run without another prompt for up to 15 minutes (file contents are not shown again; anything to any other path will still ask)."

Evidence: Plan token grant (search for `"Approving also lets writes and deletes to exactly these paths"`, `"approved plan expired"`, `"plan_token not approved in this process"`)


### `project_write` Gains `present_to_user` Flag

The `project_write` method on the Project tool now accepts an optional `present_to_user: true` boolean. Setting it marks the written document as the deliverable the user should see. Leave it unset (defaults to `false`) for routine saves, notes, and bulk writes to avoid unnecessary UI surfacing.

Evidence: New schema field (search for `"project_write: true marks this doc as the file the user needs to"`)


### Project Memory Files Now Include `updated_at`

When reading a memory file from shared storage, the response schema now includes an `updated_at` timestamp alongside `content`, `id`, `path`, and `content_sha256`. This lets sessions detect whether a file changed since they last read it.

Evidence: Schema change (search for `"updated_at: A.string()"` in the memory object schema)


### Feedback Memory Instructions Refined

The instruction for writing `feedback` memories (when a user corrects a repeatable workflow step) is now more precise about the "never create a new skill file" rule:

The updated instruction adds one explicit exception: if the correction is about how to verify changes in a particular subtree, create `.claude/skills/verify/SKILL.md` at the appropriate scope (repo root for repo-wide, subproject directory for subtree-specific). Never create other skill files — a new project skill shadows the same-named built-in.

Evidence: Updated skill-memory instruction (search for `"each correction lives in exactly one skill file"`)


### `SendMessage` Now Covers Cloud Sessions

The `SendMessage` tool description was updated to include cloud Claude sessions (when the current session has cloud access) in the list of reachable recipients, alongside in-process subagents and local peer sessions. The previous description omitted cloud sessions.

Evidence: Updated SendMessage description (search for `"your Claude sessions running in the cloud (when this session has cloud access)"`)


### `/plugin` Command Refresh Hint Fixed

The help message that suggests refreshing the plugin cache now says `run /plugin` instead of the previous `run /plugins` (which was incorrect — the command is `/plugin`, not `/plugins`).

Evidence: String change (search for `"Run /plugin to refresh the plugin cache"`)


### GitHub CLI Operation Detection Expanded

The auto-detection regex for dangerous GitHub CLI operations (used to enforce safety checks) was expanded from `gh pr create` and `gh pr merge` alone to a unified pattern covering:

`gh pr create`, `gh pr merge`, `gh issue create`, `gh issue comment`, `gh release create`, `gh repo fork`

Evidence: Combined operation regex (search for `"ghs+(prs+create|prs+merge|issues+create"`, or the literal regex string `"pr\s+create|pr\s+merge|issue\s+create|issue\s+comment|release\s+create|repo\s+fork"`)


### MCP Server Enable/Disable List Now Null-Safe

The function that checks whether an MCP server is disabled now always treats `enabledMcpServers` and `disabledMcpServers` as empty arrays when they are `null` or `undefined`, preventing potential crashes when these settings are missing from the config.

Evidence: Null-safe array (search for `"Array.isArray(e) ? e : []"` in MCP server check)


## Bug Fixes

- `/cd` directory validation extracted into a shared helper (`F5o`) used by both the interactive command and the new `set_cwd` API, so both paths apply identical validation logic. (search for `"cd: unexpected stat errno"`)
- Team member removal now correctly detects stale removals when a member was re-added between when the removal was queued and when it executes, avoiding inadvertent double-removal. (search for `"re-added after removal was initiated"`)
- `isDirEmptySync` replaced with an async `opendir`-based implementation to avoid blocking the event loop on directory emptiness checks. (search for `"mDs"` near `"opendir"`)
- Model ID alias resolution now correctly handles `modelOverrides` from policy settings, falling through to the override value before the default alias. (search for `"yRd"` near `"modelOverrides"`)


Generated with:
- tool: `harness-investigations@03136fb-dirty`
- provider: `claude`
- model: `claude-sonnet-4-6`
- primary diff: `archive/claude-code/changes/changes-v2.1.200.md` (filtered astdiff)
- string diff: `archive/claude-code/changes/string-diff-v2.1.200.txt`
