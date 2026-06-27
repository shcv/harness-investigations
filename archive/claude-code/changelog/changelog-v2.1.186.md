# Changelog for version 2.1.186

## Summary

This release delivers a major expansion of MCP authentication — two new CLI commands let you authenticate and sign out of MCP servers directly — alongside a new `ReadMcpResourceDirTool` for browsing MCP directory resources. The agent proxy gains Bazel JVM truststore support and authenticated proxy credentials, making it more viable in enterprise Java build environments. Several quality-of-life improvements round out the release: iTerm2 is now a first-class teammate mode, stream reconnection after laptop suspend is more reliable, and the `deniedDomains` network policy now accepts a bare `"*"` to deny all external hosts.


## New Features


### `claude mcp login` and `claude mcp logout` commands

Two new `mcp` subcommands handle OAuth authentication and credential management for MCP servers.

Usage:
```bash
# Authenticate with an HTTP or SSE server
claude mcp login myserver

# Authenticate headlessly (SSH, no browser available)
claude mcp login myserver --no-browser

# Clear stored credentials
claude mcp logout myserver
```

Details:
- Works with HTTP servers, SSE servers, and claude.ai connectors
- `--no-browser` prints the authorization URL instead of opening a browser; paste the redirect URL back when prompted
- After authenticating a claude.ai connector, the connector becomes available on the next Claude Code launch
- `mcp logout` clears the stored OAuth token but does not affect API-key–authenticated servers or stdio servers (those have no stored credentials to clear)
- Descriptive error messages indicate what kind of authentication each server uses and what to do when auth is unavailable

Evidence: `"Authenticate with an MCP server (HTTP, SSE, or claude.ai connector)"`, `"Clear stored OAuth credentials for an MCP server"`, `"Print the authorization URL instead of opening a browser"` (search for these strings)


### ReadMcpResourceDirTool — list MCP directory resources

A new built-in tool (`ReadMcpResourceDirTool`, alias `ReadMcpResourceDir`) lists the direct children of a directory resource on an MCP server using the `resources/directory/read` protocol extension.

Details:
- Accepts `server` (MCP server name) and `uri` (directory resource URI)
- Only works against servers that declare directory listing support; other servers return a clear error
- Subdirectories are identified by `mimeType` in the result; traverse them by calling the tool again on a child `uri`
- The tool alias map is updated so `ReadMcpResourceDir` routes to `ReadMcpResourceDirTool`

Evidence: `"List the direct children of a directory resource on an MCP server"`, `"ReadMcpResourceDirTool"`, `"ReadMcpResourceDir"` (search for these strings)


### iTerm2 teammate mode

`teammateMode: "iterm2"` is now a supported value for the `teammateMode` settings key, in addition to `"tmux"`, `"in-process"`, and `"auto"`.

Usage:
```json
// settings.json
{ "teammateMode": "iterm2" }
```

Details:
- Requires the `it2` CLI tool (`pip install it2`) and the iTerm2 Python API enabled under Preferences > General > Magic > Enable Python API
- When `teammateMode` is `"iterm2"`, Claude Code opens teammate panes as iTerm2 split panes
- If the `it2` binary is not on PATH or the Python API is not enabled, a descriptive error is shown and the pane falls back to in-process mode
- You can also force this mode with `[BackendRegistry] Selected: iterm2 (explicit teammateMode)` being logged

Evidence: `"How spawned teammates execute (tmux, iterm2, in-process, auto)"`, `"teammateMode is set to \"iterm2\" but the it2 CLI is not reachable"` (search for these strings)


### AWS credentials refresh in the third-party platform setup

The "Using 3rd-party platforms" login screen now offers a "Claude Platform on AWS · refresh credentials" option when an active AWS session is detected.

Details:
- Selecting this option runs the configured `awsAuthRefresh` command in the background and shows a spinner
- On success, the screen shows "AWS credentials refreshed." and prompts to continue
- On failure, a descriptive error suggests checking the command in your settings and testing it in a separate terminal
- This provides a quick path to refresh expiring Bedrock credentials from within the Claude Code auth flow

Evidence: `"Running awsAuthRefresh…"`, `"AWS credentials refreshed."`, `"awsAuthRefresh failed. Check the command in your settings"` (search for these strings)


### Agent proxy: JVM truststore, Bazel, and authenticated proxy credentials

The CCR agent proxy now provisions trust for a significantly wider set of tools:

