# Changelog for version 2.1.152

## Summary
Claude Code 2.1.152 adds a new `MessageDisplay` hook for display-only transformation of assistant output, expands `/code-review` with `ultra` cloud review and `--fix` workflows, and begins rolling out auto mode as the default permission experience. It also tightens Claude in Chrome permissions, improves model fallback behavior, and ships hidden infrastructure for conversation import and coordinator-mode worker orchestration.

### MessageDisplay Hook
What: Hooks can now intercept assistant text as it is displayed and replace only the on-screen delta, without changing the stored transcript or what the model sees.

Usage:
```json
{
  "hooks": {
    "MessageDisplay": [
      {
        "command": "your-display-filter"
      }
    ]
  }
}
```

Details:
- The hook receives `turn_id`, `message_id`, `index`, `final`, and `delta`.
- It can return `hookSpecificOutput.displayContent` to replace the visible text for that flush.
- This is explicitly display-only: the stored message and model-visible content are untouched.
- Hook failures fall back to the original assistant text.

Evidence: New hook schema and runner for streamed assistant output (search for `"Hook input for the MessageDisplay event"` and `"displayContent"`)


### Code Review Ultra and Fix Mode
What: `/code-review` now understands an `ultra` mode for cloud review, and local code review can apply fixes with `--fix`.

Usage:
```bash
/code-review ultra
/code-review ultra --fix
/code-review --fix
/simplify
```

Details:
- `/code-review ultra` is wired as the primary cloud review entry point.
- `/ultrareview` remains available as a deprecated alias.
- `--fix` tells Claude to apply findings to the local working tree after review.
- `/simplify` is now a shortcut equivalent to `/code-review --fix`.

Evidence: Code-review command now has `subcommands: { ultra: "ultrareview" }` and fix instructions (search for `"/code-review ultra"` and `"Applying fixes (--fix)"`)


### Auto Mode Default Rollout
What: Claude Code now includes first-run UI for auto mode becoming the default permission mode, plus a nudge that can set auto mode as the user default.

Usage:
```bash
claude --permission-mode auto
```

Details:
- Users entering auto mode through the new default path see a notice explaining how auto mode evaluates tool calls.
- A gradual-rollout nudge can ask users whether to make auto mode their saved default.
- Accepting the nudge writes `permissions.defaultMode: "auto"` to user settings.
- The nudge is feature-flagged, so not every install will see it immediately.

Evidence: Auto mode notice and nudge dialogs (search for `"Auto mode is now Claude Code's default permission mode"`, `"Make auto mode your default permission mode?"`, and `tengu_maple_pier`)


### Claude in Chrome Domain Permissions
Claude in Chrome now has domain-scoped permission handling for browser actions. Instead of treating browser automation as a broad allow/deny decision, Claude Code can ask for permission on a specific host, remember allowed or denied domains, and reject browser-internal or unparseable URLs.

Evidence: Domain permission rule support for Chrome actions (search for `"ClaudeInChromeDomain"`, `"Allow Claude in Chrome to"`, and `"Claude in Chrome requires permission."`)


### Fallback Model Handles Unavailable Models
The `--fallback-model` help text and runtime now cover cases where the requested model is not available, not just overloads. When the primary model is missing or retired, Claude Code can switch to the configured fallback and emit a warning.

Evidence: Fallback model trigger for unavailable models (search for `"Switched to"` and `"model_not_found"`)


### Plugin and Marketplace Safety Checks
Plugin loading now has stronger safeguards for repo-supplied plugins and managed marketplace suggestions. Project-scope `@skills-dir` plugins cannot pull MCPB sources or reference MCP files outside their plugin directory, and marketplace suggestion tips are skipped unless the marketplace source is declared in managed settings.

Evidence: Repo-supplied plugin validation and managed marketplace checks (search for `"repo-supplied plugins must declare MCP servers inline"` and `"its registered source is not declared in managed settings"`)


### Thinking Summary Setting Clarified
The `showThinkingSummaries` setting description now says it requests API-side thinking summaries and shows them both in the conversation and transcript view. This replaces the older narrower description that only mentioned transcript view.

Evidence: Updated setting description (search for `"Request API-side thinking summaries and show them in the conversation"`)


## Bug Fixes

- Claude Code now retries after the server rejects a thinking-block signature by stripping signed thinking blocks and retrying. Evidence: signature retry path (search for `"[thinking] server rejected a thinking-block signature"`)

- API content filtering is now classified as `output_content_filtered`, giving clearer diagnostics when output is blocked by policy. Evidence: filtered-output handling (search for `"Output blocked by content filtering policy"` and `"API output_content_filtered:"`)

- Claude in Chrome now rejects browser-internal or unparseable URLs before attempting actions, instead of sending them to the browser bridge. Evidence: URL validation messages (search for `"Can't interact with browser-internal or unparseable URLs"`)

- Dangerous shell commands that remove the current working directory or a parent now require explicit approval and cannot be auto-allowed by permission rules. Evidence: new permission warning (search for `"This command would remove the current working directory or one of its parent directories"`)


## In Development

Features with infrastructure added but not yet enabled. These are shipped "dark" and may become available in future versions.


### Conversation Import Command [In Development]
What: A hidden `import-conversations` command can convert exported Claude conversations into local session/archive files.

Status: Stubbed behind environment variable

Details:
- The command is hidden from normal help output.
- It requires `CLAUDE_IMPORT_CONVERSATIONS` to be enabled.
- It supports `--cwd` to choose the archive directory and `--dry-run` to parse and verify without writing.
- It imports `manifest.json`, `conversations.json`, `projects.json`, project docs, files, and JSONL session records.

Evidence: Hidden import command gated by env var (search for `"import-conversations is not enabled"` and `"Parse and verify manifest without writing files"`)


### Coordinator Mode [In Development]
What: Claude Code now contains a coordinator-mode prompt and tool context for orchestrating worker agents, peer sessions, PR subscriptions, and shared scratchpad state.

Status: Environment-gated / partially dark-launched

Details:
- Activation depends on `CLAUDE_CODE_COORDINATOR_MODE`.
- The coordinator prompt describes worker spawning, stopping, continuation, cross-session peer messages, and PR activity subscriptions.
- Scratchpad support is additionally gated by `tengu_scratch`.
- The code path explicitly has `isCcrCoordinator` returning false, so part of this mode is still disabled.

Evidence: Coordinator-mode infrastructure (search for `"CLAUDE_CODE_COORDINATOR_MODE"`, `"Workers spawned via"`, and `"Scratchpad directory:"`)


### Workflow Disable Policy [In Development]
What: Managed settings can disable the Workflows feature.

Status: Internal managed setting / environment-gated

Details:
- A new `disableWorkflows` managed setting is recognized.
- `CLAUDE_CODE_DISABLE_WORKFLOWS` also disables workflows.
- The UI can report that workflows are disabled by managed settings.

Evidence: Workflow disable gate (search for `"Workflows are disabled by managed settings"` and `"CLAUDE_CODE_DISABLE_WORKFLOWS"`)


Generated with:
- tool: `harness-investigations@1d6cc84-dirty`
- provider: `codex`
- model: `gpt-5.5`
- reasoning effort: `medium`
- primary diff: `archive/claude-code/changes/changes-v2.1.152.md` (filtered astdiff)
- string diff: `archive/claude-code/changes/string-diff-v2.1.152.txt`
