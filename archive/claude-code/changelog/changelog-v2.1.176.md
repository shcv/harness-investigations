# Changelog for version 2.1.176

## Summary

This release introduces custom footer link badges — regex-based patterns that turn CLI output into clickable links — and ships a dedicated Notifications panel in `/config`. Fork subagents are now explicitly opt-in rather than the implicit default when no `subagent_type` is provided. A long-standing remote control bug (CC-2659) that silently switched the terminal's active model when connecting from a phone is fixed. The Project tool now surfaces file uploads alongside text docs. The `rm`/`rmdir` and `sed` safety analyzers were substantially rewritten.


## New Features


### Custom Footer Link Badges (`footerLinksRegexes`)

What: A new user setting lets you define regex patterns that scan each turn's output (tool results and assistant responses) and render clickable footer badges when matched. Use this to surface ticket IDs, PR numbers, run IDs, or other identifiers printed by your project's CLI as direct deep-links.

Usage:
```json
// In ~/.claude/settings.json (user settings — ignored in project/local settings)
{
  "footerLinksRegexes": [
    {
      "type": "regex",
      "pattern": "(?<id>ISSUE-\\d+)",
      "url": "https://linear.app/myteam/issue/{id}",
      "label": "{id}"
    }
  ]
}
```

Details:
- Each entry requires `type: "regex"`, a `pattern` (matched against turn output with the `g` flag), and a `url` template
- The optional `label` field sets badge text; it defaults to the full match if omitted
- `{name}` placeholders in `url` and `label` are filled from named regex capture groups (e.g., `(?<id>\\d+)` → `{id}`); capture group values are URL-encoded in `url`
- The URL origin must be a literal in the template — no `{placeholders}` in the scheme or host
- Allowed URL schemes: `https:`, `http:`, `vscode:`, `vscode-insiders:`, `cursor:`, `windsurf:`, `zed:`, `jetbrains:`, `idea:`, `slack:`, `linear:`, `notion:`, `figma:`
- At most 5 badges render at once; the oldest is displaced as new matches arrive; `/clear` removes all regex-generated badges
- Only read from user, flag, and managed settings — ignored in project `.claude/settings.json` and `.claude/settings.local.json`
- The `prUrlTemplate` setting's badge is now rendered as the first footer-link badge; its description was updated to call it a "footer link badge" accordingly
- Entries with unrecognized `type` values are preserved in settings but silently skipped, enabling forward-compatible configs

Evidence: New `footerLinksRegexes` setting (search for `"Extra clickable footer badges that appear when a regex matches turn output"`)


### Notifications Panel in /config

What: The notification channel setting in `/config` now opens a dedicated full-screen `Notifications` panel instead of an inline enum selector.

Details:
- The panel groups all notification options in one place: channel selection (cycled with arrow keys), "Notify when Claude needs you", and "Notify when Claude is done"
- `iterm2_with_bell` now displays as `iterm2+bell` in the panel and in the terminal title
- Other channels — `auto`, `iterm2`, `terminal_bell`, `kitty`, `ghostty`, `none` — are unchanged

Evidence: New `BH9` Notifications component (search for `"Notify when Claude needs you"`)


### Fork Subagents Now Explicitly Opt-In

What: The Agent tool's fork behavior changed. `subagent_type: "fork"` must now be passed explicitly. Previously, omitting `subagent_type` when the fork experiment was active created an implicit fork that inherited your full conversation context. Now, omitting `subagent_type` always spawns a fresh general-purpose agent with zero context.

Details:
- Old description: "Implicit fork — inherits full conversation context. Not selectable via subagent_type; triggered by omitting subagent_type when the fork experiment is active."
- New description: "Fork — inherits full conversation context. Selected explicitly via subagent_type: 'fork' when the fork experiment is active; never the default."
- The `model` parameter on the Agent tool now explicitly notes "Ignored for `subagent_type: \"fork\"` — forks always inherit the parent model."
- When spawning a fresh agent, all docs now read "Any agent other than a fork starts with zero context" (was "When spawning a fresh agent (with a `subagent_type`), it starts with zero context")

