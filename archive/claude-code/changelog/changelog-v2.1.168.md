# Changelog for version 2.1.168

## Summary

This is a small internal release (100% structural similarity to 2.1.167) focused on preparing extended-thinking support for upcoming model families. Three new model codenames — "fruitcake", "macaroon", and "mythos" — are registered so that thinking is automatically enabled for any model whose name contains these strings, bypassing the usual `disableThinking` configuration path. No new user-facing commands or settings were added.

## Improvements

### Extended thinking support for upcoming model families

What: Claude Code now unconditionally enables extended thinking when it detects that the active model belongs to one of three new model families, identified by the substrings "fruitcake", "macaroon", or "mythos" in the model name.

Details:
- A new internal list `ZW_ = ["fruitcake", "macaroon", "mythos"]` is checked against the active model identifier (case-insensitive substring match).
- When a match is found, the permission/security classifier that runs in the background is given a 2048-token thinking budget instead of the previous default of zero (thinking disabled).
- Separately, the background tool-call classifier also receives a thinking budget for these models, bypassing any `disableThinking` flag that may be set in user configuration or a server-side feature flag.
- The main conversation thinking path has an additional guard: even if the user has configured thinking as "disabled", that setting is ignored for models in this group.
- `claude-mythos-preview` was already present in the model list in v2.1.167; this change adds the broader pattern match so any future model with "mythos" in its identifier gets the same treatment without a separate code change. The "fruitcake" and "macaroon" families have no corresponding model strings yet in the codebase — this is infrastructure-only.

Evidence: New model-family list (search for `"fruitcake"` or `ZW_`); thinking-enable check (search for `ecH(H)`) — `xp7()` at line ~332464 returns `[void 0, 2048]` and main thinking path at line ~672006 adds `!ecH(Y)` guard.

## Notes

The "fruitcake" and "macaroon" family names have no associated model string values anywhere in the codebase yet. Users cannot select or reference them; the code additions are purely preparatory for a future model launch. "mythos" maps to the already-present `claude-mythos-preview` model identifier.


Generated with:
- tool: `harness-investigations@1d6cc84-dirty`
- provider: `claude`
- model: `claude-sonnet-4-6`
- primary diff: `archive/claude-code/changes/changes-v2.1.168-2.md` (filtered astdiff)
- string diff: `archive/claude-code/changes/string-diff-v2.1.168.txt`
