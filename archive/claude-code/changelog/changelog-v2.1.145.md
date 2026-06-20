# Changelog for version 2.1.145

## Summary
Claude Code 2.1.145 adds a scriptable `claude agents --json` mode for inspecting live background/interactive sessions, and gives plugin authors a stricter CI-friendly manifest validator. This release also improves `/usage-credits` handling for monthly spend limits, hardens shell-command analysis, and makes Remote Control and mounted-skill loading more resilient.


### JSON Output for `claude agents`
What: `claude agents` can now print live sessions as JSON, including background sessions, interactive sessions, status, PID, cwd, start time, and session metadata.

Usage:
```bash
claude agents --json
claude agents --cwd /path/to/project --json
```

Details:
- Works without a TTY, so scripts and dashboards can query active sessions.
- Filters to sessions under `--cwd` when a cwd filter is provided.
- Emits `kind` as `background` or `interactive`, and normalizes status to `idle`, `waiting`, or `busy` when available.
- Non-TTY invocations of plain `claude agents` now point users to `claude agents --json`.

Evidence: `claude agents` command adds `--json` and calls `printAgentsJson` (search for `"Print live sessions as a JSON array and exit"` and `"claude agents --json"`).


### Strict Plugin Manifest Validation
What: `claude plugin validate` now has a `--strict` option that treats warnings as validation failures.

Usage:
```bash
claude plugin validate ./my-plugin --strict
claude plugin validate ./marketplace.json --strict
```

Details:
- Intended for CI checks where warnings such as ignored fields, missing metadata, or manifest drift should fail the build.
- Without `--strict`, validation can still pass with warnings as before.
- With `--strict`, warning-only validation exits as failed and prints `Validation failed (--strict treats warnings as errors)`.

Evidence: plugin validate command adds `--strict` with CI wording (search for `"Treat warnings as errors (exit 1)"` and `"Validation failed (--strict treats warnings as errors)"`).


### Monthly Spend-Limit Recovery in `/usage-credits`
What: When usage credits are blocked by a monthly spend limit, Claude Code now nudges users toward adjusting that limit instead of only showing a generic usage-credit limit error.

Details:
- The rate-limit UI can show `You've hit your monthly spend limit.` as a warning.
- `/usage-credits` can present an “Adjust monthly spend limit” flow with keyboard controls.
- Users can raise the limit or remove it, with follow-up messages if the new limit is still below current monthly spend.
- The command itself existed in 2.1.144; the new part is the monthly spend-limit recovery path.

Evidence: spend-limit nudge path and UI (search for `"/usage-credits to adjust your monthly spend limit."`, `"Adjust monthly spend limit:"`, `"Removed monthly spend limit"`, and `"Increased monthly spend limit to"`).


### Better Plugin and Marketplace Manifest Diagnostics
What: Plugin validation now reports more actionable warnings for ignored or misplaced manifest fields.

Details:
- Unknown fields get “did you mean” suggestions when a close supported field exists.
- Cross-tool field spellings are called out as ignored by Claude Code unless renamed.
- Common external manifest fields are identified as harmless but unused.
- Marketplace `relevance` shape problems now get explicit warnings.
- `skills` entries pointing directly at a file now explain that entries must be directories containing `SKILL.md`.

Evidence: manifest warning helpers (search for `"Unknown field '"`, `"Claude Code ignores unrecognized fields at load time"`, `"cross-tool spelling of Claude Code"`, `"'relevance' must be an object containing topic and signals"`, and `"skills entries must be directories containing SKILL.md"`).


### Safer Shell Command Parsing
What: Claude Code’s shell analysis now detects more cases where the parser dropped or could not safely interpret shell text.

Details:
- Detects unparsed bytes inside concatenations and redirects.
- Detects unsafe redirect target concatenations containing `$` or backticks.
- Tracks bare assignments to non-allowlisted environment variables that could affect subsequent commands.
- These checks should reduce incorrect “simple command” classification for tricky shell syntax.

