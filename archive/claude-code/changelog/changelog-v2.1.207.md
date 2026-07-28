# Changelog for version 2.1.207

## Summary

This release adds a `/morning` daily brief command, project-wide permission grants for Claude Design, sibling-repo context in auto-mode setup, and credential cache invalidation for AWS Bedrock. It also rewrites the streaming markdown renderer for better code-block handling and tightens auto-mode security by blocking repo-controlled classifier rules.


## New Features


### `/morning` — Daily Morning Brief

What: A new slash command that produces a styled single-page HTML artifact summarizing the day's calendar, emails, chat messages, and documents. Can also be scheduled as a recurring weekday task.

Usage:
```
/morning
/morning Sections: calendar, email · role: I work in design
/morning set up a recurring brief at 8am Pacific
```

Details:
- Renders a single HTML artifact: date header, a day timeline from the calendar, and sections for what needs attention today
- Respects any sources connected (calendar, email, chat, docs) and silently skips unavailable ones
- When asked to set up, creates a scheduled task and immediately renders today's brief as a preview
- Custom prompt stored in `CLAUDE_CODE_MORNING_BRIEF_PROMPT` env var, or via the `tengu_morning_brief_config` feature flag
- Available on remote/co-work sessions and when `CLAUDE_CODE_ENABLE_MORNING_BRIEF=1`

Status: Available in remote/co-work sessions; for interactive sessions requires `CLAUDE_CODE_ENABLE_MORNING_BRIEF=1` or the `tengu_morning_brief_skill` flag.

Evidence: Morning brief skill registration (search for `"Your morning brief — run it now, or set it up as a recurring weekday task"`)


### Claude Design: Project-Wide `finalize_plan` Grant

What: The `finalize_plan` operation now accepts `scope: "project"`, which grants prompt-free writes to every path in a Design project for up to 4 hours — instead of the per-batch 15-minute grant on specific listed paths.

Details:
- Requires a `project_id` (validated: letters, digits, dot, underscore, dash only; length limit enforced)
- Project identity is server-verified before the approval dialog names it
- Not available in non-interactive, subagent, or PermissionRequest-hook sessions (where approvals cannot be recorded)
- Requires the Claude Design connection to be approved first (read the project to trigger the approval prompt)
- Falls back gracefully: if project identity cannot be verified, suggests the classic per-batch flow

Evidence: Project-scope finalize_plan guards (search for `"finalize_plan scope:\"project\" — approval grants prompt-free writes to every path in this project for up to 4 hours"`)


### `CLAUDE_CODE_WALNUT_SPIRE` — Unlock `plugin eval` Without a Feature Flag

What: The `claude plugin eval` subcommand (previously gated behind the `tengu_walnut_spire` server flag) can now be unlocked via an environment variable.

Usage:
```bash
CLAUDE_CODE_WALNUT_SPIRE=1 claude plugin eval <target>
```

Details:
- Same early-access behaviour as before; the env var is an alternative to the server-side flag
- Still shows "plugin eval is currently in early access" notice

Evidence: New `mvc()` function checks `tengu_walnut_spire` OR `CLAUDE_CODE_WALNUT_SPIRE` (search for `"CLAUDE_CODE_WALNUT_SPIRE"`)


### AWS Bedrock: Credential Cache with Timeout and Invalidation

What: AWS default-credential-chain resolution now has a configurable timeout and automatically invalidates cached credentials on 401/403 responses.

Details:
- New env var: `CLAUDE_CODE_AWS_CHAIN_RESOLVE_TIMEOUT_MS` (default: 60 000 ms) — caps the time spent resolving AWS credentials from the default chain, which can otherwise hang indefinitely
- On a 401 or 403 from Bedrock, the per-region credential cache is invalidated and the request retried once automatically
- Log line: "invalidated credential cache" (or "credential invalidation debounced" if the cache was cleared too recently)
- New env var: `CLAUDE_CODE_SKIP_AWS_CRED_CACHE=1` to bypass caching entirely

