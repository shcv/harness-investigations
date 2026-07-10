# Changelog for version 2.1.203

## Summary

This release adds artifact listing (browse previously published claude.ai artifacts from the CLI), a new `background_tasks_changed` protocol event for IDE surfaces, and `ANTHROPIC_FOUNDRY_AUTH_TOKEN` support. It also brings notable improvements: proxy URL validation with clear error messages, a new E2BIG spawn diagnostic when sandbox worktrees overflow the OS argument limit, significantly reduced break-reminder defaults (30 min instead of 120), smarter worktree lock safety, and MCP roots change notifications.


## New Features


### Artifact Listing

Claude can now list your previously published artifacts on claude.ai directly from the CLI. The first time per session you ask, Claude prompts for confirmation before fetching; subsequent fetches in the same session run without an extra ask.

Usage:

Ask Claude naturally: "list my published artifacts" or "what artifacts have I shared?" Claude calls the listing tool automatically.

Details:
- Returns artifact titles, URLs, and last-updated timestamps (up to 25 results by default; pass a higher `limit` up to 50)
- Only lists artifacts you own (`rel: "mine"`)
- Requires claude.ai OAuth credentials; prompts you to `/login` if missing
- You can pass an artifact URL from a previous session as the `url` parameter when republishing to keep the same link
- Retries once with a short delay on transient network errors or 5xx responses

Evidence: artifact listing HTTP client (search for `"/api/frame/frames?limit="`) and confirmation gate (search for `"First artifact listing this session requires confirmation"`)


### `background_tasks_changed` Protocol Event

A new `system` event type is now emitted over the inter-process query protocol whenever the set of live background tasks changes: a task starts, completes, is killed, or an agent is backgrounded.

Details:
- Payload: `{ type: "system", subtype: "background_tasks_changed", tasks: [{ task_id, task_type, description }] }`
- REPLACE semantics: the full current set is sent each time, so consumers swap their state with each payload rather than tracking start/stop bookends
- Nothing is emitted at startup; consumers should reset to the empty set when the CLI process starts and let the first change repopulate it
- Primarily useful for IDE surfaces and thin clients that need a "is background work running?" indicator without maintaining complex edge-event state

Evidence: schema addition (search for `"background_tasks_changed"`)


### ANTHROPIC_FOUNDRY_AUTH_TOKEN

New environment variable for Anthropic Foundry authentication. Set this to a bearer token to authenticate without a Foundry API key.

Usage:
```bash
export ANTHROPIC_FOUNDRY_AUTH_TOKEN="<your-bearer-token>"
claude
```

Details:
- Takes precedence over `ANTHROPIC_FOUNDRY_API_KEY` when set
- When neither is present and `CLAUDE_CODE_SKIP_FOUNDRY_AUTH` is unset, falls back to Azure Default Credentials

Evidence: Foundry auth branching (search for `"ANTHROPIC_FOUNDRY_AUTH_TOKEN"`)


### Fleet View Past Sessions [Gradual Rollout]

The session manager (fleet/agents view) can now show past completed sessions intermixed with currently running ones in the "done" section, sorted by modification time. Past sessions are loaded from local transcript history and interleaved chronologically with live jobs.

Details:
- Past sessions show a title derived from transcript content (or a truncated session ID as fallback) and the directory where they ran
- Controlled by feature flag `tengu_fleet_past_sessions` or by setting `CLAUDE_CODE_FLEET_PAST_SESSIONS=true`
- Not yet available to all users

Evidence: past-session loader (search for `"tengu_fleet_past_sessions"`) and fleet view layout (search for `"[fleetview] past-session enumeration failed"`)


## Improvements


### Proxy URL Validation with Clear Errors

`https_proxy`, `HTTPS_PROXY`, `http_proxy`, and `HTTP_PROXY` values are now validated as complete URLs before use. Previously Claude Code would silently use any non-empty string; now invalid values (e.g., a hostname without a scheme) produce a clear error on startup:

```
Invalid proxy URL in HTTPS_PROXY: "proxy.example.com" cannot be parsed as a URL.
Proxy settings must be a complete URL including the scheme, e.g. "http://proxy.example.com:8080".
Fix or unset HTTPS_PROXY and restart Claude Code.
```

The same env vars are also detected via `/doctor`.

