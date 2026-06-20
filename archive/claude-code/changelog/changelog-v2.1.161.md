# Changelog for version 2.1.161

## Summary

Claude Code 2.1.161 is a small, high-similarity release focused on safety checks, remote-session reliability, MCP/plugin polish, and clearer diagnostics. The most important user-visible changes are stricter auto-approval screening for risky shell patterns, better remote-session recovery messages, improved usage-credit guidance for org limits, and clearer handling for teammate/team workflows.


### Stricter Shell Safety Screening

Claude Code now rejects additional risky shell patterns before treating a command as safe. The new checks catch zsh `read` operands that can trigger arithmetic evaluation or command substitution, and jq filters that use `include` or `import`, which can load local jq modules.

Details:
- zsh `read` handling now distinguishes numeric, string, and prompt operands instead of treating all option operands alike.
- Fused `read -p...` forms are inspected for subscripted identifiers and command substitutions.
- jq commands using `include` or `import` are blocked alongside existing checks for `system()` and file-loading flags.

Evidence: Bash safety classifier adds zsh `read -p` and jq module-loading diagnostics (search for `"read -p' fused remainder"` and `"jq command contains include/import"`)


### Remote Session Reliability and Recovery Messages

Remote and thin-client sessions now provide better state recovery and clearer failure messages when reconnecting, sending control requests, or displaying context usage.

Details:
- Reconnects can warn when catch-up was truncated and earlier transcript messages could not be loaded.
- Control requests fail with a user-readable “remote session is not connected” message instead of a generic missing-manager failure.
- `/context` now explicitly tells users when context usage is unavailable over the current remote connection.
- Side questions now explain when the session is read-only or the remote transport does not support them.

Evidence: Remote session catch-up and unsupported-feature diagnostics (search for `"Some earlier messages from this session could not be loaded after reconnecting."`, `"Remote session is not connected"`, `"Context usage isn't available over this remote connection"`, and `"This remote connection doesn't support side questions"`)


### Dynamic Slash-Command Refresh for Stream Clients

Stream-json clients can now receive a full replacement slash-command list when commands change mid-session, such as when skills are discovered after changing directories.

Usage:
```bash
claude --output-format stream-json
```

Details:
- A new `commands_changed` system event carries the updated command list.
- The schema text tells clients to replace their cached command list rather than refetching the stale initialize-time list.

Evidence: Stream protocol emits updated command lists (search for `"commands_changed"` and `"Fire-and-forget push of the full slash-command list after a mid-session change"`)


### Pending Permission Requests on Session Initialization

Remote/session clients can now learn about permission prompts that were already waiting when they joined or initialized a session.

Details:
- The initialize response can include `pending_permission_requests`.
- This helps clients render in-flight approval prompts instead of missing prompts created before reconnect or attach.

Evidence: Initialize response schema includes in-flight prompts (search for `"Permission requests still awaiting a response"`)


### Better Usage-Credit Guidance for Organizations

Usage-credit messaging now handles organization spend-cap states more explicitly and points team/enterprise users to the appropriate organization usage page.

Details:
- `org_spend_cap_reached` is treated as a usage-credit limit state.
- Team and enterprise users can be directed to manage usage credits for their organization instead of falling into a personal login flow.

Evidence: Usage-credit org spend-cap handling (search for `"org_spend_cap_reached"` and `"manage usage credits for your organization"`)


### Clearer MCP Connector and Channel UI

The MCP/connector UI has been polished to reduce confusion around hidden or inactive connectors and inbound channel messages.

Details:
- The connector UI can fold inactive entries under “Show unused connectors.”
- Channel warnings now say that experimental channel messages inject directly into the current session and explain how to stop them by restarting without the channel option.

Evidence: MCP connector/channel UI strings (search for `"Show unused connectors"` and `"Channels (experimental) messages from"`)


### Linux Clipboard Copy Updates the Primary Selection

On Linux, clipboard writes now also update the primary selection where supported.

Details:
- `wl-copy` is called for both the regular clipboard and `--primary`.
- `xclip` writes both `clipboard` and `primary`.
- `xsel` writes both `--clipboard` and `--primary`.

