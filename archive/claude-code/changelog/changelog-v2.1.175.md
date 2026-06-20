# Changelog for version 2.1.175

## Summary

This release delivers a comprehensive enforcement overhaul for enterprise model allowlists. A new `enforceAvailableModels` managed setting ensures that even the automatic default model respects the organization's `availableModels` policy — previously only manual model selections were constrained. Across all model-selection paths (startup, plan mode, agent spawning, skill invocation, API control messages, and settings changes) Claude Code now validates against the allowlist and surfaces clear warnings when restrictions apply.


## New Features


### `enforceAvailableModels` — Policy-Enforced Default Model Constraint

What: A new managed settings field that, when set to `true`, also constrains the automatically chosen default model to the `availableModels` allowlist. Previously `availableModels` only filtered which models users could manually pick; the default model was always unrestricted.

Details:
- When `enforceAvailableModels: true` and `availableModels` is a non-empty array, the resting default model for the user's tier is checked against the allowlist. If it is not allowed, the first permitted entry in `availableModels` is used instead.
- This setting is for enterprise/managed deployments and belongs in admin-tier policy settings, not in user or project settings files.
- The setting is validated on load; a malformed value is treated as `true` (fail-safe enforcement) and a warning is logged.
- `enforceAvailableModels` without a companion `availableModels` array has no effect and logs a warning: `"enforceAvailableModels: the policy view sets the enforce flag but not availableModels; enforcement is disabled"`.

Evidence: New settings schema field (search for `"enforceAvailableModels"`) with `.describe("When true and availableModels is a non-empty array, the Default model selection is also constrained: if the default model for the user tier is not in availableModels, Default resolves to the first allowed availableModels entry instead."`)


### `CLAUDE_CODE_REMOTE_MEMORY_DIR` — Custom Memory Directory

What: A new environment variable that redirects memory file storage to a custom path instead of the default local directory.

Usage:
```bash
CLAUDE_CODE_REMOTE_MEMORY_DIR=/mnt/shared/claude-memory claude
```

Details:
- When set, all memory reads and writes use the specified path.
- Useful for shared or network-backed memory stores in multi-machine or container environments.
- Falls back to the default local directory when unset.

Evidence: New function that returns `process.env.CLAUDE_CODE_REMOTE_MEMORY_DIR` when defined (search for `"CLAUDE_CODE_REMOTE_MEMORY_DIR"`)


## Improvements


### Allowlist Enforcement Across All Model Selection Paths

All places where a model can be introduced into a session now validate against the `availableModels` allowlist. In v2.1.174, only explicit user selection in the model picker was checked; everything else could bypass the restriction.

The following paths now enforce the allowlist:

**Startup model**: When the session opens with a model outside the allowlist, the restricted model is recorded and a warning message is injected into the conversation transcript.

**Plan mode upgrades**: When the `opusplan` or `haiku` plan mode upgrade model is not in the allowlist, Claude falls back to the resting session model and logs: `"Plan mode: the opusplan upgrade model is not in the availableModels allowlist; planning uses the resting model instead"`.

**Agent and skill model overrides**: Agents or skills that specify a model field are now validated; if the requested model is outside the allowlist the session model is kept and a warning is logged: `"Agent model \"…\" is not in the availableModels allowlist; keeping the session model"` / `"Skill/command model \"…\" is not in the availableModels allowlist; keeping the session model"`.

**Sub-agent notifications**: When a spawned sub-agent's model is restricted, an `onModelRestricted` callback now triggers a medium-priority warning notification in the UI (search for `"agent-model-restricted-"` in notification keys).

**API `set_model` control messages**: The `set_model` control request now returns a proper error response when the requested model is not permitted, instead of silently applying or ignoring it.

**Settings changes**: When a model is set via `/settings` or equivalent and it fails the allowlist check, the restriction is surfaced and the previous model is retained.

Evidence: Consistent allowlist guard inserted across all model-assignment sites (search for `"is not in the availableModels allowlist"`)


### "Set by Your Organization" Model Indicator

