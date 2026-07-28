# Changelog for version 2.1.217

## Summary

This release overhauls the Workshop Artifact skill so decision clicks update the published page directly through a browser self-capability rather than going through the interactions API. MCP tool failures now throw typed `McpToolError` exceptions inside workflow scripts instead of silently returning `{error: string}`. Skill discovery switches from reading a `skill://index.json` resource to calling a paginated `skills/list` MCP method, and path-containment checks gain significantly hardened handling for UNC shares, `/net` automounts, device namespaces, and macOS `/System/Volumes/Data` paths.


## New Features


### MCP Tool Errors Now Throw in Workflow Scripts

What: When a workflow script calls an MCP tool and that tool fails, the script now receives a thrown `McpToolError` exception (with `.toolName`, `.error`, and `.detail` properties) instead of a `{error: string}` return value. This matches the documented contract and lets scripts use try/catch to distinguish tool failures from successful results.

Details:
- The new `McpToolError` class crosses the VM realm boundary safely — the host-side wrapper throws by name and the sandbox rebuilds a VM-realm Error so scripts never hold a host-realm object.
- The `.detail` property carries the parsed JSON body when the tool error was a JSON object.
- The flag `tengu_repl_mcp_error_throw` controls this behavior (defaults to `!0` — enabled).
- REPL/workflow script context now documents: "MCP tool calls (`mcp__*`) THROW on failure (rate limits, server errors, permission denials) — `e.message` carries the tool error (`e.detail` the parsed body when it was JSON). Let the throw abort the script unless you can genuinely proceed without the result."

Evidence: New `McpToolError` class and VM-realm rebuild (search for `"McpToolError"`)


### Workshop Artifact Self-Update via `self` Capability

What: The Workshop skill's published artifacts now handle decision clicks directly in the browser — clicking an option row fetches the stored source, mutates the resolved decision, and publishes the new version via `window.claude.self.publish`, eliminating the round-trip through the interactions API.

Details:
- The first publish must declare `capabilities: {self: {}}` to enable self-update; subsequent republishes should omit the field (omission carries the declaration forward; sending `{}` clears it and option rows go inert).
- Clicking an option shows optimistic UI immediately, then fetches the stored source (not the live DOM) to build publishable bytes — this ensures no client-runtime DOM artefacts (theme stamps, hljs spans, script notes) leak into stored content.
- Concurrent clicks are handled via compare-and-swap on the server: the loser's browser reloads to the winner's version.
- Authorization stays server-side; the browser script holds no authority — the shell enforces write access and consent per publish call.
- The loop protocol changed: instead of reading open interactions via the interactions API, the session now diffs the published page against its local markdown to discover resolved decisions.
- Workshop documents no longer include a `Source:` breadcrumb line.

Evidence: Decision-option wiring script in updated HTML template (search for `"window.claude.self"` and `"capabilities: {self: {}}"`)


### `skills/list` MCP Method Replaces `skill://index.json`

What: MCP skill discovery now calls a paginated `skills/list` JSON-RPC method instead of reading a `skill://index.json` resource. The new method returns skills with a `uri` field (replacing the old `url` field) and supports cursor-based pagination for servers with many skills.

Details:
- If an MCP server returns `MethodNotFound` for `skills/list`, it is silently skipped (not an error).
- Partial results are preserved: if page N fails after page 0 succeeds, Claude uses the entries already fetched from prior pages.
- Entries with malformed, missing, or oversized fields are dropped with a count logged ("N skills/list entries skipped (malformed, missing, or oversized fields)").
- A per-page and per-total cap is enforced; if the cursor isn't exhausted, a warning is logged.

Evidence: New `Ycy()` paginator (search for `"skills/list"`, `"skills/list failed ("`, `"skills/list page"`)


### Usage-Limit Grace Window Signal

What: Claude Code now tracks a grace-window state when the API reports that you are in a usage-limit grace zone (via `anthropic-ratelimit-unified-grace-status` and related utilization headers). While in the grace window, a status bar message reminds you to wrap up: "[Usage limit reached — grace window active. Wrap up: finish or ...]".

Details:
- Grace state is derived from `anthropic-ratelimit-unified-grace-5h-utilization` and `anthropic-ratelimit-unified-grace-7d-utilization` response headers — whichever is higher.
- The state is latched: it turns on when utilization > 0 and clears when a subsequent response reports it back at zero. Because extended requests may stop mid-session, UI should expire via `resetsAt` rather than waiting for a clearing event.
- A new `rateLimitGraceActive` field in the session usage schema tracks this state.
- Feature flag: `tengu_lantern_spool` controls whether the extended request headers are sent.

