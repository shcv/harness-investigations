# Changelog for version 2.1.170

## Summary

This release introduces Claude Fable 5, a new top-tier model above Opus, accessible via the `fable` alias in all model-selection surfaces. Alongside the model launch, the refusal fallback system gains a richer `model_refusal_fallback` event schema with category, explanation, and retraction details, and tool dispatch now cancels cleanly when a server-side fallback retracts a call mid-flight. Several improvements to the model picker, rate-limit messaging, and the enterprise Vertex AI setup flow round out the release.


## New Features


### Claude Fable 5 model support

What: Claude Fable 5 (`claude-fable-5`) is now a first-class model in Claude Code, available as the `fable` alias — the same way `opus`, `sonnet`, and `haiku` work. It is positioned as the highest-capability tier, above Opus, designed for the hardest and longest-running tasks.

Usage:
```bash
claude --model fable

# or switch interactively
/model
```

Details:
- The `fable` alias and `fable[1m]` (1M-context variant) are recognized everywhere model aliases are accepted: `--model`, `/model`, settings files, and the `model` field in `CLAUDE.md` frontmatter
- When you are on Fable 5, the status area shows "Fable 5 is here! Our newest model for complex, long-running work"
- Token limits: 64 k default thinking, 128 k max output — same as Opus 4.8
- Knowledge cutoff: January 2026 (same as Opus 4.8)
- If Fable 5 experiences high load, Claude Code shows: "Fable is experiencing high load, please use /model to switch to Sonnet"
- When Fable 5 is rate-limited on a Pro plan, the model-switch suggestion is "try /model opus · more runway" (Fable costs more runway than Opus)
- The fallback model for Fable 5 (e.g. for background tasks) is Opus 4.8 (or `ANTHROPIC_DEFAULT_OPUS_MODEL` if set)
- Subagents (the `Agent` tool) now accept `"fable"` in the `model` parameter

Evidence: model alias registration (search for `"fable"` in model alias tables) — `wkH` at line ~119375, launch banner (search for `"Fable 5 is here!"`)


### New environment variables for Fable 5 (enterprise / BYOC)

What: Four new environment variables let enterprise and bring-your-own-cloud deployments customize the Fable 5 model used by Claude Code, mirroring the existing `ANTHROPIC_DEFAULT_OPUS_MODEL` family.

Details:
- `ANTHROPIC_DEFAULT_FABLE_MODEL` — Override the Fable 5 model ID (e.g. a specific snapshot or a private endpoint). When set, enables the `fable` alias even on providers that don't expose Fable 5 by default.
- `ANTHROPIC_DEFAULT_FABLE_MODEL_NAME` — Custom display name shown in the model picker.
- `ANTHROPIC_DEFAULT_FABLE_MODEL_DESCRIPTION` — Custom description shown in the model picker.
- `ANTHROPIC_DEFAULT_FABLE_MODEL_SUPPORTED_CAPABILITIES` — Declare which capabilities your custom Fable endpoint supports.
- `VERTEX_REGION_CLAUDE_FABLE_5` — Pin Fable 5 to a specific Vertex AI region, like the existing per-model region env vars.

For providers that don't natively expose Fable 5, Claude Code displays: "To enable automatic fallback on this provider, set `ANTHROPIC_DEFAULT_FABLE_MODEL` to your Fable 5 model ID and `ANTHROPIC_DEFAULT_OPUS_MODEL` to your Opus 4.8 model ID."

Evidence: env var whitelist (search for `"ANTHROPIC_DEFAULT_FABLE_MODEL"`) — `MW8` at line ~354090; Vertex region entry (search for `"VERTEX_REGION_CLAUDE_FABLE_5"`)


### Fable 5 model pinning in Vertex AI setup

What: The Vertex AI provider setup flow now includes a Fable 5 pinning option alongside the existing Sonnet, Opus, and Haiku pins.

