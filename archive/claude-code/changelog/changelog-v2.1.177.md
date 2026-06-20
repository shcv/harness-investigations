# Changelog for version 2.1.177

## Summary

This patch introduces server-configurable model error overrides, allowing Anthropic to mark specific models as unavailable in the picker with explanatory hints rather than leaving users to encounter silent failures. A secondary change tightens auto-update eligibility to first-party (direct Anthropic API) installations only.

## New Features


### Model Error Overrides: Disabled Models Now Show Explanatory Hints

What: Anthropic can now configure server-side blocks for individual models, causing the model picker to show them as disabled with a descriptive message explaining why — instead of letting users select a model and hit an opaque error.

Details:
- A new remote configuration key (`tengu-model-error-overrides`) accepts a map of model IDs to override entries
- Each entry can specify a `block` string (shown as the reason) and an optional `pickerHint` (shown instead of the block text when both are present)
- Models with an active block appear grayed out at the bottom of the picker with the hint as their description
- The same config is also consulted asynchronously before API calls, so blocked models cannot be invoked even if the picker state was stale
- If reading the override config throws, the error is logged (`"model-error-overrides picker hint failed:"`) and the model is displayed normally — the feature degrades gracefully

Example override config shape (set server-side via the feature config system):
```json
{
  "claude-opus-4": {
    "block": "Temporarily unavailable due to capacity constraints.",
    "pickerHint": "Please use claude-sonnet-4-5 instead."
  }
}
```

Status: The client-side plumbing is fully enabled. Whether any specific model appears blocked depends on what Anthropic sets in the `tengu-model-error-overrides` remote config — no local configuration is required or possible.

Evidence: Model picker integration (search for `"model-error-overrides picker hint failed:"`) — picker now maps over model options calling `uQK` to check each model's override entry, marking it `disabled: true` with a description from the hint


## Improvements


### Auto-Update Restricted to First-Party Installations

The function that decides whether the Saffron Lattice auto-update path is available now returns false immediately for non-first-party installations (`l6() !== "firstParty"`). Users accessing Claude Code through Bedrock, Vertex AI, or other enterprise integrations will no longer have this update path evaluated for them.

This means the `tengu_saffron_lattice` feature — which governs a particular update flow — is now silently inactive for enterprise API users regardless of any server-side flag state.

Evidence: early-return guard added to the update-eligibility check (search for `"firstParty"` in the update-check function, `Gy8` at line ~408594)


### Saffron Lattice Feature Defaults to Explicitly Disabled

The `tengu_saffron_lattice` config reader previously fell back to `{}` when no server value was present; it now falls back to `{ enabled: false }`. This makes "disabled unless explicitly enabled" the canonical default state, closing a gap where an absent config could be interpreted as enabled.

Evidence: fallback default changed from `{}` to `{ enabled: !1 }` (search for `"tengu_saffron_lattice"`)


Generated with:
- tool: `harness-investigations@1d6cc84-dirty`
- provider: `claude`
- model: `claude-sonnet-4-6`
- primary diff: `archive/claude-code/changes/changes-v2.1.177-2.md` (filtered astdiff)
- string diff: `archive/claude-code/changes/string-diff-v2.1.177.txt`