Evidence: New grace state machine (search for `"anthropic-ratelimit-unified-grace-status"`, `"anthropic-ratelimit-unified-grace-5h-utilization"`)


### Emoji Completion Setting

What: A new `emojiCompletionEnabled` boolean setting lets users disable the `:emoji:` shortcode typeahead — both the suggestion popup and the `:name:` inline replacement. When absent or `true`, emoji completion is enabled (existing behavior); set to `false` to turn it off.

Evidence: New Zod schema field (search for `"When false, the :emoji: shortcode typeahead"`)


### Concurrent Subagent Limit Enforcement

What: When a session reaches the concurrent subagent limit, agents now receive an explicit error message: "Concurrent subagent limit reached. You can run N at once. Do not retry. If the user wants more concurrent subagents, ask them to increase CLAUDE_CODE_MAX_CONCURRENT_SUBAGENTS."

Details:
- The `runningSubagents` counter is tracked in session state and checked before spawning.
- The limit defaults to a server-controlled value.

Evidence: New message constant (search for `"Concurrent subagent limit reached. You can run"`)


### Subagent Depth Configurable via Feature Flag

What: The maximum subagent spawn depth can now be controlled server-side via the `tengu_hazel_trellis` feature flag (in addition to the existing `CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH` env var). The env var takes precedence over the flag.

Details:
- Worker agent prompts now mention the `Task` tool for fan-out at non-depth-cap workers: "If you have the Task tool, you may use it to fan out (e.g. `/simplify`, `/code-review`, or your own parallel research/verification) — workers at the depth cap don't receive it."

Evidence: New depth resolver (search for `"tengu_hazel_trellis"`, `"CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH"`)


### Bridge Terminal Session Isolation Message

What: When you open a CLI terminal attached to a running Claude.ai browser session (bridge mode), the terminal now displays: "This terminal now has its own copy of the session: new work here stays local and will not appear in the Claude app. To continue on your phone later, run /remote-control in this session."

Evidence: New warning block in bridge session setup (search for `"This terminal now has its own copy of the session"`)


### Transcript Saving Status Messages

What: Two new messages appear in the UI when transcript saving is suppressed:
- "Transcript saving is off — CLAUDE_CODE_SKIP_PROMPT_HISTORY is set" (when the `CLAUDE_CODE_SKIP_PROMPT_HISTORY` env var is set)
- "Transcript saving is off — inherited CLAUDE_CODE_CHILD_SESSION marker" (when a nested session inherits the child-session marker)

Details:
- `CLAUDE_CODE_SKIP_PROMPT_HISTORY` is a new env var that disables transcript writing.
- `CLAUDE_CODE_FORCE_SESSION_PERSISTENCE=1` is referenced as a way to override suppression and keep future transcripts (search for `"restart with CLAUDE_CODE_FORCE_SESSION_PERSISTENCE=1"`).

Evidence: New persistence-suppression classifier (search for `"CLAUDE_CODE_SKIP_PROMPT_HISTORY"`)


### Auto-Update Executable Self-Healing

What: If Claude Code's own executable is missing after a failed update, the updater now scans retired directories for a preserved `.old.<ts>` copy and restores the executable from it before attempting a fresh update download.

Details:
- Logs "Restored missing [path] from preserved copy [path] before update attempt" on success.
- Logs "Failed to restore missing [path] from preserved copy [path]: [error]" on failure.
- If no preserved copy is found: "No preserved [name].old.<ts> found in N retired dir(s) — sweep restore skipped."
- The new message for total failure (no preserved copy and no restore): "Your Claude Code executable could not be restored after the failed update and no preserved copy was found. Reinstall with: npm i -g ..."

Evidence: New sweep-restore function (search for `"from preserved copy"`, `".old.<ts> found in"`)


## Improvements


### Path Containment Hardened Against Adversarial Path Shapes

The worktree-isolation containment check was rewritten to handle a broader set of path spellings that could previously escape containment:

- UNC shares (`\\server\share`) and `/net/hostname` automounts are now explicitly classified as network-shaped and refused when the checkout root is local.
- Device-namespace paths (`\\?\...`) on Windows are detected and refused.
- Paths with trailing dots or spaces (Windows API quirk) are detected.
- macOS `/System/Volumes/Data/` prefixes are normalized before comparison.
- Paths with raw dot-segments (symlinks storing `.` or `..`) are refused as unresolvable.
- Case-insensitive path comparison is applied correctly on macOS and Windows.