Details:
- The `pinFable` field is accepted in the Vertex AI configuration object and translates to `ANTHROPIC_DEFAULT_FABLE_MODEL` in the spawned environment
- The setup completion event (`tengu_vertex_setup_complete`) now reports whether any of Sonnet, Opus, Fable, or Haiku was pinned

Evidence: Vertex AI setup form (search for `"pinFable"`) — `dG4` at line ~466092; `X04` at line ~467646


### `model_refusal_fallback` system event with category and retraction data

What: When Claude Code's refusal-fallback mechanism fires (the primary model refuses a request and the session falls back to another model), a new `model_refusal_fallback` system event is now emitted with richer structured data compared to the previous generic `model_fallback` event.

Details:
New fields on the `model_refusal_fallback` event:
- `direction`: `"retry"` | `"revert"` | `"sticky"` — indicates the fallback strategy; currently only `"retry"` is emitted
- `api_refusal_category`: the API's refusal category string (e.g. `"cyber"`, `"bio"`); open-ended — new categories may appear before schema updates
- `api_refusal_explanation`: human-readable explanation from the API (display only, do not parse)
- `retracted_message_uuids`: list of wire UUIDs the fallback retracted — consumers should evict these messages from transcript state on receipt; eviction is idempotent

This event is primarily relevant to SDK consumers and integrators reading the transcript stream.

Evidence: new system event schema (search for `"model_refusal_fallback"`) — added in `NF6` at line ~340786


### Tool dispatch cancellation on server-fallback tombstone

What: When a server-side refusal fallback retracts a tool call that is already in flight, Claude Code now cleanly cancels dispatch at every phase rather than letting the call proceed with potentially truncated or invalid input.

Details:
The abort signal reason `"server-fallback-tombstone"` is checked at four points in the tool execution pipeline:
1. After input validation
2. After permission check
3. Before the tool call executes
4. After the call returns

In each case, a `"Tool dispatch was retracted by a server fallback; the input may be truncated."` result is returned, ensuring the transcript is consistent with what the server delivered.

Evidence: tombstone check (search for `"server-fallback-tombstone"`) — `bLH` at line ~263717; tombstone validation message (search for `"Tool dispatch was retracted by a server fallback"`)


## Improvements


### Updated model descriptions in the model picker

The human-readable descriptions for all models in the `/model` picker and settings UI have been refreshed to be more consistent and informative:

| Model | New description |
|-------|----------------|
| Fable | Most capable for your hardest and longest-running tasks |
| Opus | Best for everyday, complex tasks |
| Sonnet | Efficient for routine tasks |
| Haiku | Fastest for quick answers |

The `--model` flag help text now also lists `fable` as the first example alias.

Evidence: model description constants (search for `"Efficient for routine tasks"` and `"Best for everyday, complex tasks"`) — `RD6`, `J78`, `zxK` at line ~133191


### Warning when effort is set to "max"

When the `/effort` level is set to `max`, a dim hint is now shown below the effort selector: "May use excessive tokens resulting in long response times or overthinking. Use sparingly for the hardest tasks."

Evidence: effort UI warning (search for `"May use excessive tokens resulting in long response times or overthinking"`) — `JJ$` at line ~132435, displayed in `edf` at line ~642437


### Rate-limit `overageInUse` tracking from response headers

A new `overageInUse` boolean is now read from the `anthropic-ratelimit-unified-overage-in-use: true` response header and stored in rate-limit state. Registered listeners are notified when overage transitions to active. This enables more accurate display of overage status in the UI.

Evidence: header parsing (search for `"anthropic-ratelimit-unified-overage-in-use"`) — `Jl7` at line ~334876


### Cleaner safety-refusal message

The message shown when a model refuses a request due to cybersecurity or biology safety measures is simplified and made more informative:

Old: "has specific safety measures that flag messages with cybersecurity or biology topics (https://www.anthropic.com/legal/aup). This sometimes happens with safe, normal conversations."

New: "has safety measures that flag messages on most cybersecurity or biology topics (https://www.anthropic.com/legal/aup). They may flag safe, normal content as well. These measures let us bring you Mythos-level capability in other areas sooner, and we're working to refine them."

