# Changelog for version 2.1.197

## Summary

This release adds Claude Sonnet 5 (`claude-sonnet-5`) as the new default Sonnet model, replacing Sonnet 4.6. Sonnet 5 ships with a 1M context window, a January 2026 knowledge cutoff, and a $2/$10/MTok launch promo price — displayed directly in the model picker alongside the regular list price. Sonnet 4.6 remains selectable as a "Previous Sonnet version" option.


## New Features


### Claude Sonnet 5 — New Default Model

What: Claude Sonnet 5 (`claude-sonnet-5`) is now the default Sonnet model for Claude Code, with a 1M context window, extended output limits, and native support across all third-party providers.

Details:
- Model ID: `claude-sonnet-5`
- Knowledge cutoff: January 2026
- Context window: 1M tokens (native — no beta header required)
- Max output tokens: 64,000; max thinking tokens: 128,000
- Capabilities: effort control (high/max/xhigh), adaptive thinking, mid-conversation system prompt updates, context management
- Available on: first-party API, Amazon Bedrock (`us.anthropic.claude-sonnet-5`), Google Vertex (`claude-sonnet-5`), Azure AI Foundry, Anthropic Gateway, and AWS Mantle
- Native 1M context is supported natively on Bedrock, Vertex, and Foundry (no `supports_1m_beta` workaround needed)
- Eager input streaming enabled on Bedrock and Vertex for faster time-to-first-token

Evidence: Model registry entry — search for `"claude-sonnet-5"` in the provider_ids block containing `"us.anthropic.claude-sonnet-5"` and `"native_1m_3p"`.


### Promotional Pricing Display in Model Picker

What: The model picker now shows the Sonnet 5 launch promo price ($2/$10 per MTok) alongside the expiry date, with the regular list price ($3/$15) available for rich pickers to display struck-through.

Details:
- Sonnet 5 description renders as: `Sonnet 5 · $2/$10 per Mtok · promo through Jun 29`
- The 1M-context variant shows: `Sonnet 5 for long sessions · $2/$10 per Mtok · promo through Jun 29`
- A new `promoListPrice` field on model info objects carries the list price (e.g., `"$3/$15"`) so rich UIs (e.g., the VSCode extension) can render it struck-through before the promo price in the description
- When no promo is active, the field is absent and the description reverts to the standard pricing line

Evidence: Model schema `promoListPrice` field — search for `"@internal List price (e.g. \`$3/$15\`)"`. Pricing display logic — search for `"$2/$10 per Mtok"`.


### Model Alias Resolution Field

What: Model info objects now include a `resolvedModel` field that exposes the canonical wire model ID that an alias resolves to, enabling hosts to match a persisted explicit ID against the alias row that covers it.

Details:
- Example: a row with `value: "sonnet"` now also carries `resolvedModel: "claude-sonnet-5"`
- Lets extension hosts and API consumers programmatically detect when a saved explicit ID (e.g., `"claude-sonnet-4-6"`) is superseded by the current alias without special-casing model names
- The alias matching logic was also upgraded: the new `z4t` comparison function handles cross-version alias equivalence (e.g., recognising that `"sonnet"` and `"claude-sonnet-5"` are the same selection)

Evidence: Schema description — search for `"Canonical wire model id this row's \`value\` resolves to"`. Matching logic — search for `"Lets hosts match a persisted explicit id"`.


## Improvements


### Sonnet 4.6 Preserved as "Previous Sonnet Version" Option

The model picker retains Sonnet 4.6 as a selectable option, now labeled "Sonnet 4.6 · Previous Sonnet version" with description "Sonnet 4.6 - previous Sonnet version". Users who want to pin to the prior-generation Sonnet can still do so explicitly without needing to type the full model ID.

Evidence: New `Wua()` builder function — search for `"Sonnet 4.6 \xB7 Previous Sonnet version"`.


### Sonnet 5 1M Context Window Option

The 1M-context variant of Sonnet 5 is exposed in the model picker as "Sonnet 5 (1M context)" with the description "Sonnet 5 for long sessions · $2/$10 per Mtok · promo through [date]". For third-party API users (Bedrock, Vertex, Foundry), the 1M context window is native — no separate beta enablement is required, unlike the Sonnet 4.6 1M variant.

Evidence: New `Nlo()` builder — search for `"Sonnet 5 with 1M context window - for long sessions with large codebases"`. 3P support check — search for `"native_1m_3p"`.


### Hook Model Examples Updated to Sonnet 5

The `.describe()` text for the `model` field in agent and prompt hooks now references `"claude-sonnet-5"` as the example model ID instead of `"claude-sonnet-4-6"`.

Old: `Model to use for this agent hook (e.g., "claude-sonnet-4-6"). If not specified, uses Haiku.`
New: `Model to use for this agent hook (e.g., "claude-sonnet-5"). If not specified, uses Haiku.`

Evidence: Search for `"Model to use for this agent hook (e.g., \"claude-sonnet-5\")"`.


### Agent Capability Tier Descriptions Updated

The strings describing which models support which agent/tool capability tiers now include Sonnet 5:

- Tier 1 (highest): was "Fable 5, Opus 4.7+" → now "Fable 5, Opus 4.7+, Sonnet 5"
- Tier 2: was "Fable 5, Opus 4.6+, Sonnet 4.6" → now "Fable 5, Opus 4.6+, Sonnet 4.6+"

The "+" suffix on Sonnet 4.6+ indicates Sonnet 5 and later also qualify for tier 2.

Evidence: Search for `"Fable 5, Opus 4.7+, Sonnet 5"` and `"Fable 5, Opus 4.6+, Sonnet 4.6+"`.


### Model Listing Description Updated for Claude 5 Family

The text shown when listing available models was updated to reflect the current model landscape:

Old: "The most recent Claude models are Fable 5 and the Claude 4.X family. Model IDs —"
New: "The most recent Claude models are the Claude 5 family, Opus 4.8, and Haiku 4.5. Model IDs —"

Evidence: Search for `"The most recent Claude models are the Claude 5 family"`.


### 1M Context Unavailability Message Simplified

The error shown when 1M context is unavailable for an account was simplified to be model-version-agnostic:

Old: "Sonnet 4.6 with 1M context is not available for your account. Learn more: …"
New: "Sonnet with 1M context is not available for your account. Learn more: …"

Evidence: Search for `"Sonnet with 1M context is not available for your account"`.


### Bedrock Configuration Validation Improved

The function that builds Bedrock fallback model IDs for third-party providers now throws an explicit error if a default model configuration has `bedrock: null` — a misconfiguration that previously would silently fail. The error message is:

> A DEFAULT_3P_*_KEY points at a model config with bedrock: null — Bedrock setup has no fallback id for that tier

Evidence: Search for `"A DEFAULT_3P_*_KEY points at a model config with bedrock: null"`.


Generated with:
- tool: `harness-investigations@03136fb-dirty`
- provider: `claude`
- model: `claude-sonnet-4-6`
- primary diff: `archive/claude-code/changes/changes-v2.1.197.md` (filtered astdiff)
- string diff: `archive/claude-code/changes/string-diff-v2.1.197.txt`