Evidence: shell parser safety reasons (search for `"Concatenation has unparsed bytes between children"`, `"Redirect has unparsed trailing bytes"`, `"Redirect target concatenation contains $/`"`, and `"Bare assignment to a non-allowlisted environment variable"`).


### More Informative Stop Hook Payloads
What: Stop and SubagentStop hooks now expose in-flight background work and session-scoped cron wakeups.

Details:
- Hook payload schemas now include `background_tasks` for running/pending/backgrounded work.
- Hook payload schemas now include `session_crons` for CronCreate, ScheduleWakeup, and `/loop` tasks.
- This helps hooks distinguish a finished session from one that is paused while background work or a scheduled wakeup is still outstanding.

Evidence: hook schema additions (search for `"In-flight background work (running/pending + backgrounded)"` and `"Session-scoped cron tasks (CronCreate, ScheduleWakeup, /loop)"`).


### Clearer Hook JSON Warnings
What: Hook JSON output with ignored keys now produces an explicit warning, including a targeted hint for misplaced `additionalContext`.

Details:
- Unknown top-level hook output keys are logged as ignored.
- Unknown nested `hookSpecificOutput.*` keys are also reported.
- If `additionalContext` is placed at the wrong level, the warning suggests `hookSpecificOutput.additionalContext`.

Evidence: hook output warning (search for `"Hook JSON output had unrecognized keys (ignored):"` and `"Did you mean hookSpecificOutput.additionalContext"`).


### Remote Control Environment Reuse
What: `claude remote-control` can preserve and reuse an existing remote environment across restarts when possible.

Details:
- On shutdown, Claude Code may preserve the environment instead of archiving and deregistering it.
- On startup, it checks for a prior environment pointer and requests reuse.
- If the backend cannot reuse it, users get a clear warning that existing `claude.ai/code` sessions from the previous run will not reconnect.

Evidence: Remote Control reuse path (search for `"Environment preserved. Restart `claude remote-control` to reconnect existing sessions."`, `"[bridge:init] Found prior environment"`, and `"Warning: Could not reuse the previous environment"`).


### Host-Managed Auth Refresh for Embedded CLI Sessions
What: SDK-hosted or embedded CLI sessions can request a fresh provider auth token from the host after a 401 when the host owns the credential.

Details:
- New host-auth refresh plumbing uses `CLAUDE_CODE_SDK_HAS_HOST_AUTH_REFRESH`.
- The token environment variable can be selected with `CLAUDE_CODE_HOST_AUTH_ENV_VAR`, defaulting to `ANTHROPIC_AUTH_TOKEN`.
- `CLAUDE_CODE_HOST_AUTH_REFRESH_TIMEOUT_MS` controls the refresh timeout.
- This is mainly relevant to integrations that launch Claude Code as a subprocess rather than users running the standalone CLI.

Evidence: host-auth refresh plumbing (search for `"CLAUDE_CODE_SDK_HAS_HOST_AUTH_REFRESH"`, `"CLAUDE_CODE_HOST_AUTH_ENV_VAR"`, `"getHostAuthToken callback"`, and `"host getHostAuthToken callback failed"`).


## Bug Fixes

- Fixed transient `/mnt` skill-loading races by retrying once when the first `readdir` returns empty for mounted skills directories. Evidence: mount retry path (search for `"first readdir was empty, retry returned"` and `"transient mount race"`).

- Prevented forked skill contexts from recursively invoking the same skill tool instead of executing the already-loaded skill instructions directly. Evidence: recursion guard (search for `"is already executing in this forked context"`).

- Improved OAuth refresh failure handling around invalid or compromised refresh locks, with clearer expected-failure logging. Evidence: OAuth refresh handling (search for `"OAuth refresh lock compromised"` and `"OAuth refresh failed (expected):"`).

- Added diagnostic logging when queued commands are dropped, which should make command-queue cleanup issues easier to trace. Evidence: queue cleanup log (search for `"[clearCommandQueue] dropping"`).

## Notes
No official release-note file for 2.1.145 was present in the provided archive paths, so this changelog is based on the filtered AST diff, AST-extracted string diff, and direct searches of `pretty-v2.1.144.js` and `pretty-v2.1.145.js`.


Generated with:
- tool: `harness-investigations@1d6cc84-dirty`
- provider: `codex`
- model: `gpt-5.5`
- reasoning effort: `medium`
- primary diff: `archive/claude-code/changes/changes-v2.1.145.md` (filtered astdiff)
- string diff: `archive/claude-code/changes/string-diff-v2.1.145.txt`