Evidence: proxy validator (search for `"Invalid proxy URL in"`)


### E2BIG Spawn Error Diagnostic

When the Bash sandbox fails to spawn a command because the OS exec argument limit (E2BIG) is exceeded — which can happen when many git worktrees have been registered, inflating the sandbox deny-path list — Claude Code now prints a precise diagnostic:

```
Could not start bash: the command line plus environment exceed the OS exec argument limit (E2BIG).
At spawn: command line 14 KiB across 82 args (largest single arg 4.2 KiB);
environment 32 KiB across 210 vars.
The Bash sandbox profile adds 94 filesystem deny paths to every command, 68 of them for
registered git worktrees, which grow this list without bound. From another terminal, remove
worktrees you no longer need (git worktree remove <path>; git worktree prune for
already-deleted checkouts), then restart Claude Code so the profile is rebuilt without them
— or relax the Bash sandbox for this session with /sandbox.
```

Evidence: E2BIG detector and diagnostic builder (search for `"E2BIG"`, `"filesystem deny paths"`)


### Break Reminder Defaults Reduced

The built-in break reminder fires much sooner by default:

| Setting | Old default | New default |
|---|---|---|
| `reminderIntervalMinutes` | 120 min | 30 min |
| `breakThresholdMinutes` | 15 min | 10 min |

The interval picker in `/config` was also revised: "Every 5 minutes" and "Every 15 minutes" options added; "Every 2 hours", "Every 3 hours", and "Every 4 hours" removed (they remain configurable via settings directly).

Evidence: schema description change (search for `"default 30"`) and UI options update (search for `"Every 5 minutes"`)


### Opus Pro Tip Updated to Sonnet 5

The contextual tip shown to Pro plan users who are running Opus with >50% of their usage window consumed now references Sonnet 5:

Before: "Sonnet 4.6 handles most coding tasks and uses your weekly limit roughly half as fast as Opus."
After: "Sonnet 5 handles most coding tasks and uses your weekly limit much more slowly than Opus."

Evidence: tip content update (search for `"Sonnet 5 handles most coding tasks"`)


### Worktree Lock Safety

Worktree locking now verifies ownership by PID before acquiring or releasing locks:

- When locking a worktree, if the initial `git worktree lock` fails (someone else holds it), Claude Code checks the lock's reason string for the owning PID. If that process is confirmed dead, the stale lock is cleared and a fresh lock is acquired.
- If the owning process is still alive, Claude Code treats itself as a "guest" in that worktree and skips the lock rather than overwriting it.
- When `EnterWorktree` switches into a nested repository's worktree, the `ownerRepoRoot` is now tracked so the original session's lock can be released correctly on exit.

Evidence: lock ownership check (search for `"[worktree] failed to re-lock"`) and PID-based verification (search for `"[worktree] is already locked"`)


### MCP Roots Change Notifications

When the set of workspace root paths changes — for example, when additional working directories are added or removed — all connected MCP servers now receive a `roots/list_changed` notification. Previously, MCP servers had to poll or rely on reconnection to discover root changes.

Evidence: notification broadcast (search for `"Failed to notify MCP servers of roots change"`)


### MCP Tool Idle Timeout Per-Server Override

MCP server configurations now accept a `timeout` field (in milliseconds). When a tool runs silently for longer than the global `CLAUDE_CODE_MCP_TOOL_IDLE_TIMEOUT` limit, a server-specific `timeout` setting in `.claude/mcp-servers.json` can extend the limit for just that server.

The timeout error message was updated to mention both options:

```
set a per-server "timeout" (ms) to allow longer silent runs for just this server;
otherwise set CLAUDE_CODE_MCP_TOOL_IDLE_TIMEOUT (ms) globally or to 0 to disable
```

Evidence: per-server timeout resolver (search for `"set a per-server \"timeout\""`)


### Stdin Unreadable Error Handling

When piped stdin is unreadable (e.g., due to a broken pipe or the parent process wiring it incorrectly), Claude Code now recovers gracefully instead of propagating an error. A warning is written to stderr:

```
Warning: stdin is unreadable (EISDIR), proceeding without piped input.
If you piped input, it was not received — pass it as a prompt argument, or check
that the process launching Claude Code wires stdin to a pipe or /dev/null.
```