Evidence: Agent description update (search for `"(except subagent_type: \"fork\", which inherits your context)"`)


## Improvements


### Remote Control: Model and Permission Mode Sync at Connect Time

Two new fields — `current_model` and `current_permission_mode` — are now included in the Remote Control connect handshake. Remote clients (web/mobile) now sync their model dropdown *to* the CLI's active model at connect time, instead of sending their own default and overriding it. This fixes CC-2659, where connecting from a phone would silently switch the terminal's active model to the phone's default.

Evidence: New schema fields (search for `"The CLI's active model at connect time. Remote Control clients (web/mobile) sync their model dropdown TO this value on connect"`)


### Project Tool: File Uploads Now Visible

The Project tool now surfaces file uploads (PDFs, images, docx, etc.) alongside text docs:

- `project_info` now lists file uploads under `## Project files (N)` with each file's `file_kind` tag, and synced connector sources (Google Drive, GitHub, Outline, MCP resource) under `## Synced sources (N)` with a note to use the matching connector tool to read them
- `project_read` on a document-type upload (PDF, docx) returns extracted text inline or as a local file path; non-document uploads (images, etc.) return empty content with `file_kind` set
- `project_delete` now only removes text docs — attempts to delete file uploads are rejected with "File uploads can be removed from the project in claude.ai" — the method description was updated accordingly
- Error messages updated: "No doc at" → "No doc or file at"; "The project has no docs." → "The project has no docs or files."

Evidence: Updated project tool description (search for `"is a file upload; project_delete only removes text docs"` and `"## Synced sources"`)


### Artifact Tool: How to Read Existing Artifact Content

The Artifact tool description now includes explicit guidance: "**To read an existing artifact's content**: call WebFetch with its URL." Previously there was no documentation on how to read artifact content back into context.

The WebFetch tool description was also updated with a clearer exception note for artifact URLs: `claude.ai/code/artifact/{uuid}` URLs (including `preview.claude.ai`) are fetchable via your claude.ai login — use WebFetch, not curl (curl returns the SPA shell or a Cloudflare 403, not the actual content).

Additionally, `artifactReadVersions` tracking was added to app state so Claude can track which version of an artifact was last read and detect when a locally cached version differs from what's in the session.

Evidence: Artifact tool description update (search for `"**To read an existing artifact's content**"` and `"claude.ai/code/artifact/{uuid} URLs ARE fetchable"`)


### Ripgrep (`rg`) Auto-Permission: More Flags Recognized

The Bash tool's static command analyzer now recognizes additional `rg` flags as safe for auto-approval, expanding what permission rules can match automatically:

- `--smart-case`
- `--case-sensitive`
- `--no-line-number`
- `--multiline`
- `--pcre2`
- `-s` (smart-case short form), `-w` (word-regexp), `-x` (line-regexp), `-F` (fixed-strings), `-n` (line-number), `-N` (no line-number), `-H` (with-filename), `-U` (multiline), `-P` (pcre2)

Previously these flags caused the auto-allow check to fall back to prompting for permission even if a matching permission rule existed.

Evidence: Expanded flag set in rg analyzer (search for `"--smart-case"`)


### sed Safety Analysis: Redirect Injection Detection

The `sed` command permission analysis was substantially improved. The system now:

- Detects "redirect-borne content injection" — cases where a shell redirect could allow an injected argument to be swallowed by `sed`, bypassing static analysis — and requires explicit approval
- Distinguishes clearly between three failure modes: command is over-length or contains chars that bash and the analyzer tokenize differently, command carries redirect-borne content that can't be validated, and command passes static analysis cleanly
- Reports specific failure reasons in `decisionReason` for each case rather than a single generic message

New safe result message: "No redirect-borne sed risk detected"

Evidence: New sed analysis function (search for `"sed command carries redirect-borne content that cannot be statically validated"`)


