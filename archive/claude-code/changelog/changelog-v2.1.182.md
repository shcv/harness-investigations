# Changelog for version 2.1.182

## Summary

This release introduces `/migrate`, a new command that imports configuration from OpenAI Codex and Google Gemini CLI into Claude Code. It also ships a built-in `artifact-design` skill for production-quality page design, adds `CLAUDE_CODE_CONNECT_TIMEOUT_MS` for connection timeout control, and expands MCP server capabilities with directory listing support.

## New Features


### `/migrate` — Import Config from Codex or Gemini CLI

What: Scans for OpenAI Codex (`~/.codex/config.toml`) or Google Gemini CLI (`~/.gemini/settings.json`) configuration and imports MCP servers, slash commands, subagents, skills, and instruction files into Claude Code.

Usage:
```bash
# Scan and show what's importable (interactive picker in terminal)
claude migrate

# Target a specific agent
claude migrate codex
claude migrate gemini

# Preview without writing anything
claude migrate --dry-run

# Apply all user-level items without the interactive picker
claude migrate --yes

# Also available as a slash command inside a session
/migrate
/migrate --dry-run
/migrate --yes
```

Details:
- Instructions from Codex `AGENTS.md` and `AGENTS.override.md` are appended to `CLAUDE.md`
- Slash commands are converted from Codex `.md` prompts and Gemini `.toml` commands
- MCP servers translate from Codex `mcp_servers` and Gemini `mcpServers` config blocks
- Subagents are imported from Codex `agents` entries into `~/.claude/agents/<name>.md`
- Skills are copied from Codex `skills.config` entries
- Approval policy is mapped to Claude Code permission modes (with warnings when elevated)
- Items requiring review get a ⚠ flag and are held back from `--yes` auto-import
- Project-level config is never auto-imported — requires terminal `claude migrate` for review
- Unmapped items generate a `migrate-to-claude-code` skill that lists them for manual follow-up

Evidence: `/migrate` command definition (search for `"Import config from another AI coding agent (Codex, Gemini CLI)"`)


### `artifact-design` Skill — Built-in Design Guidance for Artifacts

What: A new bundled skill with comprehensive design guidance for building Artifact pages (`claude.ai`-hosted HTML/Markdown). Invoked automatically when Claude builds an Artifact.

Usage:
```bash
# Load design guidance manually
/artifact-design
```

Details:
- Guides Claude through a two-pass design process: brainstorm a token system (color, type, layout), critique it against the subject, then build
- Identifies and avoids three common AI design clichés (warm cream + serif, dark + acid accent, broadsheet hairlines)
- Includes copy-writing principles, CSS cascade guidance, responsive layout requirements, and palette commit workflow
- The Artifact tool description now explicitly loads this skill before generating a page

Evidence: Skill definition (search for `"Design guidance for Artifact pages — process, principles, palette, copy."`) and Artifact tool (search for `"load the \`artifact-design\` skill"`)


### MCP Directory Listing (`resources/directory/read`)

What: MCP servers that advertise the `io.modelcontextprotocol/skills` capability with `directoryRead: true` can now serve paginated directory listings. Claude Code reads them automatically when loading skills from MCP.

Details:
- Uses the `resources/directory/read` method with cursor-based pagination
- Directories appear with MIME type `inode/directory`; SKILL.md URIs are detected automatically
- Pagination stops after a built-in page limit; a warning is logged if more pages exist
- Handles `InvalidParams` on cursor gracefully by returning what was already fetched
- URI sanitization strips invisible Unicode characters (control, private-use, BOM) to prevent injection

Evidence: New MCP directory reader (search for `"readMcpDirectory called on a server without directoryRead capability"`)


### `CLAUDE_CODE_CONNECT_TIMEOUT_MS` — Streaming Connection Timeout

What: New environment variable that sets a Time-to-First-Byte (TTFB) deadline on streaming API requests. If response headers aren't received within the timeout, the request is aborted with a clear error rather than hanging indefinitely.

Usage:
```bash
# Abort if no response headers arrive within 10 seconds
CLAUDE_CODE_CONNECT_TIMEOUT_MS=10000 claude
```

Details:
- Only applies to streaming requests (SSE, Bedrock event streams, `:streamRawPredict`)
- Non-streaming requests are not affected
- Timeout of `0` or a non-finite value disables the feature (uses a built-in default otherwise)
- Error message: `"Request timed out: no response headers after Ns (CLAUDE_CODE_CONNECT_TIMEOUT_MS)"`

Evidence: Timeout implementation (search for `"ms — aborting (CLAUDE_CODE_CONNECT_TIMEOUT_MS)"`)


### `disableClaudeAiConnectors` Setting

What: New boolean setting that prevents claude.ai MCP cloud connectors from being auto-fetched or connected. Any source (user or project settings) setting it to `true` wins — a project can opt out, but a project-level `false` cannot override a user-level `true`.

Usage: Add to `~/.claude/settings.json` or `.claude/settings.json`:
```json
{
  "disableClaudeAiConnectors": true
}
```

