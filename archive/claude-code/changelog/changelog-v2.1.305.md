# Changelog for version 2.1.305

## Summary

Version 2.1.305 fixes the 2.1.304 regression that broke requests when providers or gateways rejected tool search, adds actionable `/usage` recommendations, and introduces plugin directory validation. Code changes also reveal an organization default for usage attribution and gated work on connector uploads and cloud shell commands beyond the published notes. Administrators should review the MCP allowlist change, and Linux users should understand the reduced protection before enabling nested user namespaces.

## New Features


### Actionable usage recommendations

`/usage` now turns warnings into concise recommendations that name the responsible agent, skill, plugin, MCP server, or usage pattern. Press `f` to send the suggested fixes to Claude; configuration changes are requested with a preview before editing.

Recommendations include lowering effort, choosing cheaper subagent models, trimming always-loaded context, and disabling unused integrations. The same recommendations appear in `/doctor`, and rows now wrap in narrow terminals.

- Estimates cover sessions on the current machine; usage shares can overlap.
- Applying fixes from `/usage` is unavailable while Remote Control is active.


### Plugin directory validation

Plugin authors can check a plugin against additional submission requirements before publishing it:

```bash
claude plugin validate ./my-plugin --profile directory
```

The directory profile checks listing metadata and files such as the README, license, icon, privacy policy, MCP configuration, and hooks. It also explains which checks could not be completed.

```bash
claude plugin validate ./my-plugin --profile directory --strict --json
```

- `--profile directory` exits unsuccessfully for detected directory rejection conditions or checks it cannot decide.
- `--strict` also treats directory warnings as failures.
- Checks inspect at most 16 declared MCP files and 16 declared hooks files; exceeding those limits fails the directory profile.
- Passing this command does not guarantee acceptance: the directory also performs a safety scan and policy review.


### Organization default for usage attribution

Administrators can set `attributionProjectPolicy.default` in managed settings to provide a fallback claude.ai Project for organization usage reports:

```json
{
  "attributionProjectPolicy": {
    "default": "12345678-1234-1234-1234-123456789abc"
  }
}
```

An explicit `CLAUDE_CODE_ATTRIBUTION_PROJECT` or `attributionProject` selection takes precedence. The default accepts a Project UUID or `claude_proj_` ID and is ignored outside managed settings.

Attribution still requires a claude.ai login, a direct Anthropic API connection, and attribution headers to be enabled; it is not sent from cloud sessions.


### Nested user namespaces for Linux sandboxed commands

The new `sandbox.allowNestedUserNamespaces` setting lets tools create their own user namespaces inside the Linux or WSL sandbox. This supports Chromium and Electron sandboxes, rootless Podman or Buildah, nested Bubblewrap, and `unshare`.

```json
{
  "sandbox": {
    "allowNestedUserNamespaces": true
  }
}
```

The setting defaults to `false`. Enabling it removes significant filesystem protection: a hostile command can bypass read and write restrictions in writable locations, including protection for settings and Git hooks, and plant code that later executes outside the sandbox.

Only user, managed/policy, or CLI `--settings` sources can enable it. Project settings cannot enable it, although a project-level `false` still applies.


### Early usage-limit rechecks for unattended retries

Unattended retry mode can now periodically check whether a usage limit has been lifted before its advertised reset:

```bash
CLAUDE_CODE_RETRY_WATCHDOG=1 \
CLAUDE_CODE_RETRY_WATCHDOG_USAGE_LIMIT_RECHECK_MS=300000 \
claude -p "Continue the maintenance task"
```

`CLAUDE_CODE_RETRY_WATCHDOG_USAGE_LIMIT_RECHECK_MS` accepts values from 60,000 to 10,800,000 milliseconds. Leaving it unset disables these periodic early checks; setting it allows eligible requests to resume sooner when usage becomes available.

## In Development


### Upload local files through the Google Drive connector

A new upload path lets Claude reference a readable local file instead of generating its base64 content in the conversation. After approval, Claude Code reads the file and supplies its contents to the Google Drive connector’s `create_file` tool.

The implementation includes SHA-256 verification, permission checks, checks for changes before sending, and a 10 MB limit. It is behind `tengu_wobbly_dewdrop`, which defaults to `false`, and the `allow_drive_file_references` organization policy.


### Cloud shell commands that share the conversation’s working directory

Behind `tengu_cloud_session_shell`, user-entered shell commands from a supported cloud client can run as conversation turns through the Bash tool. Claude sees the command and output, and directory changes carry over to subsequent shell commands and Claude’s Bash calls.

The gate defaults to `false`. The implementation rejects stale commands, mismatched working directories, hidden control characters, and oversized input. It does not enable `!` commands for Remote Control sessions.


