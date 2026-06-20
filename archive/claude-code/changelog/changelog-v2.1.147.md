# Changelog for version 2.1.147

## Summary
Claude Code 2.1.147 adds new plugin configuration paths, including `claude plugin install --config` for headless setup and `/plugin configure` / “Configure options” for interactive plugin `userConfig`. It also expands memory infrastructure with feature-flagged personal memory sync and knowledge-index recall, and replaces the built-in code-review skill with a correctness-focused review workflow.

### Plugin Configuration from CLI and `/plugin`

What: Plugins with `userConfig` can now be configured during install or from the plugin manager.

Usage:
```bash
claude plugin install <plugin> --config apiKey=... --config enabled=true
```

Details:
- `--config <key=value>` is repeatable on `claude plugin install`.
- Values are validated against the plugin manifest’s `userConfig` schema.
- Number and boolean options are parsed and rejected with clear validation errors.
- If required options remain unset, Claude Code tells users to run `/plugin configure <plugin>` or pass `--config KEY=VALUE`.
- The interactive plugin UI now exposes “Configure options” for plugins that declare `userConfig`.

Evidence: CLI install option and validation (search for `"--config <key=value>"`, `"Set a userConfig option declared in the plugin's manifest"`, and `"isn't declared in this plugin's userConfig"`); interactive command entry (search for `"/plugin configure <plugin> - Set userConfig options"`).


### Personal Memory Sync [Gradual Rollout]

What: Claude Code now includes infrastructure to sync personal memory files to the user’s account, separate from team memory.

Usage:
```bash
# Automatic when enabled for the account/session
claude
```

Details:
- This is gated by the `tengu_marble_lark` feature flag, so not every user will see it yet.
- The new sync path uses `/api/claude_code/memory?scope=user&repo=...`.
- The watcher can sync both `team` and `user` memory scopes.
- Personal memory sync excludes reserved subtrees such as `team`, `logs`, `sessions`, and `proposals`.
- Secret scanning now blocks writes to personal synced memory with a user-facing warning.

Evidence: Personal sync gate and endpoint (search for `"tengu_marble_lark"` and `"/api/claude_code/memory?scope=user&repo="`); user-facing secret warning (search for `"cannot be written to memory. Memory is synced to your account"`).


### Per-Server MCP Tool Timeouts

Claude Code now supports a per-server `timeout` setting in MCP server config. This lets users tune timeout behavior for one slow or expensive MCP server without changing the global `MCP_TOOL_TIMEOUT`.

Evidence: MCP server setting description (search for `"Per-server tool-call timeout in milliseconds. Overrides the MCP_TOOL_TIMEOUT environment variable"`).


### Code Review Skill Is Now Correctness-Focused

The built-in `code-review` skill was rewritten from a general “reuse, quality, and efficiency” cleanup workflow into a correctness-bug review. It now accepts effort levels from `low` through `max`, can post inline PR comments with `--comment`, and explicitly reports findings instead of editing code itself.

Usage:
```bash
/code-review high
/code-review max --comment <PR-or-target>
```

Evidence: New skill description (search for `"Review the current diff for correctness bugs at the given effort level"` and `"Pass --comment to post findings as inline PR comments"`); old behavior existed in 2.1.146 as `"Review changed code for reuse, quality, and efficiency, then fix any issues found."`.


### Memory Recall Can Use Knowledge-Index Results

Memory recall can now pass knowledge-index search results into both memory selection and synthesis, letting Claude cite relevant knowledge entries alongside local memory files.

Evidence: New recall prompts and schemas (search for `"Knowledge-index results for this query (select by id):"`, `"Knowledge-index results for this query (cite by id):"`, and `"selected_knowledge_ids"`).


### Plugin and Workflow Signals Can Match Hostnames

Signal matching gained a `hosts` field that can match hostnames seen in `https?://` URLs from bash commands. This gives plugin/workflow authors a more precise trigger than only matching command names or file paths.

Evidence: Signal schema description (search for `"Hostnames (e.g. [\"api.stripe.com\"])"`).


### Safer Non-Interactive Unknown Slash Commands

Unknown slash commands in non-interactive sessions now return the unknown-command text as local command stdout instead of rendering the interactive warning path. This should make headless/scripted runs easier to parse and prevents an unknown slash command from falling into the wrong presentation mode.

Evidence: Non-interactive branch for unknown commands (search for `"Unknown command: /"` and `"isNonInteractiveSession"`).


### Safer Agent Guidance for Config Changes

The config-update skill guidance now more explicitly tells Claude to read existing settings first, merge arrays instead of replacing them, and use hooks for event-driven behavior instead of trying to store those preferences in memory.

Evidence: Config skill guidance (search for `"Always read the existing settings file before making changes"` and `"If the user wants something to happen automatically in response to an EVENT, they need a **hook** configured in settings.json"`).


## Bug Fixes

- MCP session expiry handling now treats server 404 expiry consistently instead of requiring the older `session-not-found` / `-32001` wording, improving reconnection behavior for expired MCP sessions. Evidence: MCP reconnection message changed from `"MCP session expired (server returned 404 with session-not-found)"` to `"MCP session expired (server returned 404)"`.

- Low-level file reading now clamps the final read size to the remaining byte count, avoiding over-reading on the last chunk. Evidence: file read loop now uses `Math.min(1048576, ... - ...)`; related user-facing file-read failure guidance can be found by searching for `"The file may be unsupported or corrupt; do not retry reading it"`.

- The safety classifier now more explicitly treats unrequested additions or widening of permission allow rules as self-modification, closing a loophole around changing Claude Code’s own permissions while editing config files. Evidence: self-modification rule now includes `"Includes adding or widening permission allow rules"`.

### Remote Trigger Client Hardening [In Development]

What: The remote trigger tool path was refactored to use the shared authenticated request client and now has clearer unavailable-state errors.

Status: Dark-launched/internal-facing infrastructure

Details:
- Trigger list/get/create/update/run paths still exist.
- The user-visible change is mostly better failure wording through `"Remote triggers unavailable:"`.
- This does not appear to add a new public CLI command in this package; it updates existing remote trigger infrastructure.

Evidence: Trigger API paths and failure message (search for `"/v1/code/triggers"` and `"Remote triggers unavailable:"`).


Generated with:
- tool: `harness-investigations@1d6cc84-dirty`
- provider: `codex`
- model: `gpt-5.5`
- reasoning effort: `medium`
- primary diff: `archive/claude-code/changes/changes-v2.1.147.md` (filtered astdiff)
- string diff: `archive/claude-code/changes/string-diff-v2.1.147.txt`
