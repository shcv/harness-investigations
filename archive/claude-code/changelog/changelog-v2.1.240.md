# Changelog for version 2.1.240

## Summary

This release adds two server-controlled rollout paths: a clearer presentation for specially marked summarized thinking, and a prompt that can switch eligible Opus 5 users from high to medium default effort. Neither is enabled universally in the bundled CLI.

## In Development

Features with infrastructure added but not yet enabled. These are shipped “dark” and may become available in future versions.


### Summarized Thinking Display [In Development]

What: Claude Code can recognize specially signed narration-style thinking blocks and render them as a distinct summarized entry, including a `(summarized)` label and connector text.

Status: Feature-flagged. The display path defaults off unless enabled through `thinking_display_updates` / `tengu_thinking_display_updates`, and the signed-block classifier also requires `tengu_sable_thrush`.

Details:

- The new renderer labels eligible content as `(summarized)` rather than presenting it as ordinary thinking.
- The feature distinguishes summarized and omitted thinking from connector-only display modes.
- An advanced environment override, `CLAUDE_CODE_THINKING_DISPLAY_UPDATES`, exists, but it does not bypass the separate signed-block rollout gate.

Evidence: Summary renderer and classifier (search for `"(summarized)"`, `"summarized:"`, and `"thinking_display_updates"`).


### Default Medium-Effort Recommendation [In Development]

What: Eligible users may be offered a one-time prompt to make medium their default effort level.

Status: Feature-flagged. The prompt configuration is read from `tengu_radiant_island`; its default configuration is empty and fails validation, so it is unavailable without a server-provided rollout payload.

Details:

- The prompt is limited to completed-onboarding users on Claude Opus 5 whose effective effort is high.
- It can target users with no explicit effort setting or users who explicitly pinned high effort.
- Choosing the affirmative action saves medium effort to user settings and confirms with a notification.
- Users can decline with “No, keep high”; the prompt is recorded as seen either way.

Evidence: Effort-default prompt (search for `"Switch your default effort to medium?"`, `"Yes, use medium effort by default"`, and `"tengu_radiant_island"`).


Generated with:
- tool: `harness-investigations@f350b18-dirty`
- provider: `codex`
- model: `gpt-5.6-terra`
- reasoning effort: `medium`
- primary diff: `archive/claude-code/changes/changes-v2.1.240.md` (filtered astdiff)
- string diff: `archive/claude-code/changes/string-diff-v2.1.240.txt`