Evidence: updated refusal message (search for `"flag messages on most cybersecurity or biology topics"`) — `wI8` at line ~545435


### System prompt updated to include Fable 5

Claude Code's own system context about available models is updated:

Old: "The most recent Claude model family is Claude 4.X. Model IDs — Opus 4.8: '…'"

New: "The most recent Claude models are Fable 5 and the Claude 4.X family. Model IDs — Fable 5: '…', Opus 4.8: '…', Sonnet 4.6: '…', Haiku 4.5: '…'"

Evidence: system prompt model list (search for `"The most recent Claude models are Fable 5"`) — `ytf` at line ~676070


### Logout clears model-related server caches

When the user logs out, three additional cached fields are now cleared from local state:
- `additionalModelOptionsCache` — the list of available model options received from the server
- `additionalModelCostsCache` — cached per-model cost data
- `clientDataCache` — general client data

This prevents stale model lists from persisting across account switches.

Evidence: logout cache clear (search for `"additionalModelOptionsCache"`) — `_6$` at line ~402516


### Vertex AI setup message fix

The confirmation message shown after completing Vertex AI setup now correctly refers to Vertex AI and its credential refresh flow, rather than accidentally showing Bedrock SSO instructions:

New: "Vertex AI configuration saved to [path]. When your ADC token expires, run `gcloud auth application-default login` — Claude Code picks up refreshed credentials automatically."

Evidence: setup completion message (search for `"Vertex AI configuration saved"`) — `O04` at line ~416914


### Model validation now distinguishes "not found" errors

When a model name cannot be validated, the error result now includes a `notFound: true` field to let callers distinguish a missing model from other validation errors (permissions, network, etc.).

Evidence: model validation (search for `"notFound: !0"`) — `Kgf` at line ~637122


## Bug Fixes

- **`--effort` flag only forwarded when Fable 5 effort is also unlocked**: The effort flag passed to subprocess invocations now requires all three model effort settings (Opus 4.7, Opus 4.8, and Fable 5) to have been unlocked. For new Fable 5 users this means effort is withheld until the Fable 5 effort-intro prompt is dismissed, consistent with how Opus 4.7 and 4.8 were handled. (search for `"unpinFable5LaunchEffort"`)

- **Prompt history saving no longer gated on session persistence mode**: The check that previously skipped saving prompt history when session persistence was active has been removed. History is now saved consistently regardless of session mode, unless `CLAUDE_CODE_SKIP_PROMPT_HISTORY` is set. (search for `"CLAUDE_CODE_SKIP_PROMPT_HISTORY"`)

- **Usage-credit 429 errors not retried when overage is org-level disabled**: When a 429 contains "usage credits are required" or "extra usage is required" and the `anthropic-ratelimit-unified-overage-disabled-reason` header is `fetch_error` or `org_level_disabled_until`, the request is now treated as non-retryable. Previously these could be retried unnecessarily. (search for `"usage credits are required"` in retry logic)

- **Fable 5 context-aware compaction threshold**: The compaction trigger now correctly uses the 1M-token threshold for Fable 5 and Mythos 5, matching Opus 4.8 behavior. Previously only Opus 4.8 triggered the 1M threshold. (search for `"claude-fable-5"` in compaction logic — `Ssf` at line ~670106)

- **Tool abort tracking now returns `toolUseIds`**: The abort summary returned when concurrent tools are cancelled now includes the list of tool-use IDs that were aborted, enabling more precise tombstone-eviction by SDK consumers. (search for `"toolUseIds"` in abort return)


Generated with:
- tool: `harness-investigations@1d6cc84-dirty`
- provider: `claude`
- model: `claude-sonnet-4-6`
- primary diff: `archive/claude-code/changes/changes-v2.1.170-2.md` (filtered astdiff)
- string diff: `archive/claude-code/changes/string-diff-v2.1.170.txt`
