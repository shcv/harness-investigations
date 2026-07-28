# Changelog for version 2.1.213

## Summary

This release introduces `claude import`, a new command that migrates configuration from OpenAI Codex and Google Gemini CLI directly into Claude Code. It also adds first-class support for Claude Platform on Google Cloud via a new `AnthropicGoogleCloud` client, a `CLAUDE_CODE_NO_MODEL_FALLBACK` environment variable to lock model substitution, and several SDK wire schema additions useful to host and SDK builders.

## New Features


### `claude import` — Migrate from Codex or Gemini CLI

What: A new terminal command and in-session slash command that scans an OpenAI Codex or Google Gemini CLI config and imports compatible items into Claude Code: MCP servers, subagents/agents, skills, instructions, and permission mode.

Usage:
```bash
# Interactive picker (terminal only)
claude import codex
claude import gemini

# Preview without writing anything
claude import codex --dry-run

# Headless / CI — applies user-level items without prompts
claude import --yes

# In an active Claude Code session
/import
/import --yes
```

Details:
- From Codex (`~/.codex/config.toml`): imports `[mcp_servers]`, `[agents]`, `[[skills.config]]`, and `approval_policy`. Maps Codex approval policies to Claude Code permission modes (`suggest`/`untrusted`/`on-request` → `default`; `auto-edit` → `acceptEdits`; `full-auto`/`on-failure` → `auto`).
- From Gemini (`~/.gemini/settings.json`): imports MCP servers, slash commands, and `defaultMode`. Gemini extensions and `system.md` are flagged for manual review.
- Project-level config from `.codex/` or `.gemini/` directories is listed but never auto-imported — it requires a terminal session and per-item review because repo-level config is author-controlled.
- Safety guards: path traversal, symlink detection, shell-exec marker scanning. Items containing `` !`…` `` or ` ```! ` markers (inert in Codex/Gemini but live in Claude Code) are blocked and require manual porting.
- Items that can't be mapped automatically (hooks, product-specific toggles, Gemini extensions) are written to a helper skill at `~/.claude/skills/import-to-claude-code/SKILL.md` for later review with `/import-to-claude-code`.
- `--yes` applies user-level items only; warning-flagged items and skills are held back for interactive review.

Evidence: full import infrastructure (search for `"Usage: claude import [codex|gemini] [--dry-run] [--yes]"`)


### Claude Platform on Google Cloud

What: Claude Code can now connect to Anthropic's Claude Platform on Google Cloud, routing API calls through `claude.googleapis.com` instead of `api.anthropic.com`. Authentication uses Google Application Default Credentials, a service account, or an explicit bearer token.

Usage:
```bash
# Enable via environment variables
export CLAUDE_CODE_USE_ANTHROPIC_GOOGLE_CLOUD=1
export ANTHROPIC_GOOGLE_CLOUD_PROJECT=my-gcp-project
export ANTHROPIC_GOOGLE_CLOUD_WORKSPACE_ID=my-workspace-id

# Optional overrides
export ANTHROPIC_GOOGLE_CLOUD_LOCATION=us-east5     # default: global
export ANTHROPIC_GOOGLE_CLOUD_BASE_URL=https://...  # override endpoint
export CLAUDE_CODE_SKIP_ANTHROPIC_GOOGLE_CLOUD_AUTH=1  # skip Google auth (for custom gateways)
```

Details:
- Adds a new `AnthropicGoogleCloud` SDK client class backed by `https://claude.googleapis.com/v1alpha/projects/{project}/locations/{location}/workspaces/{workspaceId}/invoke`.
- Supports `bearerTokenProvider`, `googleAuth` (google-auth-library), `authClient`, or Application Default Credentials.
- `authClient` and `googleAuth` are mutually exclusive; `skipAuth` is mutually exclusive with all auth options.
- The deprecated text Completions API is not available on this provider.
- GCP path-segment env vars (`ANTHROPIC_GOOGLE_CLOUD_PROJECT`, `ANTHROPIC_GOOGLE_CLOUD_WORKSPACE_ID`, `ANTHROPIC_GOOGLE_CLOUD_LOCATION`) must contain only letters, digits, hyphens, and underscores — URL metacharacters are rejected to prevent request-path rewriting.

Evidence: new `AnthropicGoogleCloud` client class (search for `"Claude Platform on Google Cloud"`)


### `CLAUDE_CODE_NO_MODEL_FALLBACK` — Prevent model substitution

What: A new environment variable that disables all model-fallback pivots, including the fallback used during context compaction. When set, Claude Code uses only the configured primary model and fails rather than silently switching.

Usage:
```bash
export CLAUDE_CODE_NO_MODEL_FALLBACK=1
```

Details:
- When active, any code path that would normally pivot to a fallback model throws an error with a stack trace identifying the call site.
- Compaction is disabled when the flag is set: "Compaction unavailable: CLAUDE_CODE_NO_MODEL_FALLBACK is set and model substitution is disabled · unset it to allow the swap".
- The availability chain collapses to `[primary]` only; the tripwire function `_Nr()` guards against code that bypasses the chain.
- Intended for CI or compliance scenarios where a specific model must be used throughout the entire session.

Evidence: tripwire error (search for `"CLAUDE_CODE_NO_MODEL_FALLBACK tripwire: a model-fallback pivot was attempted"`)

## Improvements


### Scheduled task framing in SDK wire schema

The `task-notification` origin kind now carries an optional `subkind: "scheduled-trigger"` field that identifies turns fired from stored scheduled prompts. Harnesses use this to frame the turn as the session's assigned task rather than a generic background notification. The harness banner `[SCHEDULED TASK - AUTOMATED FIRING OF A CONFIGURED PROMPT]` is now only shown on scheduled-trigger subkind turns.

