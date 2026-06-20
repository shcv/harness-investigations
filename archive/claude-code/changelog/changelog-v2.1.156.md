# Changelog for version 2.1.156

## Summary
Claude Code 2.1.156 is a very small patch release over 2.1.154. The only diff-backed user-impacting changes are around preserving and recovering conversations that include signed or redacted thinking blocks, especially when tool-use content appears near thinking content.

## Bug Fixes

- Fixed an error-recovery gap where some API 400 responses about modified thinking signatures were not recognized unless the server used the exact phrase “thinking block.” Claude Code now also recognizes messages that mention `` `thinking` `` or `redacted_thinking`, so it can strip signed thinking blocks and retry instead of surfacing the raw invalid-request failure. Evidence: thinking-signature retry detection now searches for `` "`thinking`" `` and `"redacted_thinking"` in addition to `"thinking block"`; retry path logs `"retry:thinking-signature-strip"`.

- Fixed assistant-message normalization so Claude Code no longer reorders tool-use blocks across adjacent thinking or redacted-thinking blocks in cases where that could invalidate signed thinking content. This should reduce failures in longer conversations that mix tool calls with thinking blocks. Evidence: tool-use reorder logic now skips the reorder path and records `"tengu_reorder_tool_uses_skipped_for_thinking"` when it sees `"thinking"` or `"redacted_thinking"` around tool-use content.

## Notes
The diff from 2.1.154 to 2.1.156 contains no new commands, CLI flags, settings, environment variables, tips, or feature-gated workflows. Most structural and string changes are version metadata updates from `2.1.154` to `2.1.156`, build time changes, and the new commit SHA `de3d672b5e8c35ae78d81c9dd83844d334ec63af`.


Generated with:
- tool: `harness-investigations@1d6cc84-dirty`
- provider: `codex`
- model: `gpt-5.5`
- reasoning effort: `medium`
- primary diff: `archive/claude-code/changes/changes-v2.1.156.md` (filtered astdiff)
- string diff: `archive/claude-code/changes/string-diff-v2.1.156.txt`
