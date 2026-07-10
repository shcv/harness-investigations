# Changelog for version 2.1.196

## Summary

This release introduces a new `ReportFindings` tool for structured code review output, unifies the HTTP and SOCKS proxies into a single multiplexed port, adds Claude Preview as a new MCP integration, and ships substantial Windows sandbox improvements. There are also additions to hook event payloads, a new per-user Artifact toggle in settings, and improved security analysis for awk programs.

## New Features


### ReportFindings tool for code review

What: The code review workflow now uses a dedicated `ReportFindings` tool to emit structured findings rather than printing them as free text. Each finding includes the file path, line number, a one-sentence summary, a concrete failure scenario, an optional verify verdict (CONFIRMED or PLAUSIBLE), and an optional post-fix outcome.

Details:
- The tool accepts `{level, findings}` where `level` is one of `low`, `medium`, `high`, `xhigh`, or `max`
- `findings` is an array capped at 32 entries, ranked most-severe first
- Each finding has `file`, `line` (1-indexed, optional), `summary`, `failure_scenario`, `verdict` (set when a verify pass ran), and `outcome` (set when re-reporting after fixing)
- The UI renders findings with colored bullets: CONFIRMED in red, PLAUSIBLE in orange, fixed items with a checkmark
- Calling with an empty array is the correct way to report that nothing survived verification

Evidence: New tool constant (search for `"ReportFindings"`) and full schema at `WAl` (contains `"Repo-relative path of the file the finding is in"`)


### Unified HTTP+SOCKS proxy (Mux)

What: The sandbox network proxy now exposes a single port that multiplexes both HTTP CONNECT and SOCKS5 connections. Previously, HTTP and SOCKS had separate ports and separate listeners.

Details:
- The mux proxy detects the protocol from the first byte: SOCKS bytes (4 or 5) route to the SOCKS handler; all other bytes route to the HTTP backend
- On non-Windows platforms the HTTP backend binds to a Unix socket for zero-port-waste
- On Windows both backends bind on 127.0.0.1 with TCP port allocation
- First-byte timeout destroys the connection if no data arrives
- A 502 Bad Gateway response is sent if the backend is not yet bound when a connection arrives
- Old separate "HTTP proxy" and "SOCKS proxy" listener log lines are gone; now logs `Mux proxy (HTTP+SOCKS) listening on localhost:<port>`

Evidence: New `lea()` mux server function (search for `"mux: HTTP dispatch before backend bound; dropping"`) and `nop()` startup function (search for `"Mux proxy (HTTP+SOCKS) listening on localhost:"`)


### Claude Preview MCP integration

What: "Claude Preview" joins "Claude in Chrome" as a recognized MCP integration. Tools from this server use the `mcp__Claude_Preview__` prefix and require explicit permission before use.

Details:
- Permission prompt message: "Claude Preview requires permission."
- Permission can be granted per-session
- The tool name slug is computed from the string "Claude Preview"
- Added to the set of recognized chrome-type MCP servers alongside `claude-in-chrome`

Evidence: New `rno` module (search for `"Claude Preview"`) and permission check function `IXi` (search for `"mcp__Claude_Preview__"`)


### Artifact tool toggle in settings UI

What: A new "Artifacts" toggle appears in the settings panel, allowing users to explicitly enable or disable the Artifact tool independent of the plan-level default.

Details:
- New `enableArtifact` field in user settings (`boolean`, optional)
- Separate from the existing `disableArtifact` field — `enableArtifact` explicitly sets the value; `disableArtifact` remains for legacy compatibility
- The toggle is only shown when `artifactToggleable` is true (controlled server-side)
- Setting `enableArtifact: undefined` reverts to the plan default
- Also readable as `ONn()` which checks `policySettings`, `flagSettings`, and `userSettings` in priority order

Evidence: Settings schema change (search for `"Enable or disable the Artifact tool for this user. Unset = default by plan once the feature is available."`)


### `prompt_id` in hook event payloads

What: Hook events now include a `prompt_id` field — a UUID that correlates a single user prompt with all events generated until the next user prompt arrives.

Details:
- The same value is emitted as the `prompt.id` attribute on OpenTelemetry events, enabling joins between hook output and OTel traces
- The field is absent on events that occur before the first user input of the process lifetime
- Available in the hook context under `prompt_id`

Evidence: Settings schema addition (search for `"UUID correlating a user prompt with all subsequent events until the next prompt"`)


### awk static security analysis

What: The shell command safety analyzer now inspects awk programs for dangerous patterns that can execute arbitrary code or exfiltrate data.