Evidence: Timeout wrapper (search for `"AWS default-chain credential resolve timed out"`) and invalidation logic (search for `"invalidated credential cache"`)


## Improvements


### `/auto-mode-setup`: Sibling Repo Docs Now Gathered

What adds to the context gather for `/auto-mode-setup`: CLAUDE.md or README from up to 3 recently-active repos in the same GitHub org (via `gh`, read-only).

Details:
- Fetched only when `gh` is authenticated and the `allow_auto_mode_sibling_docs` feature flag is set
- Not gathered when nonessential traffic is disabled or origin remote is not github.com
- Treated as unverified-provenance content (same trust class as the current repo's CLAUDE.md): corroborating evidence, not an authoritative source
- The setup preamble now says "fetched any sibling-repo docs from your GitHub org via gh (read-only)"

Evidence: Sibling repo fetch function (search for `"Sibling repo docs (via gh — unverified provenance)"`)


### `/auto-mode-setup`: Clearer `permissions.allow` Categorization

What: The flagged-entries section is split into two named groups with distinct stakes, replacing the previous single "over-broad" heading.

Details:
- **Entries auto mode ignores** (classifier-bypassing): bare or wildcard `Bash`, interpreter-prefix rules like `Bash(python3:*)`, `Bash(sudo:*)`, PowerShell equivalents, and any `Agent` rule. These don't affect auto mode but still apply elsewhere — removing them changes that too.
- **Destructive entries**: wildcarded `rm`, force-push, cloud-delete, world-writable `chmod`, piped credential reads. These are auto-approved at runtime with no classifier check.
- A capped list with a "re-run /auto-mode-setup to see the rest" note when entries exceed the display limit

Evidence: New two-group categorization (search for `"#### Destructive permissions.allow entries"` and `"#### permissions.allow entries auto mode ignores (classifier-bypassing"`)


### `/auto-mode-setup`: Security Hardening for `autoMode` Config Sources

What: `autoMode` configuration found in `projectSettings` (`settings.local.json`) or `localSettings` is now silently ignored for classifier purposes, with a warning logged.

Details:
- Only user settings, flag settings, and managed (policy) settings may supply classifier rules
- When a repo-controllable source contains `autoMode` keys, a one-time warning is emitted and a telemetry event fired (`tengu_settings_auto_mode_rules_untrusted_source_ignored`)
- The `/auto-mode-setup` gather now shows a sub-block for any `settings.local.json` `autoMode` content it finds, with guidance on migrating it to user settings

Evidence: Warning log (search for `"settings autoMode in"`) and source restriction (search for `"only user/flag/managed settings may set classifier rules"`)


### `/auto-mode-setup`: `hard_deny` and `deny` Now Supported

What: The setup flow now reads, proposes, and writes `hard_deny` and `deny` entries alongside `allow`, `soft_deny`, and `environment`.

Details:
- The `jq` command shown in Phase 6 now includes `hard_deny, deny`
- Existing `hard_deny` and `deny` entries are preserved when adding to an existing configuration

Evidence: Updated jq command (search for `"hard_deny, deny"`)


### Credit Purchase and Monthly Limit: Confirmation Step

What: Buying credits and setting a monthly spend limit now show a dedicated "Confirm amount" screen instead of submitting immediately on the amount entry screen.

Details:
- The amount entry (`cst()`) validates both "20" and "20.50" formats and shows "Enter an amount like 20 or 20.50" for invalid input
- After entering a valid amount, a separate confirmation screen shows the currency symbol and amount with a "Confirm amount" title (credit purchase) or "Set your monthly spend limit to" (limit)
- Auto-reload confirmation shows "Auto-reload will top your balance up to [amount]"
- The "Buys X of usage credits" success line appears in green once a valid amount is entered

Evidence: Confirmation step (search for `"Confirm amount"` and `"Auto-reload will top your balance up to"`)


### Streaming Markdown: Code Fence Tracking

What: The streaming markdown renderer (`rhs`, replacing `mps`) now tracks open code fences across render cycles, so partially-received code blocks display correctly and do not trigger spurious re-renders.

Details:
- Tracks whether the current streaming position is inside a fenced code block (backticks or tildes)
- Freezes completed sections into static chunks to reduce re-render cost for long responses
- Splits very long pending content at word or line boundaries before freezing, avoiding mid-emoji or mid-codepoint cuts
- When inside a fence, the provisional tail is prefixed with the opening fence marker so it renders as code

Evidence: Fence-aware streaming renderer (search for `"openFence"` or `"frozenSource"` in the new `rhs` function)


### Claude Design: Improved 401 Error Messages

What: Authentication failures from the Design tool now give more specific guidance depending on whether a refresh was attempted.

Details:
- "Claude Design authentication failed (HTTP 401): the credential was rejected and an automatic refresh did not produce a new one." — no refresh token available
- "Claude Design authentication failed (HTTP 401): a freshly refreshed credential was also rejected — likely a server-side access problem." — refresh succeeded but still 401
- `DesignAuth401Error` class tracks the `wasRetried` flag to pick the right message

Evidence: Two-path 401 messages (search for `"a freshly refreshed credential was also rejected"` and `"DesignAuth401Error"`)


### TeammateMailbox: Schema Validation and Pruning

What: Invalid entries in the teammate mailbox file are now detected on read, logged with structured error codes, and pruned automatically. Invalid write requests are also rejected.

Details:
- On read: entries failing schema validation are dropped, a warning logged, and the pruned file written back atomically
- Error codes distinguish: "not an object", "missing text", "null text", "non-string text", "schema validation failure"
- The top-level inbox file must be a JSON array; a non-array is reported and the mailbox treated as empty
- Prune log: `[TeammateMailbox] pruned N schema-invalid entries at <path>`
- Writes: messages failing schema validation are refused with a `refused mailbox write` log entry

Evidence: Prune logic (search for `"[TeammateMailbox] pruned"`) and write guard (search for `"TeammateMailbox: refused mailbox write failing schema validation"`)


### Remote Control: Clear Project-Locking Error

What: Attempting to change the project of an already-connected Remote Control session now immediately fails with a clear message instead of silently being ignored.

Details:
- Error: "Remote Control is already connected — a session's Project is fixed when it's created. Disconnect first, then re-run /remote-control --project to start a new session in the Project."
- Same clarification added to the `--project` flag's validation logic

Evidence: Project-fixed message (search for `"A session's Project is fixed when it's created"`)


### ScheduleWakeup: Session-Type-Aware Delay Guidance

What: The `## Picking delaySeconds` section in the ScheduleWakeup tool description now varies by session billing type rather than using one-size-fits-all cache guidance.

Details:
- Subscriber sessions (1-hour prompt-cache TTL): "no cache cliff inside [60, 3600] to pace around; scheduling extra wakeups to keep cache warm is pure waste"
- API / Bedrock / Vertex sessions (5-minute TTL): the existing cache-breakpoint guidance (270s vs 1200s+)
- Unknown or mixed context: a combined explanation covering both regimes
- Guidance is passed as a boolean flag (`true` = 1-hour TTL, `false` = 5-minute TTL, `undefined` = combined)

Evidence: Three-branch delay guidance function (search for `"This session's requests use a 1-hour Anthropic prompt-cache TTL"`)


### Native Installer: Clearer "Not Our Binary" Messages

What: When the `claude` binary was not installed by the native installer (not a symlink into `$XDG_DATA_HOME/claude/versions/`), the updater now explains this and gives actionable guidance instead of silently skipping.

Details:
- Skipping version cleanup: "Skipping native version cleanup: the launcher at [path] is externally managed, so the version(s) it needs cannot be determined"
- Not overwriting: "Not replacing [path]: it was not created by the native installer (not a symlink into a claude/versions/ directory) and is not an npm shim, so this update will not overwrite it. New versions still install under the versions/ directory; remove [path] and re-run the update to let the installer manage the launcher again."
- Custom wrapper advice: "If you put a launcher wrapper there on purpose, this is expected — new versions still install under $XDG_DATA_HOME/claude/versions, your launcher decides what runs, and automatic version cleanup is disabled on this machine."

Evidence: Three new skipping messages (search for `"Skipping native version cleanup"` and `"not created by the native installer"`)


### `extensions.worktreeConfig` Auto-Cleanup

What: When the last linked git worktree is removed, Claude Code now automatically cleans up the `extensions.worktreeConfig` setting from the repository's git config, restoring it to its pre-worktree state.

Details:
- Runs after a worktree is removed and the linked-worktree count drops to ≤1
- Removes both `extensions.worktreeConfig` and its related config key
- Log: "Restored extensions.worktreeConfig in [repo] after removing its last linked worktree"
- On failure: "Could not restore extensions.worktreeConfig for [repo]: [error]" (warning only)

Evidence: Cleanup function (search for `"Restored extensions.worktreeConfig in"` and `"enabledWorktreeConfigExtension"`)


### Bedrock AWS Key Pair Validation

What: Bedrock upstream connections now validate that `aws_access_key_id` and `aws_secret_access_key` are always set together, and that `aws_session_token` requires both.

Details:
- Error thrown immediately if only one of the key pair is present: "aws_access_key_id and aws_secret_access_key must be set together"
- Error if `aws_session_token` is set without the key pair: "aws_session_token requires aws_access_key_id and aws_secret_access_key"
- These validations also appear in the `authCredentials` schema as Zod refinements

Evidence: Validation error messages (search for `"bedrock upstream: aws_access_key_id and aws_secret_access_key must be set together"`)


### Env Var Whitespace Trimming

What: Model-selection and credential environment variables are now trimmed of leading/trailing whitespace before use. Settings schema validation also flags excess whitespace around enum values.

Details:
- `ANTHROPIC_DEFAULT_SONNET_MODEL`, `_OPUS_MODEL`, `_HAIKU_MODEL`, `ANTHROPIC_SMALL_FAST_MODEL`, and credential env vars now have `.trim()` applied
- Settings validation reports "excess whitespace around the value" for case-insensitive enum fields (e.g. scope values)

Evidence: Env var trimming (search for `"?.trim()"` around model env var reads) and validation (search for `"excess whitespace around the value"`)


### Permission Mode Downgrade Message Clarification

What: The message shown when permission mode is downgraded to default now correctly says "bypass requires accepting the disclaimer interactively first" instead of "bypass/auto requires…".

Details:
- Auto mode does not require interactive disclaimer acceptance; bypass mode does
- The old message incorrectly implied auto mode had the same interactive requirement

Evidence: Updated string (search for `"bypass requires accepting the disclaimer interactively first"`)


## Bug Fixes

- Plugin feedback survey: activity is now recorded per-plugin per-trigger, preventing duplicate survey appearances for the same plugin within the cooldown window (search for `"pluginActivity: recorded"`)
- TeammateMailbox write race: mailbox writes now use file locking (`lockfilePath`) to prevent concurrent write corruption (search for `"TeammateMailbox: refused mailbox write"`)
- Usage fetch: correctly handles non-object body responses in addition to fieldless objects, fixing an edge case where a non-object response slipped past the error check (search for `"Usage fetch returned a fieldless or non-object body"`)
- Git worktree security: `.git` pointer files and `config` paths are now checked against symlink-escape rules before being read, preventing symlink traversal through crafted worktrees (search for `"gitdir back-link is a symlink"` and `"git pointer file is a symlink"`)
- AWS credential: `ANTHROPIC_CUSTOM_HEADERS` containing an `x-api-key` header is now detected (`Fpe()`) and used to suppress the default `X-Api-Key` header, preventing duplicate key headers on Bedrock `bearer_token` connections (search for `"x-api-key"` in the new auth header check)


Generated with:
- tool: `harness-investigations@d5cccf8-dirty`
- provider: `claude`
- model: `claude-sonnet-4-6`
- primary diff: `archive/claude-code/changes/changes-v2.1.207.md` (filtered astdiff)
- string diff: `archive/claude-code/changes/string-diff-v2.1.207.txt`