Evidence: stdin error recovery (search for `"getInputPrompt: piped stdin unreadable"`)


### Transcript Cleanup Skipped When Settings Are Unreadable

If any settings file can't be read or parsed, transcript retention cleanup is now explicitly paused. This prevents accidental deletion when `cleanupPeriodDays` might be configured in a file that Claude Code can't currently access.

`/doctor` will now report: "Transcript retention cleanup is paused until the settings errors above are fixed."

Evidence: cleanup guard (search for `"Skipping cleanup: a settings file could not be read"`)


### `/code-review` Description Updated

The `/code-review` command description was revised to better reflect its current behavior:

Before: "runs three review agents on your changes — reuse, quality, efficiency — and fixes what they find before you commit."
After: "checks your diff for correctness bugs and cleanup opportunities before you commit — add --fix to apply what it finds."

Evidence: command tip (search for `"/code-review checks your diff"`)


### Strict Structured Output Schema Derivation

When generating structured output, Claude Code now attempts to derive a strict JSON schema (with `strict: true`). If the tool schema is not strict-compatible, it falls back to non-strict mode and logs a warning:

```
Strict structured-output schema derivation failed, falling back to non-strict: <reason>
```

Evidence: schema validator (search for `"Strict structured-output schema derivation failed"`)


### Claude Desktop Gateway Policy Enforcement Improved

For enterprise deployments using Claude Desktop through a managed gateway, the `/user/bootstrap` endpoint now explicitly checks that:
1. A managed policy is configured on the gateway at all (fails with a 404 and "Claude Desktop is not configured on this gateway — add a 'desktop:' block to a managed policy")
2. The matched policy contains a `desktop:` block (fails with "the policy matching this user does not opt into desktop — add a 'desktop:' block to it")

These error messages are now visible to admins debugging access issues.

Evidence: gateway bootstrap guard (search for `"Claude Desktop is not configured on this gateway"`)


### Terminal Size Preservation Across Relaunch

When Claude Code relaunches itself (e.g., during a self-update), the parent process now passes the current terminal dimensions via `CLAUDE_CODE_RELAUNCH_TERMINAL_SIZE` so the child process can restore `stdout.columns` and `stdout.rows` if they read as undefined immediately after exec.

Evidence: terminal size env var (search for `"CLAUDE_CODE_RELAUNCH_TERMINAL_SIZE"`)


### Artifact `favicon` Validation Message Improved

The error text for an invalid favicon was updated to be more concrete:

Before: "favicon must be one or two emoji — no markup"
After: "favicon must be the literal emoji character(s) — not an HTML entity, quoted string, or markup (send 📊, not '&#x1F4CA;' or '<svg/>')"

Evidence: favicon validation (search for `"favicon must be the literal emoji character(s)"`)


### Protocol Schema `@internal` Prefixes Removed

Several inter-process query event schemas that carried `@internal` in their descriptions had that prefix stripped. The following events are now treated as stable protocol:
- `progress` (long-running `control_request` status)
- `conversation_reset` (emitted by `/clear`, plan-mode exit)
- `active_goal` (goal stop-hook updates)
- Remote control auto-enable fields on the init response

Evidence: schema description changes (search for `"Emitted by /clear, plan-mode exit"`)


## Bug Fixes

- Terminal winsize reads that return garbage (non-finite, < 1) or absurd values now fall back to defaults (80×24) with a logged warning instead of propagating the bad dimension into layout calculations (search for `"terminal winsize read returned a garbage dimension"`)
- Worktree-isolated agent commands that resolve to the shared checkout (parent session's directory) are now blocked with an explicit error rather than silently running in the wrong directory (search for `"This agent is isolated in the worktree"`)
- `EnterWorktree` path matching is now case-insensitive on macOS and Windows (normalizes to lowercase before comparison) to match filesystem semantics (search for `"wVc"` at line ~289116)
- E2BIG spawn errors are now detected as such and reported with the new diagnostic message rather than surfacing as a generic spawn failure (search for `"E2BIG"`)


Generated with:
- tool: `harness-investigations@03136fb-dirty`
- provider: `claude`
- model: `claude-sonnet-4-6`
- primary diff: `archive/claude-code/changes/changes-v2.1.203.md` (filtered astdiff)
- string diff: `archive/claude-code/changes/string-diff-v2.1.203.txt`