Details:
- Detected patterns and their rejection reasons:
  - `system()` — executes arbitrary shell commands
  - Command pipes (`| "cmd"` or `| getline`) — executes arbitrary commands
  - `@load`/`@include` or indirect function calls — can execute arbitrary code
  - `extension()` — loads arbitrary native code (legacy gawk)
  - `/inet/` network sockets (gawk) — can exfiltrate data
- `awk`, `gawk`, `mawk`, and `nawk` all go through this analysis
- Commands where the awk program comes from a variable, `-f` flag, or stdin are flagged as statically unanalyzable

Evidence: New `naa()` analysis function (search for `"awk program contains system() which executes arbitrary commands"`)


### Windows sandbox ACL stamping with `--holder-pid`

What: The Windows sandbox now stamps file-deny ACLs using a `--holder-pid` argument to bind the denial to a specific process ID. This enables proper cleanup when the holder process exits.

Details:
- `srt-win acl stamp` is now called with `--holder-pid <pid>` and receives the deny lists as JSON on stdin
- Exit code 2 indicates partial success (some inputs skipped); exit code 0 is full success; non-zero throws an error
- `srt-win acl restore` similarly uses `--holder-pid`
- Changing the Windows sandbox group (groupSid or groupName) now throws an error requiring `reset()` then `re-initialize()`
- If the filesystem deny set changes mid-session the ACL stamp cannot be updated (it is session-wide); a warning is logged and the old set stays in effect
- New restrictions on Windows:
  - `filesystem.allowRead` (re-allow within denyRead) is not supported
  - `filesystem.allowWrite` is not supported (deny-only model)
  - Directory paths in deny lists throw with guidance to use explicit file paths
  - Per-exec filesystem deny via `customConfig` is not supported

Evidence: New `gta()` stamp function (search for `"[Sandbox Windows] acl stamp exit="`) and `bop()` updateConfig (search for `"Changing the Windows sandbox group requires reset() and re-initialize()"`)


### `cumulative_dropped_tokens` in compaction events

What: Each compaction event now carries a `cumulative_dropped_tokens` field tracking the running total of context tokens removed across all compactions in the session.

Details:
- Each compaction's contribution is approximately `pre_tokens − post_tokens`
- The value is monotonically increasing across compaction and `/clear` operations
- Field is optional for backward compatibility; absent on old events
- Used internally by the `padded-countdown` token reminder mode

Evidence: Schema addition (search for `"@internal Running total of context tokens compaction has removed so far, across this and every earlier compaction"`)


### `totalTokensReminder` padded-countdown mode

What: A new `padded-countdown` option for the `totalTokensReminder` internal setting counts down from a configurable budget using per-agent cumulative context spend, staying monotonic across compactions and `/clear`.

Details:
- New setting `totalTokensReminderBudget` (integer, positive) sets the starting budget; defaults to 15,000,000 tokens
- Budget can be overridden via the `CLAUDE_CODE_TOTAL_TOKENS_REMINDER_BUDGET` environment variable
- Server-controlled via GrowthBook; the existing `CLAUDE_CODE_TOTAL_TOKENS_REMINDER` env var still overrides the mode
- The other modes (`off`, `infinite`, `fixed`, `countdown`) remain unchanged

Evidence: Settings schema additions (search for `"@internal Starting budget (tokens) for totalTokensReminder 'padded-countdown' mode"`)


### Credential file masking improvements

What: The credential file masking system now handles edge cases gracefully: directories, binary files, and unreadable files all log a warning and are skipped rather than causing failures.

Details:
- Directories: logs `[credential-mask] Skipping masked file entry that resolves to a directory: <path> — use mode "deny" for directories.`
- Binary files (non-UTF-8 content): logs `[credential-mask] Skipping masked file with non-UTF-8 content (binary credential files are not supported in whole-file mask mode): <path>`
- Unreadable files: logs `[credential-mask] Skipping masked file (unreadable on host): <path> — <reason>`
- The `MaskedFileStore` class now manages temp files in a dedicated directory under `srt-credmask-*` prefix

Evidence: New `hea()` masking function (search for `"[credential-mask] Skipping masked file (unreadable on host):"`)


### Background session exit handoff

What: When Claude Code exits while background shells or workflows are still running, it now writes a handoff record so the next session startup can re-adopt them rather than losing track.

Details:
- Triggered when `CLAUDE_JOB_DIR` is set and the session is non-interactive
- Can be disabled with `CLAUDE_CODE_DISABLE_BG_EXIT_HANDOFF=1`
- Writes `adopt.json` with the PIDs, start times, output paths, and workflow run IDs of running tasks
- Shell tasks include `taskId`, `pid`, `procStart`, `startTimeTicks`, `command`, `description`, `outputPath`, and `kind`
- Workflow tasks include `taskId`, `workflowRunId`, `scriptPath`, `scriptSha256`, `argsJson`, and `transcriptDir`
- Logged as: `exit handoff: N background shell(s) and M workflow(s) handed to the next wake of this session`