Details:
- Only gates auto-fetched connectors; a `claudeai-proxy` server passed explicitly (e.g. via `--mcp-config` or the SDK `mcpServers` option) still follows the normal MCP config trust flow
- When disabled, Claude will report: `"Disabled by disableClaudeAiConnectors setting"`

Evidence: Setting schema entry (search for `"When true in any settings source, claude.ai MCP cloud connectors are not auto-fetched or connected."`)


### `git.sessionUrl` Setting

What: New boolean under the `git` settings block controlling whether the claude.ai session link is appended to commits and PRs created from web or Remote Control sessions. Defaults to `true`.

Usage: Add to settings JSON to suppress the link:
```json
{
  "git": {
    "sessionUrl": false
  }
}
```

Details:
- Omitting the `Claude-Session` trailer from commits and the session link from PR bodies
- Only applies to sessions initiated from web or Remote Control (not local terminal sessions)

Evidence: Setting schema entry (search for `"Whether to append the claude.ai session link to commits and PRs created from web or Remote Control sessions"`)


### MCP Per-Server Permission Mode Override

What: A new control channel message (`set_mcp_permission_mode_override`) lets a client pin an MCP server to a specific permission mode, overriding the global session mode for tool calls from that server.

Details:
- This is a tighten-only channel: only `"default"` or `null` (clear) are accepted; any other mode value is rejected
- Substitutes for the session mode in `effectiveModeForTool` decisions
- Example use case: hold a server at `"default"` mode even when the session is globally in `bypassPermissions`

Evidence: Control channel schema (search for `"@internal Pin (or clear, with mode:null) an MCP server's per-tool permission-mode override. Tighten-only over this channel"`)

## Improvements


### Fable Model Disabled State in Model Picker

When the Fable model is unavailable because usage credits are not provisioned at the org level, the model picker now shows it as `"Fable (disabled)"` with instructions to contact your admin, rather than hiding it or showing a generic error.

Messages users may see:
- `"Fable (disabled) — contact your admin to turn on usage credits"` in the model list
- `"Run /usage-credits to request more from your admin, or switch models to keep working."`
- `"Buy more to keep using Fable, or switch models to keep working."` (personal plan)
- `"Your admin can enable extra usage at claude.ai/admin-settings/usage."`

Evidence: Model list filter (search for `"Fable (disabled)"`)


### Shell Arithmetic Safety — Runtime-Determined Operands

The bash safety checker now detects when an arithmetic operand is a variable whose value is runtime-determined and may carry an array subscript. Previously only literal subscript syntax (`[...]`) was caught; now variable-length operands are also flagged.

Error messages now read:
- `"'N' operand '...' is runtime-determined and may carry an array subscript — shell arith-evals $(cmd) in subscripts"`
- `"printf operand '...' is runtime-determined and may carry an array subscript — zsh arith-evals %d/%i operands (may run $(cmd))"`
- Shell expansion sequences like `$(cmd)` and `${...}` in operands are redacted to `$(…)` and `${…}` in messages

Evidence: Shell checker (search for `"is runtime-determined and may carry an array subscript — shell arith-evals $(cmd) in subscripts"`)


### Team Memory Index Compaction Warnings

Claude now proactively warns when a team memory index file is approaching or exceeding its read limit, and prompts for compaction.

Messages:
- Approaching: `"The memory index at team/.../... is X, approaching the Y read limit. Compact it to under Z now: keep one line per entry, move detail into topic files, and merge or drop stale entries."`
- Over limit: `"...over the Y read limit — content beyond that is dropped when this index is loaded"`

Warning threshold is 80% of the limit; compaction target is 70%.

Evidence: Memory index checker (search for `"The memory index at"`)


### Setup Issues Logged at Startup

When Claude Code detects setup issues (MCP, keybindings, plugins, statusline, etc.), it now logs a brief summary line at startup pointing users to `/doctor` for details.

Example: `"2 setup issues (run /doctor for details)"`

Previously this count was visible only in the statusline; now it also appears in the log output.

Evidence: New startup logger (search for `"setup issues (run /doctor for details)"`)


### Branch Diff Label in Context Window

When viewing git diffs sourced from a branch (rather than from a turn or HEAD), the context header now shows `"Branch changes"` with the base branch reference `"(vs <baseBranch>)"` instead of the generic `"Uncommitted changes"` label.

Evidence: Diff source display (search for `"Branch changes"`)


### Thinking Param Sanitization

Extra keys in a `{type:'disabled'}` thinking parameter (a known issue tracked as gh-68567) are now silently stripped before sending to the API, preventing validation errors. A warning is logged when this occurs.

Evidence: Sanitizer (search for `"extra key(s) from {type:'disabled'} thinking param (gh-68567)"`)


### Prompt Too Long Detection Expanded

The "prompt too long" error classifier now also catches responses where `input length and max_tokens exceed context limit`, in addition to the existing overload detection. This improves compaction triggers for edge cases where the API returns this phrasing.

Evidence: Error classifier (search for `"input length and \`max_tokens\` exceed context limit"`)


### Artifact Tool Description Streamlined

The Artifact tool description was shortened and now references the `artifact-design` skill for design guidance instead of embedding the full guidance inline. This reduces context usage while giving Claude access to richer design principles on demand.

