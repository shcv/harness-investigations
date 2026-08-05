# Changelog for version 2.1.223

## Summary

This release adds connected project-memory tools for eligible sessions, strengthens automatic context-window handling for unrecognized models, and expands `/code-review` targeting and effort reuse. It also adds a guarded resume-truncation option for print-mode integrations.

## New Features

### Connected Project Memory Tools

What: Claude can now list and read documents from memory stores connected to the current session.

Usage:

Ask Claude to use connected project memory, for example: “Check the project memory for prior decisions about this repository.”

Details:

- Adds the read-only `memory_list` and `memory_read` tools.
- `memory_list` can enumerate connected stores or list documents under a path prefix; `memory_read` retrieves a document by store ID and absolute path.
- Store access is available only when the workspace is trusted, organization-memory access is enabled, and a store is connected. The tools clearly refuse access when those prerequisites are not met.
- Store content is treated as reference material rather than executable instructions.

Evidence: New `memory_list` and `memory_read` tool registrations (search for `"memory_list"` and `"Read a memory document."`); eligibility checks refuse access when `"This workspace has not been granted trust yet"` or `"No memory store is connected to this session."`


## Improvements

### Safer Context Limits for Unrecognized Models

Claude Code now applies a conservative automatic context limit when it does not recognize the configured model, rather than waiting for the API to determine the model’s window.

Usage:

```bash
CLAUDE_CODE_MAX_CONTEXT_TOKENS=200000 claude
```

Details:

- Claude Code warns when a model name is unknown and explains the assumed auto-compact window.
- To use a larger recognized context window, use a recognized model name, append `[1m]` where applicable, configure `modelOverrides`, or update Claude Code.
- Advanced users can restore the previous API-driven behavior with `CLAUDE_CODE_DISABLE_UNKNOWN_MODEL_WINDOW_ENFORCEMENT=1`.

Evidence: Unknown-model warning and opt-out guidance (search for `"is not a model this version of Claude Code recognizes"` and `"CLAUDE_CODE_DISABLE_UNKNOWN_MODEL_WINDOW_ENFORCEMENT=1"`)


### More Flexible Code Review Targets and Remembered Effort

`/code-review` can now describe and accept broader review targets, while remembering the effort level you last selected when you omit one.

Usage:

```text
/code-review high src/auth.ts
/code-review medium feature/my-branch
/code-review --comment 123
/code-review --fix
```

Details:

- Review targets can be a PR number, branch, path, ref range, or free-form review instructions.
- `--comment` posts findings as inline PR comments, while `--fix` applies findings to the working tree after review.
- When no effort level is given, Claude Code reuses the previously selected level and tells you how to change it.

Evidence: Expanded command description (search for `"Review the current diff, or a PR number/branch/path target"`) and retained-effort notice (search for `"No effort level given"`)


### Safer Print-Mode Resume Truncation

A hidden print-mode option now lets integrations truncate a resumed session only when the discarded range belongs entirely to the intended turn.

Usage:

```bash
claude --print --resume <session-id> \
  --resume-session-at <kept-message-id> \
  --resume-drops-turn <turn-prompt-id>
```

Details:

- `--resume-drops-turn` requires `--resume-session-at`.
- Claude Code refuses the resume if the removed range contains queued messages, task notifications, or content attributable to another turn.
- This is primarily useful for SDK and automation integrations that need to resume from a safe transcript boundary.

Evidence: Option help and rejection path (search for `"--resume-drops-turn <message id>"` and `"Resume rejected by --resume-drops-turn:"`)


### Clearer Web-to-Terminal Teleport Guidance

When a cloud session is already running on the web, Claude Code now explains how to continue it locally and reminds users that `/teleport` must run from a terminal checkout.

Usage:

```bash
claude --teleport <session-id>
```

Details:

- The guidance includes the repository-checkout requirement.
- On claude.ai, it points users to the session menu’s Open in → Terminal flow.

Evidence: Web-session handoff message (search for `"/teleport pulls a cloud session into a terminal on your own machine"`)


Generated with:
- tool: `harness-investigations@0036485-dirty`
- provider: `codex`
- model: `gpt-5.6-terra`
- reasoning effort: `medium`
- primary diff: `archive/claude-code/changes/changes-v2.1.223.md` (filtered astdiff)
- string diff: `archive/claude-code/changes/string-diff-v2.1.223.txt`