Evidence: New `l2a()` handoff function (search for `"exit handoff: adopt.json write failed:"`)

## Improvements


### Skill tool description A/B test [Gradual Rollout]

What: A feature flag `tengu_russet_linnet` (or `CLAUDE_CODE_SKILL_DESC_REFRAME` env var) switches the Skill tool's description to a more concise variant focused on when and how to invoke skills.

Details:
- Default (flag off): existing verbose description beginning "Execute a skill within the main conversation..."
- New variant (flag on): a shorter description starting "A skill is a packaged set of instructions..."
- The new variant emphasizes that some skills run as subagents and return finished results
- Logged at startup: `skill_desc_reframe_arm_active source=env` or `source=growthbook`

Evidence: New `MSe` module (search for `"skill_desc_reframe_arm_active source="`)


### Code review workflow restructured

What: The code review finder strategy changed. Instead of one finder agent per review angle, the new approach uses one finder per correctness angle plus one finder covering all cleanup angles together, pooled before the verify phase.

Details:
- Old description: "One finder agent per review angle (correctness + cleanup + conventions)"
- New description: "One finder per correctness angle plus one finder covering all cleanup angles, pooled before verify"
- The verify phase is unchanged: one verifier per distinct (file, line) location
- Findings output now goes through `ReportFindings` (see New Features above)

Evidence: Updated description constant (search for `"One finder per correctness angle plus one finder covering all cleanup angles, pooled before verify"`)


### SendUserFile gains `display` parameter

What: The `SendUserFile` tool description now documents a `display` field that controls how the file is presented to the user.

Details:
- `'render'`: opens the file inline in the side panel — for HTML, SVG, Mermaid, images, PDFs
- `'attach'`: shows a download card only — for source code, spreadsheets, documents for other apps
- Omitting `display` lets the client decide by file type

Evidence: Updated tool description (search for `"How the client should present the file. 'render' opens it inline in the side panel"`)


### Plugin shorthand validation gives clearer error for non-GitHub hosts

What: The plugin `add owner/repo` shorthand now validates the format and returns a detailed error message when the input looks like a non-GitHub URL.

Details:
- Valid shorthand: `owner/repo`, `owner/repo#ref`, `owner/repo@ref`
- Invalid: full URLs, paths without exactly one `/`, or names not matching `[A-Za-z0-9]...[A-Za-z0-9]/[A-Za-z0-9._-]+`
- Error message for invalid input: `'<input>' is not a valid GitHub owner/repo shorthand. For a git repo, use the full https:// clone URL from your host (typically ending in .git — some hosts like Azure DevOps omit it). For a hosted marketplace.json, use its https:// URL. For a local path, use ./ or an absolute path.`

Evidence: Validation added in `tsr` (search for `"is not a valid GitHub owner/repo shorthand. For a git repo"`)


### Model catalog is now data-driven

What: The hardcoded per-model provider ID table was replaced by a generated catalog. Model display names and provider IDs now come from a single source of truth in `configs.ts`, validated at build time.

Details:
- The old static object with ~15 model entries is gone; a `CATALOG_ID_TO_KEY` map drives the new lookup
- Model family membership (`isFable`, `isMythos`, `isOpus`) now uses a `family` field from the catalog
- Model alias resolution (`"opus"` → current opus model ID) now goes through per-provider alias tables
- Old three-letter model name display functions replaced by a catalog lookup against `display_name`
- Build command: `bun run generate:model-catalog` validates the catalog

Evidence: New `WM` module (search for `"model catalog missing entry for '"`), alias functions (search for `"named CLAUDE_*_CONFIG export for '"`)


### Organization default model support

What: The client can now receive and apply an organization-level default model from the server. When an org sets a default, Claude Code respects it while still allowing user overrides (unless `override_user_selection` is true).

Details:
- Stored in `orgModelDefaultCache` in local state with fields: `name`, `updated_at`, `data_source`, `override_user_selection`, and optional `orgUuid`
- If `override_user_selection` is false, users can still pick a different model
- If the org default changes (newer `updated_at`), user's local model setting may be cleared
- UI hint `· Org default` appears next to the model name when the org default is in effect

Evidence: New `C4r()` function (search for `"orgModelDefaultCache"`) and UI hint (search for `"· Org default"`)


### `requires` field supported in skill frontmatter