Evidence: Linux clipboard handling writes primary selections (search for `"wl-copy\", [\"--primary\""`, `"xclip\", [\"-selection\", \"primary\""`, and `"xsel\", [\"--primary\", \"--input\""`)


### Clearer Temporary Directory Override Diagnostics

Claude Code now warns when `CLAUDE_CODE_TMPDIR` produces a per-user temp path too long for Unix-domain sockets, causing child processes to fall back to a shorter temp path.

Details:
- The warning explains that the override still affects Claude Code’s per-uid temp directory but child-process `$TMPDIR` falls back because of AF_UNIX socket path limits.
- It recommends shortening `CLAUDE_CODE_TMPDIR` to roughly 30 bytes or less when child processes must use the override.

Evidence: Temp-dir override warning (search for `"CLAUDE_CODE_TMPDIR makes the per-uid temp dir"`)


### Terminal Glyph Troubleshooting Tip

Claude Code can now show a targeted tip for corrupted terminal glyphs, especially in VS Code terminal GPU acceleration scenarios.

Usage:
```bash
/terminal-setup
```

Details:
- The tip suggests disabling terminal GPU acceleration or running `/terminal-setup`.
- It is gated by the tip relevance logic rather than shown universally.

Evidence: New terminal troubleshooting tip (search for `"Corrupted terminal glyphs? Disable terminal GPU acceleration in settings or run /terminal-setup"`)


### Team and Teammate Terminology Cleanup

Several multi-agent workflow strings now use “team” and “teammate” consistently instead of mixing in older “swarm” wording.

Details:
- Team creation and cleanup copy now says “multi-agent team.”
- Notifications now say “teammate started” and “teammate shut down.”
- The hidden team-name option description now says “Team name for teammate coordination.”
- Coordinator sessions now direct users to `/branch` when forking is unavailable.

Evidence: Team wording changes (search for `"create a multi-agent team"`, `"1 teammate started"`, `"Team name for teammate coordination"`, and `"Forking is not available in coordinator sessions. Use /branch instead."`)


## Bug Fixes

- Fixed path handling for write-style tool diffs so paths that require special handling are read before constructing replacement previews. Evidence: write/edit diff preview path check changed to include special paths (search for `"file_path"` near the write-tool preview logic and `"JV(f.file_path)"`)

- Fixed plugin marketplace/setup notifications so failed marketplace install or config-save states are tracked as setup issues instead of relying only on transient notification text. Evidence: marketplace setup issue tracking (search for `"marketplaceIssueCount"` and `"Anthropic marketplace installed"`)

- Fixed remote side-question handling so unsupported remote/read-only cases produce explicit messages instead of attempting the side-question request. Evidence: side-question remote precondition messages (search for `"Side questions aren't available when viewing a session read-only"`)


## In Development

Features with infrastructure added but not yet enabled. These are shipped "dark" and may become available in future versions.


### MCP-Sourced Skills [In Development]

What: Claude Code is adding infrastructure for MCP servers to publish skills that appear as slash-command-style prompts.

Status: Feature-flagged

Details:
- The feature is gated by `tengu_mcp_skills`, which defaults to false.
- MCP servers can expose a `skill://index.json` resource describing concrete skill markdown resources and URI-template-backed skill resources.
- MCP-sourced skills are loaded as user-invocable prompt commands with server-qualified names.
- Security restrictions are explicit: MCP-sourced skill frontmatter cannot register hooks or bypass permissions through `allowed-tools`.

Evidence: MCP skill discovery is gated and reads `skill://index.json` (search for `"tengu_mcp_skills"`, `"skill://index.json"`, `"declared hooks in frontmatter"`, and `"declared allowed-tools in frontmatter"`)


Generated with:
- tool: `harness-investigations@1d6cc84-dirty`
- provider: `codex`
- model: `gpt-5.5`
- reasoning effort: `medium`
- primary diff: `archive/claude-code/changes/changes-v2.1.161.md` (filtered astdiff)
- string diff: `archive/claude-code/changes/string-diff-v2.1.161.txt`