Evidence: Updated Artifact tool description (search for `"Design guidance: Before writing the page, load the \`artifact-design\` skill"`)


### Design Scope Expansion Notification

When Claude Code expands a user's claude.ai login to add `user:design:read` and `user:design:write` (for the Design MCP connector), it now logs a visible notification rather than doing so silently.

Message: `"Added user:design:read and user:design:write to your claude.ai login (for the Design MCP connector)."`

Evidence: Scope expansion handler (search for `"Added user:design:read and user:design:write to your claude.ai login"`)


### Teammate Routing Validation

When sending a message to a named teammate, Claude Code now checks the team roster and returns a clearer error if the target is not on the current team.

Error: `"No teammate named '<name>' is currently on team '<team>'. Spawn one with AgentSpawn({name: '<name>'}) — or message the lead to do so."`

Evidence: Teammate routing (search for `"is currently on team"`)


### Zsh Built-in Safety: `bye` and `logout`

The shell safety checker's recognized zsh built-in list now includes `bye` and `logout`, preventing false positives when these are used in arithmetic contexts.

Evidence: Built-in list (search for `"logout"` near `"vared"`)


### `CLAUDE_CODE_DISABLE_LEGACY_MODEL_REMAP` Opt-Out

When a model ID is deprecated and Claude Code would normally remap it silently, the warning now mentions `CLAUDE_CODE_DISABLE_LEGACY_MODEL_REMAP=1` as an explicit opt-out for users who want to keep the old model.

Evidence: Model remap warning (search for `"CLAUDE_CODE_DISABLE_LEGACY_MODEL_REMAP=1 opts out"`)


### CCR WebSearch Proxy

A new code path routes WebSearch through the CCR (Remote Control) proxy when `CLAUDE_CODE_WEBSEARCH_USE_CCR_PROXY=1` is set and a session ID is available. This enables WebSearch in CCR sessions without direct API access.

Evidence: Proxy path (search for `"/worker/web-search"`)


### Linux CA Certificate Paths for Agent Proxy

The agent proxy CA installer now tries additional Linux CA certificate paths:
- `/etc/pki/tls/certs/ca-bundle.crt` (RHEL/Fedora/CentOS)
- `/etc/pki/ca-trust/source/anchors` (RHEL trust anchors)
- `/usr/local/share/ca-certificates` (Debian/Ubuntu)

Evidence: CA install paths (search for `"[agent-proxy] CA installed to system trust via"`)


### Settings Config Redirect Cleanup

The settings-to-UI redirect map was pruned. The following redirects were removed:
- `outputStyle` → `/output-style`
- `language` → `/config (Language row)`
- `notifChannel` → `/config (Notifications row)`
- `autoUpdatesChannel` was changed to → `/channel`

The settings UI now surfaces these as direct `/model` and `/theme` links without stale config-panel row references.

Evidence: Settings redirect map (search for `"autoUpdatesChannel"`)


### `SendUserFile` Tool Example Added

The `SendUserFile` tool description now includes a concrete usage example:
`Example: SendUserFile({ files: ["report.md"], caption: "Here's the report.", status: "normal" })`

Evidence: Tool description (search for `"Example: SendUserFile({ files:"`)

## Bug Fixes

- VirtualMessageList: added error tracking for `undefined` elements in the message array, which previously caused silent rendering failures. (search for `"VirtualMessageList: undefined element in messages[]"`)
- Input JSON parse errors now produce a human-readable message including byte count instead of a bare failure. (search for `"input JSON failed to parse — ... bytes"`)
- Shell name validation in PowerShell now rejects command names containing characters outside `[A-Za-z0-9_+-]`, preventing false matches on symbolic operator strings. (search for `/^[A-Za-z0-9_+-]+$/`)
- MCP client disconnect now waits up to 2 seconds for the transport process to exit before returning, reducing zombie processes. (search for `"transport.waitForExit"`)
- Autocompact thrashing detection now logs a specific message when the context refills repeatedly within a few turns. (search for `"Autocompact is thrashing: the context refilled to the limit"`)
- SKILL.md digest mismatch log messages are now consistently titled `"SKILL.md digest mismatch for"` (was `"skill-md digest mismatch for"` in v2.1.181). (search for `"SKILL.md digest mismatch for"`)
- Repeated validation failures no longer inject a `"This call has now failed validation N times in a row"` hint — that logic was removed along with the old tool input schema hint system. The previous behaviour could confuse agents into over-adjusting inputs.

## Notes

The `/migrate` command does not import project-level config from `.codex/` or `.gemini/` automatically when using `--yes`. Project config can be authored by anyone with write access to the repo, so it requires explicit review via `claude migrate` in a terminal session. This is a security constraint, not a limitation.


Generated with:
- tool: `harness-investigations@1d6cc84-dirty`
- provider: `claude`
- model: `claude-sonnet-4-6`
- primary diff: `archive/claude-code/changes/changes-v2.1.182.md` (filtered astdiff)
- string diff: `archive/claude-code/changes/string-diff-v2.1.182.txt`