### rm/rmdir Safety Analysis: Multi-Directory and Glob-Aware

The `rm`/`rmdir` dangerous-removal detector was rewritten (`mZ8` replacing `kd6`) with substantially more coverage:

- Now considers *all* working directories (main cwd plus additional working dirs), not just the single current directory — reports "workspace directory" in the error message instead of "current working directory"
- Detects when a `cd` precedes a `rm` with a relative glob, making the target statically unresolvable
- Detects multi-level glob traversal that can't be statically enumerated
- Detects `rmdir --parents` with a wildcard glob as a separate dangerous case
- Resolves symlinks in paths before checking

Each case now gets a specific, actionable error message instead of one generic response.

Evidence: New rm analysis (search for `"This command would remove a workspace directory"`, `"This command changes directories before the removal"`, `"This command's glob pattern traverses directories that cannot be statically enumerated"`)


### Remote Control: WebSocket Close Code Error Messages

WebSocket close events in Remote Control now produce human-readable error messages organized by close code:

- `4090`: "this connection is no longer the active worker for the session"
- `4091`: "transport init failed"
- `4092`: "connection dropped — no close reason from server"
- `401`: "auth token expired"
- `403`: "server rejected connection"
- `404`: "session not found on server"
- `1002`: "server rejected the connection handshake"
- `4001`: "session expired or not found on server"
- `4003`: "server rejected credentials"

Previously most of these were "Transport closed (code N)" or a bare close code.

Evidence: New close-code mapping (search for `"this connection is no longer the active worker for the session (code 4090)"`)


### First-Party Auth: Improved MCP Connection Error Messages

When an MCP server using first-party auth (your claude.ai login) rejects the connection, the error now distinguishes between HTTP status codes:

- `403`: "missing a scope this server needs — run `/login` and retry, or check that your account has access"
- `401` (or other): "Run `/login` and retry"

The new error code `FIRST_PARTY_AUTH_REJECTED` is logged in telemetry and surfaced in the connection error object, making it programmatically distinguishable from other failure modes like `INVALID_CONFIG` or `AUTH_HEADER_REJECTED`.

Evidence: New `uo7` handler (search for `"FIRST_PARTY_AUTH_REJECTED"`)


### Windows Background Sessions: UNC Path Warning

Background sessions running from Windows network (UNC) paths (e.g., `\\server\share\path`) now emit a warning that these paths are not supported and will be neutralized. This prevents silent failures when background sessions are started from network drives.

Evidence: New warning (search for `"background sessions do not support Windows network (UNC) paths"`)


### Prompt Suggestion Opt-Out: `CLAUDE_CODE_ENABLE_PROMPT_SUGGESTION`

A new environment variable `CLAUDE_CODE_ENABLE_PROMPT_SUGGESTION` can now be used to override the server-sent `promptSuggestionEnabled` flag. Set to `false` to disable prompt suggestions regardless of the server's setting.

Evidence: New env var check (search for `"CLAUDE_CODE_ENABLE_PROMPT_SUGGESTION"`)


### Symlink Resolution in Config Path Loading

Settings file paths (`.claude/settings.json`, `.claude/settings.local.json`) are now run through a full symlink resolver before being watched and read. If your `.claude` directory is a symlink to another location, Claude Code now correctly follows it rather than watching the symlink target ambiguously.

Evidence: `FV$()` realpath function wrapping all settings path construction (search for `"realpathSync"`)


### Daemon Session Roster: Improved Messages

Several daemon management messages were updated to be more informative:

- Roster message for sessions from a different CLI version: now explains "most stay attachable and upgrade automatically once idle — exec runs never respawn" (was a bare "from a different CLI version")
- Stop instruction updated from "`claude daemon stop`" to "`claude daemon stop --any`" for reaping orphaned sessions; running `claude agents` also restarts the daemon and re-adopts still-running sessions
- Daemon control key mismatch errors now give separate messages for "this window didn't present the daemon control key" (stale window across an update) vs "the presented daemon control key doesn't match" (retry and restart daemon)