Evidence: new `subkind` field (search for `"Present when the delivery is the fired stored prompt of a scheduled task/routine"`)


### SDK wire schema additions for host and SDK builders

Several new fields were added to the SDK wire protocol:

- `aborted: true` on assistant messages — present when the message stream was cut short by an interrupt before `stop_reason` was received; content may end mid-word.
- `suppress_always_allow_rule` on permission-ask payloads — hosts must omit the "don't ask again" affordance when this flag is set, because accepting it would write a whole-tool allow rule broader than the verb being asked.
- `matched_ask_rule` on permission-ask payloads — when a user-configured ask rule forced a prompt but the tool provided a richer decision reason, the ask-rule rides here; treat it like `decision_reason_type: "rule"` for policy purposes.
- `system_prompt` on `set_model` control messages — allows replacing the custom system prompt inline from the subprocess transport without a separate message; must be non-empty.
- `version` on plugin entries in session messages — the plugin's declared version from `plugin.json`, emitted verbatim; validate before trusting.
- `anthropicGoogleCloud` added to the recognized provider enum.
- `fork` added as a valid `SessionStart` hook `source` value.

Evidence: see descriptions inline (search for `"True when this assistant message was truncated by an interrupt"`, `"True when the dialog must not offer the persistent"`, `"Set when a user-configured ask RULE"`)


### Docker safety — additional safe flags

The read-only command analyzer's Docker allowlist now includes `-r`, `--url`, `--connection`, `--identity`, `--remote`, `--module`, and `--out`. These flags were previously unrecognized and would cause Docker commands using them to be treated as potentially write-capable.

Evidence: updated safe-flag set (search for `"--connection"`)


### Bash command analysis — length guard

Very long Bash commands now short-circuit the read-only analysis with `"Command too long for read-only analysis"` and pass through as-is instead of attempting a parse that can time out or produce incorrect classifications.

Evidence: new length guard (search for `"Command too long for read-only analysis"`)


### Bash analysis — `help` command safety

The `help` built-in now applies context-aware analysis: arguments containing `/`, `\`, `~`, or flag-like patterns are flagged as potentially dangerous, matching the tightened behavior already applied to `file` and similar commands.

Evidence: new callback in help command handler (search for `"additionalCommandIsDangerousCallback"`)


### Tool progress heartbeat filtering

The SDK message adapter now silently drops `tool_progress` frames carrying `heartbeat: true` or `subagent_retry` fields instead of surfacing them as conversation messages. This prevents spurious message events from appearing when running as an SDK subprocess.

Evidence: explicit drop path (search for `"[sdkMessageAdapter] Ignoring heartbeat/subagent-retry tool_progress frame"`)


### Org memory — store selection and credential state machine

The org memory credential system was refactored with an explicit state machine (undecided / on / off / parked / ended) and a new store selection layer. Users can now be assigned to specific memory silos or grouping contexts by the server. The old single-pass write-opt-in is replaced by a separate credential renewal flow that tracks the write-access decision and selection across token refreshes.

Evidence: new state constants (search for `"org-memory-discovery: granted silo path failed the partition pin"`)


### YAML frontmatter — lossy-value quoting

The frontmatter parser now accepts a `quoteLossyValues` mode that detects scalar values which YAML would round-trip differently than their raw text (e.g., unquoted numbers, booleans, dates) and re-quotes them in-place before parsing. This prevents silent data loss when writing back modified frontmatter.

Evidence: new parser option (search for `"quoteLossyValues"`)


### Symlink-safe path normalization

The path resolution layer received a more thorough symlink-safe real-path walk that correctly handles UNC paths, symlink depth limits (40 hops), and collapsed-landing detection. The `.` and `..` components in paths are truncated at the first dot-segment, preventing path traversal via dot-segment injection.

Evidence: new symlink walk (search for `"cwy"` implementation context; stable string search: `"Is (or is under) a symlink — skipping project-scope read for safety."`)

## Bug Fixes

- URL backslash detection: the check for backslashes in URL hostnames was extended to handle http/https/ws/wss/ftp schemes where the authority section starts with `//` or `\` — previously only plain-path URLs were checked, allowing bypass via scheme-prefixed paths. (search for `"b8m = new Set"`)
- Bash test command parser: the analyzer now detects when the tree-sitter parser dropped bytes between or after child nodes in a `[[...]]` test command, correctly classifying such commands as too-complex rather than analyzing partial structure. (search for `"Test command has unparsed bytes between children"`)
- Permission-ask `requires_user_interaction` field: updated description — the flag now covers both `Tool.requiresUserInteraction()` cases and `localDisplayOnly` asks whose consent disclosure cannot ride the wire, so hosts should suppress one-tap approve/deny for either reason.
- Error recovery: `ENODEV`, `EUNKNOWN`, `UNKNOWN`, `ENOMEM`, and `Unknown system error*` codes added to the transient-error set, improving retry behavior on platforms that return non-standard POSIX errors.

## Notes

`CLAUDE_CODE_ENABLE_MORNING_BRIEF` and `CLAUDE_CODE_MORNING_BRIEF_PROMPT` are removed in this version. If you were using the morning brief feature, the environment variables no longer have any effect.

JetBrains terminal detection (`TERMINAL_EMULATOR=JetBrains-JediTerm` parent-process walk) has been removed from the startup initialization path. Terminal identification now relies only on `process.env.TERMINAL` and similar standard sources.


Generated with:
- tool: `harness-investigations@d5cccf8-dirty`
- provider: `claude`
- model: `claude-sonnet-4-6`
- primary diff: `archive/claude-code/changes/changes-v2.1.213.md` (filtered astdiff)
- string diff: `archive/claude-code/changes/string-diff-v2.1.213.txt`