New error messages distinguish the failure reason:
- "This command was blocked because its working directory is network-shaped (a UNC share or /net automount spelling)..."
- "This command was blocked because its working directory is spelled in a form that cannot be safely resolved..."
- Write operations similarly report: "This write was blocked because the path is network-shaped..." and "This write was blocked because the path is spelled in a form that cannot be safely resolved..."

A case-mismatch hint is appended when the path is the same as the registered path except for letter case: "(this path differs from the registered spelling only by letter case — respell it to match [worktree] exactly)".

Evidence: New path resolver subsystem (search for `"bg-containment: refusing"`, `"resolves-to-trailing-dot-or-space"`, `"wsl.localhost"`)


### Brace Pattern Expansion Budget

Brace pattern expansion in file-glob inputs is now subject to a budget (result count × byte size). If expansion would exceed the budget, the pattern is used unexpanded and a warning is logged: "Brace pattern expansion exceeds the budget; using it unexpanded: [pattern]". This prevents pathological inputs from causing combinatorial explosion.

Evidence: New `odg()` expander with budget (search for `"Brace pattern expansion exceeds the budget"`)


### Transcript Write Degradation Detection

A new subsystem tracks repeated transcript write failures. After consecutive failures from a drain, materialize, or adopt operation, the session enters a "degraded" state. On exit, if degraded, the following is logged: "flushSessionStorageAtExit: transcript writer degraded (ENOSPC at [source]) — entries since the failure window may be missing from the transcript". Tracked error codes: `ENOSPC`, `EROFS`, `EDQUOT`, `ENAMETOOLONG`; on Linux also `EACCES`, `EPERM`.

Related: "Transcript writes are failing ([reason])" messages in the UI now represent this state.

Evidence: New `s1t()` failure tracker and `vBs` subsystem (search for `"flushSessionStorageAtExit: transcript writer degraded"`, `"tengu_transcript_write_failed"`)


### Memory Rating UI

The memory management UI gains a rating flow: "Rate this memory: / pick good or bad" with actions "Thanks — noted as a good memory." and "mark bad and delete". A "view memories" link and "Memories recalled this session" / "No memories recalled yet" display states are also added.

Evidence: New rating strings (search for `"Rate this memory:"`, `"view memories"`, `"Memories recalled this session"`)


### Workflow Policy Gate Split

The single error message for disabled workflows is now split into two distinct messages depending on the source of the policy:
- "dynamic workflows are disabled for this session (managed settings `disableWorkflows`)."
- "dynamic workflows are disabled for this session (org policy `allow_workflows`)."

Evidence: New `zin()` gating function (search for `"managed settings \`disableWorkflows\`"`)


### Managed Settings Protect OTEL Telemetry Endpoints

When managed settings specify an `otelHeadersHelper`, lower-trust scopes (project or user settings) can no longer redirect the telemetry signal endpoints (`OTEL_EXPORTER_OTLP_*`). The env var is removed with a warning: "Dropping [var]: managed settings claim [signal], so lower-trust scopes cannot redirect [channel]."

Evidence: New `cwd()` enforcement function (search for `"managed settings claim"`, `"OTEL_EXPORTER_OTLP_"`)


### Screen Reader Startup Quiet Timer

A configurable startup quiet period (`CLAUDE_AX_STARTUP_QUIET_MS`, up to a capped maximum) now suppresses initial screen reader output during CLI startup. After the quiet period, a deferred render fires. This reduces noise for screen reader users on startup.

Evidence: New `r6c()` quiet timer and `srStartupQuietTimer` (search for `"CLAUDE_AX_STARTUP_QUIET_MS"`)


### Skill Proposal Cleanup

Old skill proposals (type `skill-proposal`) in the memory/proposals directories are now cleaned up during periodic maintenance sweeps along with the existing stale-file cleanup.

Evidence: New `l4p()` cleaner (search for `"skill-proposal"`)


### MCP Discovery Cache `.json.lock` Directory Cleanup

The MCP discovery cache cleanup now also removes stale `.json.lock` subdirectories (used as advisory locks), not just stale `.json` and `.json.tmp.` files.

Evidence: Updated `nob()` cleaner (search for `".json.lock"`)


### Session Resume: Malformed Attachment Validation

When restoring a session from transcript, attachment entries with missing or malformed payloads are now silently dropped with an error log rather than causing a restore failure. The log reads: "resume: dropped N attachment entries with a missing or malformed payload — the session transcript appears partially corrupt."

Evidence: New `rQr()` validator (search for `"resume: dropped"`, `"the session transcript appears partially corrupt"`)


### `footer:dismiss` Key Binding

The `backspace` and `delete` keys now trigger the new `footer:dismiss` action in footer context, providing a keyboard shortcut to dismiss the footer without navigating away.