### Expanded Windows sandbox setup

The existing experimental Windows sandbox gains profile read grants and configurable localhost access. Setup can make the user profile readable while excluding credential stores, allowing installed tools and package-manager configuration to work inside the sandbox.

Windows support remains gated by `tengu_nankeen_kestrel`, off by default, with the existing `CLAUDE_CODE_NANKEEN_KESTREL` override.

- Installation requires elevation and now reports incomplete profile grants and exclusions that could not be protected.
- Enabling `sandbox.network.allowLocalBinding` permits connections to local services as well as starting servers; changing this mode requires sandbox setup again.
- Profile access uses a machine-wide sandbox account, so other users’ sandboxed commands may also read granted profile files.

## Other Changes

- Changed `allowedMcpServers` so `${VAR}` references only in a `managed-mcp.json` stdio server’s `env` no longer require an allowlist match; use `deniedMcpServers` to keep such a server blocked.
- Changed Desktop-mounted path plugins to lose their `allowed-tools` grants when managed settings enable `allowManagedPermissionRulesOnly`.
- Changed screen reader settings so project and local settings cannot enable the mode; use your own settings, `CLAUDE_AX_SCREEN_READER`, or `--ax-screen-reader`.
- Changed `/artifacts` deletion confirmation to use `1` or Enter to keep, `2` to delete, and Esc to cancel; `y` and `n` no longer answer it.
- Changed docked mod panes to occupy at most 45% of terminal width, including widths retained after resizing.
- Improved startup presentation by sending diagnostic warnings to the debug log and showing ineffective permission rules as warning rows beneath the banner.
- Improved MCP consent dialogs to reduce accidental acceptance from an Enter intended for the prompt.
- Improved built-in plugin MCP consent so hooks cannot substitute an acceptance for a person’s answer; sessions unable to ask a person cancel those questions.
- Improved mod `Image` rendering in iTerm2 3.5 and later under fullscreen rendering, where supported images previously showed only their `alt` text.
- Improved Remote Control spawn-mode messages to explain that `w` saves the mode for the current folder and identify saved modes on subsequent starts.
- Improved `/login` failures with clearer guidance when the browser callback listener cannot start or input ends before a code is pasted.
- Fixed requests failing on Vertex, Bedrock, and other providers or gateways that reject tool search, including when `ToolSearch` is disallowed or omitted from `--tools`, by retrying without it.
- Fixed `/effort` and `/autocompact` settings failing to apply when model names differ from `modelOverrides` values by letter case or a `[1m]` suffix.
- Fixed new worktrees in bare repositories sometimes starting from local HEAD instead of the default branch, and unchanged subagent worktrees sometimes remaining behind.
- Fixed full-disk Bash failures to report that the disk is full and the command did not run, instead of exposing a raw `ENOSPC` path.
- Fixed cloud-provided or dynamically supplied MCP servers being replaced later by same-named servers from local settings.
- Fixed subagent results identifying the original model after switching to a fallback model.
- Fixed cloud sessions and teammates failing to tell Claude when compaction omitted the oldest messages from its summary.
- Fixed more unattended scheduled cloud sessions waiting five minutes per subagent for WebFetch URL approvals nobody could answer.
- Fixed workflow resume rerunning completed `pipeline()` and `parallel()` agents instead of restoring their results from the journal.
- Fixed Remote Control leaving empty `(session)` entries in `/resume` after switching conversations.
- Fixed screen reader search boxes to say `Search:` and highlighted prompt text to preserve words without inserting spaces.
- Fixed self-hosted runner start scripts failing with `Resource temporarily unavailable` when `TERM` is set and only stdout is shared with the runner or orchestrator.
- Fixed self-hosted runner repository access when Git credential helpers or askpass programs read configuration through `GIT_CONFIG`.
- Fixed spawn-runner hooks being reported as timed out when a background runner kept their output streams open.

## Notes

If you relied on `allowedMcpServers` to exclude a managed stdio server whose only variable substitutions are in `env`, add that server to `deniedMcpServers` before upgrading.

Move any project-level screen reader preference to your user settings, or launch with:

```bash
claude --ax-screen-reader
```

Update instructions or automation that answer `/artifacts` deletion prompts with `y` or `n`; deletion now requires `2`.

Keep `sandbox.allowNestedUserNamespaces` disabled when filesystem isolation is required. Enabling it can also make the machine ineligible to serve device tools that require a strict sandbox.


Generated by `harness-investigations@6d793ff-dirty` using codex `gpt-6.1-sol` (medium effort)
Inputs: astdiff, strings, module sources, release notes
