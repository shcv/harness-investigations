# Changelog for version 2.1.154

## Summary
Claude Code 2.1.154 adds Claude Opus 4.8 as the primary Opus option, introduces SDK/print-mode prompt suggestions, and adds a new ultracode effort mode for sessions that can use dynamic workflows. It also improves plugin author controls, MCP safety messaging, Remote Control diagnostics, Claude in Chrome browser selection, and several reliability paths for hooks and cloud MCP connectors.

### Claude Opus 4.8 Support
What: Claude Code now recognizes Opus 4.8 across first-party, Bedrock, Vertex, Foundry, Anthropic AWS, Mantle, and gateway provider mappings, and updates model-picker copy to make Opus 4.8 the most capable Opus option.

Usage:
```bash
claude --model opus
claude --model claude-opus-4-8
```

Details:
- `/model` now presents Opus 4.8 as the main Opus choice.
- The long-context Opus option also moves to Opus 4.8.
- Launch messaging says Opus 4.8 is available and notes the default high-effort behavior.

Evidence: Model mapping and launch UI (search for `"claude-opus-4-8"`, `"Opus 4.8 is now available!"`, and `"Now defaults to high effort"`)


### Prompt Suggestions for Stream JSON
What: Non-interactive SDK/print sessions can now request predicted next prompts after each turn.

Usage:
```bash
claude --print --output-format=stream-json --prompt-suggestions "inspect this repo"
claude -p --output-format=stream-json --prompt-suggestions=true "summarize the changes"
```

Details:
- Adds `--prompt-suggestions [value]` with boolean-style values: `true`, `false`, `1`, `0`, `yes`, `no`, `on`, `off`.
- When enabled, Claude Code emits a `prompt_suggestion` stream message after a turn.
- The flag is only valid with `--print` and `--output-format=stream-json`.

Evidence: New CLI flag and stream message emission (search for `"--prompt-suggestions [value]"`, `"prompt_suggestion"`, and `"Error: --prompt-suggestions requires --print and --output-format=stream-json"`)


### Ultracode Effort Mode
What: A new `ultracode` effort mode sets xhigh effort and keeps dynamic workflow orchestration active for the session.

Usage:
```bash
/effort ultracode
claude --settings '{"ultracode":true}'
```

Details:
- `ultracode` is session-scoped, not a persisted interactive preference.
- It requires dynamic workflows to be enabled and an xhigh-capable model.
- `/effort current` reports ultracode status when active.
- If `CLAUDE_CODE_EFFORT_LEVEL` conflicts, Claude Code tells the user that the environment variable overrides the session effort.

Evidence: Effort setting and command handling (search for `"Enable ultracode for the session: xhigh effort plus standing dynamic-workflow orchestration"`, `"Usage: /effort <low|medium|high|xhigh|max"`, and `"CLAUDE_CODE_EFFORT_LEVEL="`)


### Plugin `defaultEnabled`
What: Plugin authors can now mark a plugin as disabled by default until the user explicitly enables it.

Usage:
```json
{
  "name": "example-plugin",
  "defaultEnabled": false
}
```

Details:
- `defaultEnabled` applies when the user has no explicit enabled/disabled setting.
- Explicit `enabledPlugins` settings still win.
- Dependencies required by an enabled plugin can still be enabled regardless of the default.
- Install messages now tell users when a plugin was installed but remains disabled.

Evidence: Plugin manifest schema and install copy (search for `"Whether the plugin starts enabled when the user has no explicit enabled/disabled setting for it"` and `"This plugin is disabled by default"`)

### Dynamic Workflows Availability
Dynamic workflows are still controlled by policy and rollout gates, but the default feature-gate path now defaults `tengu_workflows_enabled` to true once workflow support is otherwise available. The settings schema also exposes workflow enable/disable controls without the previous internal-only description.

Evidence: Workflow availability gate and settings text (search for `"tengu_workflows_enabled"` and `"Disable the Workflows feature (also via CLAUDE_CODE_DISABLE_WORKFLOWS)."`)


### `/simplify` Now Focuses on Cleanup
The existing `/simplify` command has been repurposed from a code-review fix shortcut into a quality cleanup workflow focused on reuse, simplification, efficiency, and abstraction level. It explicitly says correctness bugs belong in `/code-review`.

Evidence: Updated command description (search for `"Review the changed code for reuse, simplification, efficiency, and altitude cleanups"`)


### Safer MCP List/Get Behavior
`claude mcp list` and `claude mcp get` now describe unapproved `.mcp.json` servers as pending approval and not connected, rather than implying Claude Code spawns them for health checks before trust is approved.

Evidence: MCP command descriptions (search for `"Unapproved .mcp.json servers are shown as ⏸ Pending approval and not connected to"`)


### Better Remote Control Eligibility Diagnostics
Remote Control now distinguishes disabled feature-flag evaluation, stale/unreachable GrowthBook feature data, and account entitlement failures. It also exposes a detailed check list for provider, login, subscription, profile scope, organization UUID, and the `tengu_ccr_bridge` gate.

Evidence: Remote Control checks and errors (search for `"Remote Control requires feature-flag evaluation"`, `"Remote Control eligibility could not be determined"`, and `"tengu_ccr_bridge gate"`)


### Claude in Chrome Browser Picker
The `/chrome` settings flow can now list connected browsers and let users select which browser receives Chrome actions. It reports empty, loading, success, and failure states.

Evidence: Browser selection UI (search for `"Choose which browser to use"`, `"No browsers are connected"`, and `"Now using browser"`)


### Structured Git Operation Metadata
Tool results now include structured `gitOperation` metadata for commit, push, merge/rebase, and GitHub PR operations. This is client-facing metadata so SDKs and UIs can render git activity without scraping stdout.

Evidence: Tool output schema (search for `"gitOperation"` and `"Structured classification of git/gh operations detected in this command"`)


### Clearer Anthropic Profile Auth Warnings
When both an Anthropic profile and a claude.ai login are present, Claude Code now warns which credential source takes precedence and how to force profile auth with `ANTHROPIC_PROFILE`.

Evidence: Auth precedence warning (search for `"An Anthropic profile (~/.config/anthropic) is configured, but a claude.ai login exists"`)

## Bug Fixes

- Cloud claude.ai MCP connector fetches now retry transient failures with backoff and a retry budget instead of failing immediately on temporary errors. Evidence: retry logging (search for `"[claudeai-mcp] Transient fetch error"` and `"[claudeai-mcp] Retry budget exhausted after"`)

- Hook prompt evaluators now retry with fewer messages when the evaluator prompt is too long, reducing non-blocking hook failures on large transcripts. Evidence: hook retry path (search for `"Hooks: evaluator prompt too long; retrying with"`)

- Plugin initialization now warns when a new local plugin name is shadowed by managed settings, an installed plugin, or a disabled setting, instead of implying it will load normally. Evidence: plugin conflict warnings (search for `"is already taken by"` and `"A disabled setting for"`)

- Windows auto-update failures caused by a locked `claude.exe` now tell users to close other Claude Code sessions or run `claude doctor`. Evidence: update error copy (search for `"Error: Update failed because claude.exe is in use"`)


Generated with:
- tool: `harness-investigations@1d6cc84-dirty`
- provider: `codex`
- model: `gpt-5.5`
- reasoning effort: `medium`
- primary diff: `archive/claude-code/changes/changes-v2.1.154.md` (filtered astdiff)
- string diff: `archive/claude-code/changes/string-diff-v2.1.154.txt`