When the effective model is forced by the `enforceAvailableModels` policy (i.e., the user's tier default was overridden by the allowlist), the model display now appends `"· Set by your organization"` to make the constraint visible.

A new `"model-restricted"` entry has also been added to the status bar's warning tier. It appears whenever the model Claude is using differs from what was requested due to policy, and shows the mapping between the requested and effective model name.

Evidence: New status-bar item with `id: "model-restricted"` (search for `"model-restricted"`) and indicator string (search for `"Set by your organization"`)


### Policy Cascade for `availableModels`

The `availableModels` array from admin-tier policy settings now propagates through the settings merge process: if a lower tier does not specify its own `availableModels`, the admin tier's value is used as a reference. `enforceAvailableModels: true` at the admin level is also carried through the cascade regardless of lower-tier settings.

Evidence: Settings merge function now includes `availableModels: w[0]?.availableModels` in the policy view (structural change to settings cascade logic)


### Detailed Policy-Load Warning Messages

When the policy enforcement system cannot fully load its configuration, it now emits precise diagnostic log entries instead of failing silently:

- `"enforceAvailableModels: a policy source exists but failed to load; refusing cascade-trust mode (model enforcement from user/project settings is disabled until the policy source is fixed)"`
- `"enforceAvailableModels: an admin policy source failed to load; enforcing the surviving admin tier (the failed source may carry a different policy — fix it to restore full coverage)"`
- `"enforceAvailableModels: an admin policy source failed to load and the surviving admin tier carries no model policy — model enforcement is OFF; the failed source may have carried it"`
- `"enforceAvailableModels: policy-tier settings read failed; refusing cascade-trust mode: <error>"`
- `"enforceAvailableModels: no availableModels entry expands to an allowed model; …"` (with fallback reason detail)
- `"enforceAvailableModels: no availableModels entry survived; N entries were allowed but skipped as server-unavailable (…); …"`

These messages appear in Claude Code's debug log and are deduplicated (each unique message is emitted only once per session).

Evidence: All messages listed above appear as string literals in the new policy enforcement function (search for `"enforceAvailableModels:"`)


### Server-Routed Model Allowlist Rejection

When the Anthropic server routes a response to a model outside the organization's `availableModels` allowlist, that response is now discarded and the user is notified: `"The server routed this response to a model that is not in your organization's availableModels allowlist; the response was discarded."`

Evidence: Search for `"The server routed this response to a model that is not in your organization's availableModels allowlist"`


### Model Swap Blocked by Allowlist — Warning With Fallback Action

When a server-suggested model swap targets a model outside the allowlist, the warning now reads `"Server refusal-fallback target … is not in the availableModels allowlist; keeping the tier default"` rather than silently falling back. The action buttons offered to the user when a safety refusal occurs also now correctly show `"Switch to <effective model>"` and `"Edit prompt and retry with <requested model>"` using the resolved model names.

Evidence: New helper builds retry-fallback and edit-prompt labels (search for `"Switch to"` / `"Edit prompt and retry with"`)


## Bug Fixes

- Safety refusal messages now consistently read "has **safety** measures that flagged something in this session" instead of the previous "has measures that flagged something in this session" — the word "safety" was dropped in a prior release and is restored. (Search for `"has safety measures that flagged something in this session"`)

- When the `set_model` control request is rejected due to an allowlist constraint, the error response is now returned immediately rather than the request proceeding with the disallowed model before being silently discarded. (Search for `"model-restricted-bridge-"` in notification keys)

- Model names used in notification keys are now sanitized through a dedicated helper that strips characters outside `[A-Za-z0-9._:/@[\]-]` and truncates at 128 characters, preventing malformed key strings. Returns `"(unrecognized model name)"` for empty results. (Search for `"(unrecognized model name)"`)


Generated with:
- tool: `harness-investigations@1d6cc84-dirty`
- provider: `claude`
- model: `claude-sonnet-4-6`
- primary diff: `archive/claude-code/changes/changes-v2.1.175-2.md` (filtered astdiff)
- string diff: `archive/claude-code/changes/string-diff-v2.1.175.txt`