Evidence: New key binding entries (search for `"footer:dismiss"`)


### Plugin and Skill Search Availability Feedback

The UI now shows "Plugin and skill search is unavailable right now; please try again." when skill/plugin search fails, rather than silently returning no results.

Evidence: New error string (search for `"Plugin and skill search is unavailable right now"`)


## Bug Fixes

- Feature-flag request cancellation: when a feature-flag remote request is not sent (e.g., falls back to local), the pending request slot is now properly cancelled before the local fallback executes. (search for `"cancelRequest"` in the request routing path)

- Auto-mode setup proposals now correctly carry the `scope` field through to the returned proposal object, fixing an issue where the scope selection was not reflected in the apply step. (search for `"proposal: { ...p.proposal, mode: \"append\", scope: e.scope }"`)

- REPL script context no longer double-declares the `budget_usd` binding; it was registered twice under different async/sync wrappers. (search for `"budget_usd"` in workflow context setup)

- Session file path update now uses `setSessionFile()` instead of directly assigning `r.sessionFile`, ensuring any observers of the session file path are notified correctly. (search for `"setSessionFile"`)


## In Development


### Usage Credits Display [In Development] — Gated by `tengu_satchel_banjo`

What: A message indicating how long usage credits are valid will appear: "Usage credits are valid for N months. Learn more: https://support.claude.com/en/articles/12429409".

Status: Feature-flagged — controlled by `tengu_satchel_banjo` (defaults false).

Evidence: `E0b()` function (returns `null` when flag off, search for `"tengu_satchel_banjo"`, `"Usage credits are valid for"`)


### Remote Workflow Launch Events [In Development] — CCR Sessions Only

What: Remote/CCR sessions can receive `workflow_launch` server events via SSE that carry a filestore bundle pointer. The CLI fetches the bundle, verifies its SHA-256, parses it, and dispatches the workflow script via a hidden `/workflow-launch-exec` command. This allows server-side orchestration to trigger workflow execution in a running CLI session.

Status: Active infrastructure, but only reachable in sessions running under `CLAUDE_CODE_REMOTE` with an SSE transport. The hidden command `workflow-launch-exec` is not user-invocable. At most one `workflow_launch` event is allowed per session.

Details:
- Bundle format is versioned; unknown format versions are refused.
- SHA-256 integrity is verified before execution.
- Workflow policy gates (`disableWorkflows`, `allow_workflows`) still apply, except when the carrier is server-authored and `CLAUDE_CODE_REMOTE_SESSION_ORIGIN=review`.
- Error layers: `not-remote-session`, `launch-payload`, `bundle-fetch`, `payload-digest-mismatch`, `args-parse`, `policy-gate`, `launch-protocol`.

Evidence: New `ci_()` event handler and `kLo()` executor (search for `"workflow_launch received outside a remote (CCR) session"`, `"/.workflow/"`, `"workflow-launch-exec"`)


### Bridge Placeholder Sweep [In Development] — Gated by `tengu_bridge_placeholder_sweep`

What: A background sweep identifies and archives orphaned REPL bridge session placeholders — session IDs in the local store whose corresponding server session was never used (updated_at equals created_at) and whose originating process is no longer running.

Status: Feature-flagged — `tengu_bridge_placeholder_sweep` (defaults true, but `Js()` / interactive-session check may gate it further).

Evidence: New `yfd()` sweep and `dLy()` checker (search for `"[bridge:placeholder] archived orphaned placeholder"`, `"tengu_bridge_placeholder_sweep"`)


### Four New Unnamed Feature Flags

Four new feature flags are wired to env var overrides but their intended behaviors are not visible from string evidence alone:

- `tengu_amber_astrolabe` (env `CLAUDE_CODE_AMBER_ASTROLABE`)
- `tengu_bison_cairn` (env `CLAUDE_CODE_BISON_CAIRN`)
- `tengu_larch_cistern` (env `CLAUDE_CODE_LARCH_CISTERN`)
- `tengu_alder_wicket` (env `CLAUDE_CODE_ALDER_WICKET`)
- `tengu_heron_tallow` (env `CLAUDE_CODE_HERON_TALLOW`)

All default to disabled. No user-facing strings are associated with them in this release.

Evidence: New flag registration functions (search for `"tengu_amber_astrolabe"`, `"tengu_heron_tallow"`)


Generated with:
- tool: `harness-investigations@d5cccf8-dirty`
- provider: `claude`
- model: `claude-sonnet-4-6`
- primary diff: `archive/claude-code/changes/changes-v2.1.217.md` (filtered astdiff)
- string diff: `archive/claude-code/changes/string-diff-v2.1.217.txt`
