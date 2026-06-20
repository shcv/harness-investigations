# Changelog for version 2.1.143

## Summary
Claude Code 2.1.143 expands background-agent control, adds a shareable-conversation support flow, and introduces configurable multi-store team memory sync. It also improves plugin discovery metadata, worktree cleanup diagnostics, hook-stop behavior, remote transport diagnostics, and shell argument safety.

### Agent View Dispatch Configuration
What: The `claude agents` command now exposes more of the same environment-shaping controls available to regular Claude Code sessions, so dispatched background sessions can be launched with extra directories, plugin roots, settings, and MCP configuration.

Usage:
```bash
claude agents --add-dir ../shared --plugin-dir ./plugins --mcp-config ./mcp.json --strict-mcp-config
```

Details:
- New `claude agents` options include `--add-dir`, `--plugin-dir`, `--settings`, `--mcp-config`, and `--strict-mcp-config`.
- `--allow-dangerously-skip-permissions` now makes bypass mode available to dispatched sessions without making it the default.
- `claude agents` now rejects excess unrecognized arguments, which should make typo failures clearer.

Evidence: `claude agents` option registration (search for `"Additional directory to allow tool access to in dispatched sessions"` and `"Make bypass-permissions mode available to dispatched sessions without defaulting to it"`). These options were absent from the 2.1.142 `agents` command registration.


### Shareable Conversation Support Flow
What: `/feedback` can now create a shareable conversation link for debugging and support.

Usage:
```bash
/feedback
```

Details:
- The new flow tells users exactly what will be included before upload.
- It distinguishes shared-conversation consent from ordinary feedback submission.
- The wording was updated from a generic feedback-use statement to a more specific debugging/support explanation.

Evidence: Share consent UI (search for `"A shareable link will be created so you can post the conversation for debugging and support."`, `"This shared conversation will include:"`, and `"Uploading share…"`). These strings are new in 2.1.143.


### Configurable Multi-Store Team Memory Sync
What: Team memory can now be configured from multiple mounted stores through `CLAUDE_MEMORY_STORES`.

Usage:
```bash
CLAUDE_MEMORY_STORES='[
  {"path":"/api/org/memory/main","mount":"main","mode":"rw"},
  {"path":"/api/org/memory/reference","mount":"reference","mode":"ro"}
]' claude
```

Details:
- Each store has a path, mount name, and `rw` or `ro` mode.
- Read-only mounts refuse writes.
- Sync protects against path traversal, oversized files, and secret-looking content.
- Invalid JSON, duplicate mounts, invalid mount names, and malformed backend responses now produce explicit diagnostics.

Evidence: Multi-store memory parser and sync backend (search for `"CLAUDE_MEMORY_STORES failed validation:"`, `"memory-stores: parsed"`, `"refused on read-only mount"`, and `"multi-store-sync:"`). `CLAUDE_MEMORY_STORES` does not appear in 2.1.142.


### Plugin Relevance Metadata
What: Plugin manifests and marketplace entries can now declare richer discovery metadata so Claude Code can suggest plugins when they match the current work.

Usage:
```json
{
  "name": "stripe-tools",
  "displayName": "Stripe Tools",
  "relevance": {
    "topic": "Stripe",
    "signals": {
      "cli": ["stripe"],
      "manifestDeps": [{"file": "package.json", "pattern": "stripe"}]
    }
  }
}
```

Details:
- `displayName` lets plugin authors show a human-readable name without changing the plugin namespace.
- `relevance.topic` fills “Working with {topic}?” style suggestions.
- Relevance signals can match CLI command tokens, file paths, and dependency declarations in manifests.

Evidence: Plugin schema additions (search for `"Human-readable name shown in UI"`, `"First command tokens"`, `"Dependency declared in a package manifest"`, and `"Declares when this plugin is relevant to the user's work."`). The relevance schema is new in 2.1.143.

### Background Isolation Can Be Disabled Per Repo
Background sessions now have an explicit `worktree.bgIsolation: none` path for repos that intentionally want background jobs editing the shared checkout.

Evidence: Background-session guidance (search for `"This repository is configured with `worktree.bgIsolation: none`"` and `"To disable this guard for this repo"`).


### Plugin Names Are Shown More Nicely
Plugin install, configure, picker, and command descriptions now prefer the manifest `displayName` while preserving the technical plugin name where useful.