- **JVM truststore**: A PKCS12 truststore (`java-truststore.p12`, password `"changeit"`) is built and injected via `JAVA_TOOL_OPTIONS` so Java-based tools trust the proxy's CA
- **Bazel**: A Bazel system bazelrc block is written to configure `--host_jvm_args` with the truststore, since Bazel's embedded JDK ignores `JAVA_TOOL_OPTIONS`
- **NSS/browser trust**: The `certutil` tool is used to add the proxy CA to NSS databases (for Chromium-based browsers); falls back gracefully when `certutil` is absent
- **Boto/gsutil trust**: A `[Boto]` config section (`ca_certificates_file`) is written for gsutil
- **Authenticated proxy credentials**: When the upstream requires authentication, `CLOUDSDK_PROXY_USERNAME`, `CLOUDSDK_PROXY_PASSWORD`, `GIT_CONFIG_PARAMETERS='http.proxyAuthMethod=basic'`, and SOCKS credential prefixes (`srt:password@`) are set in the sandbox environment

Evidence: `"[agent-proxy] JVM truststore built at"`, `"[agent-proxy] wrote Bazel trust block to"`, `"[agent-proxy] MITM CA added to NSS DB at"`, `"CLOUDSDK_PROXY_USERNAME=srt"`, `"GIT_CONFIG_PARAMETERS='http.proxyAuthMethod=basic'"` (search for these strings)


### `respondToBashCommands` setting

A new boolean setting controls whether Claude responds after a `!`-prefixed bash command typed in the input box.

Usage:
```json
// settings.json
{ "respondToBashCommands": false }
```

Details:
- Default is `true` (Claude responds as before)
- Set to `false` to inject the command's output into context silently, without triggering a response — useful for scripting or context enrichment workflows

Evidence: `"Whether Claude responds after an input-box ! bash command runs. Set to false to add the command output to context without a response. Default: true."` (search for this string)


### VS Code 1.123/1.124 clipboard encoding warning

When pasting content that contains non-ASCII characters (e.g. Hebrew, emoji, accented letters) into Claude Code while running inside VS Code 1.123 or 1.124, a warning is now shown:

> VS Code 1.123/1.124 will mojibake this paste — update to ≥1.125

Details:
- The check is applied to clipboard content before it is passed to the OSC 52 paste path
- VS Code 1.125+ fixes the underlying bug; no warning is shown there

Evidence: `"VS Code 1.123/1.124 will mojibake this paste — update to ≥1.125"` (search for this string)


### `CLAUDE_CODE_FORCE_STRIKETHROUGH` and expanded strikethrough detection

Strikethrough text rendering now detects many more terminal emulators, and can be overridden unconditionally.

Details:
- New environment variable `CLAUDE_CODE_FORCE_STRIKETHROUGH`: set to any value to force strikethrough rendering regardless of terminal detection
- Auto-detection now recognizes: Ghostty, Mintty, JetBrains IDE Terminal, iTerm2, kitty, alacritty, foot, Konsole, Windows Terminal (`WT_SESSION`), Zed (`ZED_TERM`), and VTE ≥ 4400
- Apple Terminal and the Linux `linux` console remain excluded

Evidence: `"CLAUDE_CODE_FORCE_STRIKETHROUGH"` (search for this string)


### PowerShell single-quoted string safety check

Claude Code's PowerShell command builder now rejects Unicode "smart quote" characters (U+2018–U+201F) in single-quoted string values, because PowerShell's tokenizer treats them as quote delimiters and produces silently broken commands.

Details:
- Throws a descriptive error that includes the offending code point: "Cannot safely quote value in a PowerShell single-quoted string literal: it contains U+201C…"
- Logged with key `"psSingleQuotedLiteral: rejected a PowerShell quote-variant codepoint"`
- Affects any PowerShell command that passes user-supplied strings through the builder (e.g. clipboard operations, `Set-Location`)

Evidence: `"psSingleQuotedLiteral: rejected a PowerShell quote-variant codepoint (U+2018..U+201F)"` (search for this string)


### Code review respects `linguist-generated` git attribute

When reviewing files in `/code-review` or `/review`, Claude Code now checks `git check-attr linguist-generated` on each file and skips files marked as generated.

Details:
- Runs `git check-attr linguist-generated -- <path>` with a 5 s timeout
- If the attribute is `set` or `true`, the file is treated as generated and excluded from review scope
- Consistent with how GitHub's Linguist and many code-review tools handle generated files
- Results are cached per path to avoid repeated git calls

Evidence: `"linguist-generated"`, `"check-attr"` (search for these strings)


## Improvements


### `deniedDomains` accepts `"*"` for deny-all; new `strictAllowlist` option

The network policy schema for the agent proxy sandbox gains two additions:

1. `deniedDomains` now accepts a bare `"*"` entry to deny all outbound HTTP/HTTPS traffic not explicitly allowed. Previously only specific hostnames were accepted.
2. New `strictAllowlist` boolean field: when `true`, hosts not in `allowedDomains` are denied without calling the `ask` callback — enforcing the allowlist as a hard policy rather than a prompt-suppression hint.

