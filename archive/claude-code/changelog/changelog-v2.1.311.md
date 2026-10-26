# Changelog for version 2.1.311

## Summary

Version 2.1.311 adds permission-rule diagnostics to `/doctor`, supports verifying organization-delivered plugins by digest, and gives self-hosted runners a way to keep idle sessions attached while background processes remain alive. It also tightens several permission and authentication checks. Code for automatic subagent recovery, effort shortcuts, and a built-in Claude Platform documentation connector is present behind disabled gates.

## New Features


### Permission Rule Diagnostics

`/doctor` now includes a `Permission rules that may not work as written` section. It identifies rules that name unknown tools, use field-prefixed content that will never match, or contain other questionable permission syntax.

```text
/doctor
```

The diagnostics suggest the appropriate tool matcher where possible. They report problems without rewriting your rules.


### Verified Organization Plugins

Administrators can now identify approved plugin releases through `extraKnownMarketplaces.<marketplace>.pluginDigests` in managed settings. This lets an organization deliver a plugin from a remote source and have its hooks run in the configured organization tier after Claude Code verifies the installed files.

The plugin must also be enabled through managed settings and listed in `prependPlugins` or `appendPlugins`.

- Digests use `sha256-` followed by a base64 SHA-256 value calculated over the plugin’s files.
- Verification covers the complete bundled plugin, including `node_modules`.
- Modified files, converted line endings, symbolic links, or a mismatched digest prevent the copy from qualifying.
- See Notes if an existing managed plugin stops loading its hooks.


### Keep Self-Hosted Sessions Attached for Background Processes

Self-hosted runners gain `--hold-idle-file` and `--max-hold-min`. A host can keep a marker file fresh while a process left running by the session—such as a server in `tmux`—is alive, preventing ordinary idle release from detaching the session.

Add these options to an existing runner invocation:

```bash
claude self-hosted-runner \
  --release-idle-session-min 15 \
  --hold-idle-file /run/claude/background-alive \
  --max-hold-min 120
```

The host must maintain the marker; Claude Code checks that it is a regular local file modified within the last three minutes and checks again every 30 seconds.

- `--max-hold-min` defaults to 1,440 minutes; `0` disables the hold.
- Environment equivalents are `SELF_HOSTED_RUNNER_HOLD_IDLE_FILE` and `SELF_HOSTED_RUNNER_MAX_HOLD_MS`.
- The hold does not override startup timeouts, retirement deadlines, shutdown ceilings, or `--kill-session-after-min`.

## In Development


### Automatic Subagent Recovery After a Restart

A new recovery path can resume eligible subagents from their saved transcripts after a cloud worker or container restart, then deliver their results through normal notifications. It checks current permissions, plugin launch decisions, saved agent settings, and restart counts before continuing work.

This path requires both `tengu_iterative_haven` and `tengu_steady_puppy`, which default to off. Eligibility is limited to unfinished, top-level agents launched with defaults; worktree-isolated agents and agents explicitly stopped by the user are excluded. The new automatic-recovery messages therefore do not mean every interrupted agent will resume in ordinary sessions.


### Keyboard Shortcuts for Effort

Interactive handlers can now step effort up or down through the `chat:increaseEffort` and `chat:decreaseEffort` keybindings. They respect model support and organization caps, and stop below `max`; reaching maximum effort still requires an explicit choice such as:

```text
/effort max
```

The feature is behind `tengu_velvety_kay`, off by default.


### Claude Platform Documentation Connector

A bundled `cc-plugin-claude-platform` plugin connects `/claude-api` assistance to the developer documentation MCP endpoint at `https://platform.claude.com/docs/mcp`. When available, Claude can search and read platform documentation while working on API integrations.

Registration and connection checks are implemented, but availability requires `tengu_peppy_crescent`, off by default, plus additional account and environment checks.


### Reconnect Failed MCP Servers Through Tool Search

Tool search can attempt to reconnect an eligible failed server when the search query includes that server’s name. This is intended to help when an app or local service starts after Claude Code.

The reconnect path is behind `tengu_floating_lagoon`, off by default. It currently targets selected HTTP and SSE connections without OAuth, with retry limits and a cooldown.


### Save Task Results Into a Hosted Container

The existing `save_task_files` capability is being extended to save task-produced files into a hosted chat’s container, where subsequent shell commands and file tools can use them.

The extension requires `tengu_abundant_squid` as well as the existing `tengu_serene_frog` gate; both default to off. It asks for approval on every save, supports up to 20 files per call, limits individual files to 500 MiB, and adds numbered filenames instead of overwriting existing files.

## Other Changes

- Changed Bash permission checks to reject or request approval for more commands whose variable assignments, redirects, loops, or arithmetic cannot be verified consistently across Bash and zsh.
- Changed tool execution to refuse calls when the working directory’s path changes after its permission check; the command must be checked again.
- Changed organization-plugin classification so enabling a plugin alone does not establish trusted provenance for its hooks.
- Changed Claude in Chrome to refuse certain `browser_batch` calls when session permission rules require actions to be checked individually.
- Changed `/code-review` guidance to reserve `max` and `ultra` reviews for explicit requests from the user or their instructions.
- Added `CLAUDE_CODE_EVEN_MORE_DANGEROUSLY_SKIP_PERMISSIONS` to waive dangerous-removal prompts in bypass mode when permission rules, hooks, and managed-policy checks permit it; startup reports whether it takes effect.
- Added `CLAUDE_CODE_DISABLE_WORKING_SYNC_WATCH` to disable the Linux working-file synchronization watcher.
- Added mod support for decorating prompt text without changing the draft, caret, or undo history, and for specifying pane background colors.
- Improved MCP errors for oversized, deeply nested, or otherwise unreadable structured responses to explain that the tool may already have run.
- Improved validation of MCP tool listings supplied at startup, refusing calls when the connected server’s tool definition or handshake no longer matches.
- Improved background memory saving with tracked, cancellable `saving memories` tasks.
- Improved plugin MCP and LSP configuration errors to explain when required environment variables are withheld from organization-managed launches.
- Fixed file discovery omitting files explicitly re-included by `.ignore`.
- Fixed agent worktree cleanup releasing or removing worktrees still used by live tasks or being handed off through `/background`.
- Fixed MCP `Clear authentication` reconnecting before stored credentials for the relevant configurations were confirmed cleared.
- Fixed reactive compaction accepting a response without its expected summary without first attempting another summary request.
- Fixed oversized hook replacement results being passed onward; Claude now receives the original tool result with an explanation.
- Fixed Windows sandbox setup guidance failing to distinguish an installed sandbox from one disabled by settings or managed policy.

## Notes

Organization-managed plugins loaded from a cache, archive, or seed directory may now run in the user tier—or fail to load where only managed hooks are allowed—unless their provenance qualifies. Administrators should declare a local marketplace source in managed settings, or configure approved `pluginDigests` and list the plugin in `prependPlugins` or `appendPlugins`. Ship digest-verified plugins with dependencies already bundled.

If a command is refused because its working directory changed after approval, inspect the current directory and reissue the command for a fresh permission check. Use `/doctor` to find permission rules that cannot match as written.


Generated by `harness-investigations@5a47f65-dirty` using codex `gpt-6.1-sol` (medium effort)
Inputs: astdiff, strings, module sources