Evidence: Plugin display helper (search for `"Configure ${tf"` and `"Installed and configured ${tf"`), backed by the new `displayName` schema.


### Fullscreen Renderer Switching Gives Better Recovery
`/tui` now reports when a renderer switch could not be applied immediately, saves the setting, and tells the user to restart Claude Code. Switching back from fullscreen can also ask for optional feedback.

Evidence: TUI messages (search for `"Couldn't switch renderers"` and `"To help us make fullscreen mode better"`).


### Remote Transport Diagnostics Are More Specific
Remote-control and bridge transports now report connection, reconnection, liveness-timeout, and retry-budget details instead of only generic close messages.

Evidence: Transport diagnostics (search for `"WS connected in"`, `"WS reconnected after"`, `"WS reconnection budget exhausted"`, `"SSE connected in"`, and `"PUT /worker retries exhausted"`).


### Channel Plugin Template Support
Plugin scaffolding now includes a channel-server template for stdio MCP servers that implement Claude Code’s channel contract.

Evidence: Channel scaffold template (search for `"channel server — stdio MCP server implementing the channel contract"` and `"experimental: { 'claude/channel': {} }"`).

## Bug Fixes

- Shell permission analysis now treats runtime-generated arguments that may start with option syntax as too complex, preventing unsafe auto-classification of commands whose arguments can become flags. Evidence: search for `"Argument starting with `-` contains runtime-determined content"` and `"cat-heredoc body would make the argument start with option syntax"`.

- Stop and SubagentStop hooks now have a cap for repeated turn-ending blocks, with guidance to check `stop_hook_active` and an override via `CLAUDE_CODE_STOP_HOOK_BLOCK_CAP`. Evidence: search for `"A hook blocked the turn from ending"` and `"CLAUDE_CODE_STOP_HOOK_BLOCK_CAP"`.

- Prompt hook conditions can now report that a condition is impossible, allowing Claude Code to end a blocked stop condition cleanly instead of continuing forever. Evidence: search for `"Whether the condition can never be satisfied"` and `"Hooks: Prompt hook condition judged impossible"`.

- Worktree cleanup failures now keep and report the worktree path instead of implying cleanup succeeded or exiting with only a generic failure. Evidence: search for `"Worktree could not be removed — kept at"`, `"Failed to remove linked worktree, kept"`, and `"removeAgentWorktree: git worktree remove failed, kept"`.

- Passing the same `--fallback-model` as the main model no longer produces the old top-level CLI error; the duplicate fallback is omitted before launch. Evidence: the old string `"Error: Fallback model cannot be the same as the main model. Please specify a different model for --fallback-model."` is removed, while fallback args are now guarded before dispatch.

- Clipboard reads now have a dedicated cross-platform helper that avoids SSH sessions, uses `Get-Clipboard -Raw` on Windows/WSL, and tries `wl-paste`, `xclip`, and `xsel` on Linux. Evidence: search for `"Get-Clipboard -Raw"` and `"wl-paste"`.

## In Development

Features with infrastructure added but not yet clearly exposed as stable CLI workflows. These are shipped dark or appear to be tied to remote/service-side rollout.


### PR Auto-Fix Remote Workflows [In Development]
What: Claude Code now contains UI and status text for remote workflows that monitor pull requests and can post comments using the user’s GitHub identity.

Status: Dark-launched or service-gated; the diff shows UI strings and status handling, but no ordinary new CLI command surfaced in the package diff.

Details:
- New strings describe PR monitoring and remote workflow completion.
- The UI can show counts like “1 remote workflow” or multiple remote workflows.
- This appears related to background/remote workflow infrastructure rather than a universally available terminal command.

Evidence: Remote workflow UI (search for `"Auto-fix monitors the PR and can post comments on your behalf using your GitHub identity."`, `"start monitoring this PR"`, and `"Remote workflow completed"`).


Generated with:
- tool: `harness-investigations@1d6cc84-dirty`
- provider: `codex`
- model: `gpt-5.5`
- reasoning effort: `medium`
- primary diff: `archive/claude-code/changes/changes-v2.1.143.md` (filtered astdiff)
- string diff: `archive/claude-code/changes/string-diff-v2.1.143.txt`