What: Skill frontmatter parsing now picks up a `requires` field alongside existing fields like `agent`, `context`, and `isEnabled`.

Evidence: `requires: e.requires` assignment added in skill definition mapping (in the function building skill objects from frontmatter)


### Session relocated working directory tracking

What: Sessions now record `relocatedCwd` when the working directory is relocated. This persists across forks and resume, and shows up in session metadata.

Details:
- Stored in the session transcript under a `"relocated"` event type
- Cleared on resume (so a resumed session doesn't carry the old relocation)
- Accessible as `currentSessionRelocatedCwd` in session state

Evidence: New JSONL event type (search for `".orphaned-"` and `"relocated"` in session handling code)


### Duplicate agent name detection

What: When loading agent skills, duplicate `name:` values in frontmatter are now detected and reported.

Details:
- Error format: `- Duplicate agent name '<name>'`
- Fix guidance: `Fix: rename or remove all but one so the frontmatter 'name:' is unique.`

Evidence: New validation strings (search for `"Duplicate agent name '"`)


### Left-arrow multi-session shortcut uses single press

What: The keyboard shortcut to switch away from a multi-session queue now requires a single `←` rather than double `←←`.

Details:
- Previous UI text: `Press ←← again once the queue clears.` / `Press ←← again to confirm.`
- New UI text: `Press ← again once the queue clears.` / `Press ← again to confirm.`
- The "Running multiple Claude sessions?" prompt text changed from "Run" to "Press"

Evidence: String replacements (search for `"Press ← again once the queue clears."`)


### `tlsTerminate.excludeDomains` now warns about masked credentials

What: When a domain matches `tlsTerminate.excludeDomains` and TLS termination is skipped, the proxy now warns if any masked credentials are configured for injection at that domain — because they will not be injected.

Details:
- Log message: `tlsTerminate.excludeDomains: masked credential(s) <names> are configured for injection at <host>, but its connections are not terminated, so the upstream will receive the placeholder`
- Also logs: `Host <host> matches tlsTerminate.excludeDomains pattern <pattern>; skipping TLS termination`

Evidence: New `top()` function (search for `"tlsTerminate.excludeDomains: masked credential(s)"`)


### Alt screen background color restored on exit

What: When leaving alternate screen mode (e.g., closing the TUI), the terminal background color is now properly reset.

Details:
- New `setAltScreenBackground()` / `altScreenBackgroundColor` API on the terminal renderer
- On exit, emits a reset-background-color sequence before returning to the normal screen

Evidence: New `altScreenBackground` property (search for `"altScreenBackground"`) and `slt()` reset function


### `hasUnquotedGlob` tracked in shell command AST

What: The shell command parser now annotates each parsed command with `hasUnquotedGlob: true` when the command text contains unquoted glob characters. This feeds the safety analyzer.

Evidence: `hasUnquotedGlob: R5e(e.text)` added to AST node construction in the shell parser

## Bug Fixes

- gRPC keepalive failures now call `session.destroy()` instead of `session.close()`, fixing a hang when a connection drops under load (search for `"Connection dropped by keepalive timeout"`)
- Vertex SDK provider check now guards against a null model name before proceeding, preventing a crash when the model is unset (search for `"AnthropicVertex"` null guard)
- `ERR_NOT_REGULAR_FILE` is now caught alongside `ENOENT` when reading config files, so devices, FIFOs, and sockets in config paths produce a clear error rather than a crash
- Background session daemon no longer sets `CLAUDE_ENABLE_STREAM_WATCHDOG=1` in the child environment (the watchdog was removed)
- Speculation (forked agent preview) errors are now captured and reported to telemetry instead of being silently dropped (search for `"Speculation runForkedAgent failed"`)
- Compaction API errors now use a redacted sentinel string instead of including the potentially-sensitive summary text in error reports (search for `"compactConversation: api_error (summary text redacted)"`)

## In Development


### Background task activity fd [In Development]

Status: Infrastructure only — new env var `CLAUDE_RUNNER_ACTIVITY_FD` defined but not yet surfaced in user-facing configuration.

What: A file descriptor for reporting runner activity to a parent process, intended for supervisor/monitoring integrations.

Evidence: String `"CLAUDE_RUNNER_ACTIVITY_FD"` added; activity fd logging (search for `"[remote-io] activity fd"`)


Generated with:
- tool: `harness-investigations@03136fb-dirty`
- provider: `claude`
- model: `claude-sonnet-4-6`
- primary diff: `archive/claude-code/changes/changes-v2.1.196.md` (filtered astdiff)
- string diff: `archive/claude-code/changes/string-diff-v2.1.196.txt`