Evidence: Message updates (search for `"most stay attachable and upgrade automatically once idle"`, `"claude daemon stop --any"`)


### `--` Argument Separator in argv Parsing

The CLI's argument parser now correctly handles `--` as a separator, stopping flag parsing at that point. Anything after `--` is treated as positional arguments rather than flags. This matches standard Unix argument parsing behavior and prevents edge cases where user-provided strings beginning with `-` were treated as flags.

Evidence: `sl$()` function (search for `"process.argv.indexOf(\"--\")"`)


### Agent Summary: Limited to Single Turn

The agent summary generation (used internally when summarizing subagent results) is now capped at `maxTurns: 1`. This prevents the summarizer from taking multiple turns when summarizing a task, keeping it fast and predictable.

Evidence: `maxTurns: 1` added to agent summary call (search for `"querySource: \"agent_summary\""`)


## Bug Fixes

- Pasted content that was lost during session restore now shows a readable placeholder — `[Pasted text #N — content no longer available]` or `[...Truncated text #N — content no longer available...]` — instead of silently disappearing or causing an error. A telemetry event tracks how often this occurs. (search for `"paste_store_content_lost"`)

- Claude in Chrome now defaults to **off**. Users who want Chrome browser tools are prompted at first use with "Yes, use my browser" / "No, keep browser tools off". Previously the auto-enable experiment could leave the integration on by default. (search for `"claudeInChromeDefaultEnabled"`)

- Clipboard copy via tmux now retries using `load-buffer` (without `-w`) when `load-buffer -w` fails, improving compatibility with older tmux versions. (search for `"clipboard: retry tmux load-buffer"`)

- The daemon manager now validates resume session IDs before using them and generates a fresh UUID when the stored ID fails validation. Invalid IDs are logged to `invalid-resume-id.jsonl` for diagnostics. (search for `"invalid-resume-id.jsonl"`)

- The safety classifier error reporting now includes the HTTP status code of classifier failures, allowing `vo4` to produce better-informed error messages when the classifier is unavailable due to a specific HTTP error. (search for `"httpStatus"` in auto-mode classifier handling)

- Background job `exec` mode now emits a telemetry event when the last-line buffer is empty at job completion (indicating the output ring had bytes but no last-line was captured), helping diagnose silent exec job completions. (search for `"tengu_bg_exec_no_lastline"`)


## In Development

Features with infrastructure added but not yet generally enabled.


### Token Count Reminder (`totalTokensReminder`) [In Development]

What: Infrastructure for injecting a token-count reminder block into the system prompt and after each tool result, intended to help the model understand remaining context.

Status: Available via internal `totalTokensReminder` setting; controlled by the `tengu_lapis_anchor` feature flag. Not enabled by default.

Details:
- Setting values: `off` (default), `infinite` (emits `Infinite`), `fixed` (emits 5,000,000), `countdown` (live remaining context-window tokens)
- Can be overridden with `CLAUDE_CODE_TOTAL_TOKENS_REMINDER` environment variable
- Emits `<total_tokens>N tokens left</total_tokens>` blocks in the system prompt and after each tool result

Evidence: Setting description (search for `"Emit a <total_tokens>N tokens left</total_tokens> block in the system prompt"`)


### `claude-in-teams` Entrypoint [In Development]

What: A new `claude-in-teams` deployment mode is being added alongside the existing `remote`, `claude-desktop`, and CLI entrypoints. It routes to the `claude_code_remote` product analytics bucket.

Status: Entrypoint string recognized and has routing logic; no user-visible behavior beyond the entrypoint itself yet.

Evidence: New entrypoint routing (search for `"claude-in-teams"`)


Generated with:
- tool: `harness-investigations@1d6cc84-dirty`
- provider: `claude`
- model: `claude-sonnet-4-6`
- primary diff: `archive/claude-code/changes/changes-v2.1.176-2.md` (filtered astdiff)
- string diff: `archive/claude-code/changes/string-diff-v2.1.176.txt`