Evidence: `'List of denied domains. Unlike allowedDomains, a bare "*" is accepted here (deny-all).'`, `"If true, hosts not in allowedDomains are denied without consulting the ask callback."` (search for these strings)


### Stream suspend detection: abort and reconnect instead of re-arming

When the stream watchdog detects that the system suspended (e.g. laptop lid close) during an active API stream, Claude Code now aborts the request and opens a fresh connection. Previously it re-armed the watchdog and continued on the existing connection, which often failed silently.

The change is surfaced as a new error class (`StreamSuspendedError`) and a cleaner log message:

> Stream watchdog detected system suspend; aborting to retry on a fresh connection

Evidence: `"Stream watchdog detected system suspend; aborting to retry on a fresh connection"`, `"StreamSuspendedError"` (search for these strings)


### Artifact tool: clear validation error for inline `content`/`title`

When Claude mistakenly calls the Artifact tool with an inline `content` or `title` field instead of a `file_path`, a helpful steering message is now returned immediately:

> The Artifact tool reads from a file on disk — it does not take inline `content` or `title`. Write the page to an .html or .md file first (Write/Edit), then call Artifact with `file_path` pointing at it.

An additional check rejects `label` values longer than 60 characters with a clear message to put the content in the page body instead.

Evidence: `"The Artifact tool reads from a file on disk — it does not take inline \`content\` or \`title\`."`, `"\`label\` is a short version name (max 60 chars)."` (search for these strings)


### `/review` command description updated

The `/review` command description changed from "Review a pull request" to "Review a GitHub pull request; for your working diff use /code-review", making it clear that `/review` targets GitHub PRs and `/code-review` is for local working-tree diffs.

Evidence: `"Review a GitHub pull request; for your working diff use /code-review"` (search for this string)


### Security classifier now sees removed code in Edit operations

The auto-mode security classifier prompt now includes an `EDIT REMOVALS` annotation section that surfaces the `removes` (replaced text) and `adds` from Edit tool calls, instructing the classifier to judge deletions as seriously as additions — removing a safety check or guard is a behavioral change even when the added replacement looks innocuous.

When `removesTruncated: true` is set, the classifier is told to treat the removal as at least as significant as the visible portion.

Evidence: `"EDIT REMOVALS: Edit calls show both \`removes\` (the replaced text) and \`adds\`."`, `"\`removesTruncated: true\` means the removed text was longer than shown"` (search for these strings)


### Worktree cleanup: reparse point handling (Windows)

Worktree teardown on Windows now handles reparse points (symlinks and junctions) in configured paths:

- Paths outside the worktree that are reparse points are skipped with a log message
- Configured reparse points inside the worktree are unlinked before the directory tree is removed, preventing failures from dangling junction targets

Evidence: `"[worktree] skipping configured reparse point outside worktree:"`, `"[worktree] unlinked configured reparse point before removal:"` (search for these strings)


### Fable 5 branding consistency

Several usage-credits strings that referred to "Fable" now say "Fable 5" throughout the UI. Affected messages include the model-switch prompt, the "out of credits" notice, and the plan inclusion notice.

Evidence: `"Buy more to keep using Fable 5, or switch models to keep working."` (search for this string; the removed version used "Fable" without "5")


### Usage credits: organization-level cap messages

New error messages for enterprise scenarios where the whole organization has hit a usage credit cap:

- "Your organization is out of usage credits. Contact your admin to add more."
- "Your organization's usage credit cap is reached for this period. Contact your admin to raise it."
- "You've hit your monthly limit — raise it below, or it resets next month."

Evidence: `"Your organization is out of usage credits. Contact your admin to add more."` (search for this string)


## In Development

Features with infrastructure added but not yet fully enabled. These are gated or behind feature flags and may become generally available in future versions.


### Per-model weekly usage display [Gradual Rollout]

What: The usage overlay can now show per-model weekly utilization alongside the monthly total, with titles like "Current week (claude-opus-4-5)".

Status: Feature-flagged — controlled by `tengu_usage_overage_included_models` (server-side list of model display names to show weekly breakdowns for). Returns an empty list by default.

Details:
- The feature flag value is a list of model display names; when non-empty, the usage API response is filtered for `kind: "weekly_scoped"` entries matching those model names
- Each matching entry produces a titled row with current-week utilization and reset time

Evidence: `"Current week ("` in usage display — gated by `"tengu_usage_overage_included_models"` (search for these strings)


Generated with:
- tool: `harness-investigations@0c752ef-dirty`
- provider: `claude`
- model: `claude-sonnet-4-6`
- primary diff: `archive/claude-code/changes/changes-v2.1.186.md` (filtered astdiff)
- string diff: `archive/claude-code/changes/string-diff-v2.1.186.txt`
