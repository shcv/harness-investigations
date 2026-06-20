# Changelog for version 2.1.159

## Summary
Claude Code 2.1.159 is a very small CLI release with no fully enabled new user commands or flags found in the diff. The notable changes are gated infrastructure for a new `SendUserMessage` behavior, a new `narration_summaries` API beta path, and a brief-mode transcript fix that should prevent assistant text from being hidden before a `SendUserMessage` call has actually succeeded.

### Brief-Mode Delivery Uses a More Precise Tool Prompt
What: Claude Code now has an alternate `SendUserMessage` prompt for sessions where the message tool is available outside the older brief-mode behavior.

Details:
- The existing `SendUserMessage` tool remains present from 2.1.158.
- 2.1.159 adds a second prompt that tells the model to use the tool for exact, user-visible content between tool calls, such as generated snippets, values, or direct replies during ongoing work.
- This is not a new slash command or CLI flag, and it is not enabled for all sessions.

Evidence: Alternate `SendUserMessage` prompt added only in 2.1.159 (search for `"Send a message the user will read verbatim"`); the existing tool name is still `"SendUserMessage"`.


### Feature-Rollout Cache Refresh
What: Claude Code now clears cached capability/header decisions when bootstrap `client_data` changes.

Details:
- The bootstrap flow already persisted server-provided `client_data`.
- 2.1.159 adds cache invalidation when that `client_data` differs, which should help server-controlled feature gates take effect more reliably without stale local decisions.
- This is mainly visible for gradual rollouts and account/model-specific feature availability.

Evidence: Bootstrap cache update path now calls cache clearing when `client_data` changes (search for `"[Bootstrap] Cache updated, persisting to disk"` and `"client_data"`).

## Bug Fixes

- Brief-mode transcript filtering now waits for a successful `SendUserMessage` tool result before hiding related assistant text. Previously, the transcript filter could mark text as handled as soon as the `SendUserMessage` tool call appeared; 2.1.159 tracks the tool-use id and only hides the text after a non-error `tool_result`. Evidence: brief transcript filter now checks `tool_result`, `tool_use_id`, and `!f.is_error` around the `"SendUserMessage"` tool path.

- `SendUserMessage` rendering in the normal transcript path now uses the same left-edge message marker layout as other assistant messages, instead of reserving a blank two-column spacer. This is a small display polish for sessions where the tool is enabled. Evidence: message rendering for the `SendUserMessage` result changed near the tool definition (search for `"Send a message to the user"` and `"fromLeftEdge"`).

## In Development

Features with infrastructure added but not yet enabled for everyone. These are shipped behind flags, server-provided client data, or environment overrides and may become available in future versions.


### Pewter Owl Message Mode [In Development]
What: A new gated mode appears to let Claude send exact user-visible messages through `SendUserMessage` without enabling the full older brief-mode behavior.

Status: Feature-flagged / gradual rollout

Details:
- New gates were added for `pewter_owl_header`, `pewter_owl_tool`, and `pewter_owl_brief`.
- The mode can be controlled by server flags/client data, constrained to a configured model via `tengu_pewter_owl_model`, and overridden by `CLAUDE_CODE_PEWTER_OWL`.
- When enabled for the tool, the `SendUserMessage` tool can use the new verbatim-message prompt instead of the full brief-mode prompt.
- No public CLI command or settings-schema entry was added for this in the diff.

Evidence: Gated Pewter Owl checks (search for `"CLAUDE_CODE_PEWTER_OWL"`, `"tengu_pewter_owl_model"`, and `"pewter_owl_tool"`); new prompt text (search for `"Send a message the user will read verbatim"`).


### Narration Summaries API Beta [In Development]
What: Claude Code can now attach a new `narration_summaries` beta header when the Pewter Owl header gate is enabled.

Status: Feature-flagged

Details:
- 2.1.159 adds the beta identifier `summarize-connector-text-2026-03-13`.
- The header is only pushed when the session is eligible for experimental betas and the `pewter_owl_header` gate is active.
- This looks like backend support for summarizing or transforming connector/narration text, but the diff does not expose a user command or setting for it.

Evidence: New beta registration (search for `"narration_summaries"` and `"summarize-connector-text-2026-03-13"`); activation gate (search for `"pewter_owl_header"`).


Generated with:
- tool: `harness-investigations@1d6cc84-dirty`
- provider: `codex`
- model: `gpt-5.5`
- reasoning effort: `medium`
- primary diff: `archive/claude-code/changes/changes-v2.1.159.md` (filtered astdiff)
- string diff: `archive/claude-code/changes/string-diff-v2.1.159.txt`
