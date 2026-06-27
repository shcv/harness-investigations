# Changelog for version 2.1.190

## Summary

This release overhauls how Fable 5 (Claude's highest-capability model tier) communicates rate limits and credit requirements. A new `seven_day_overage_included` limit type tracks a weekly Fable 5 allotment included with certain plans, with cleaner messages when that allotment runs out. Error messages for non-admin users hitting Fable 5 limits are simplified throughout, and the model picker now shows a concise "Requires usage credits" label. The usage data API gains a `model_scoped` field for per-model weekly windows.


## Improvements


### Fable 5 Weekly Allotment Limit Handling

Plans that include a weekly Fable 5 allotment now have a dedicated rate limit type (`seven_day_overage_included`). When you exhaust that allotment, Claude Code shows "You've reached your Fable 5 limit" and offers to continue on paid usage credits rather than treating it the same as running out of purchased credits from the start.

Previously, the Fable 5 limit dialog showed a generic message and pointed to `/usage-credits` regardless of how the limit was reached. Now the prompt distinguishes two cases:

- Hit the weekly included allotment → "You've used your included Fable 5 usage for this week. Continuing on Fable 5 uses usage credits"
- No credits configured at all → "Fable 5 runs on usage credits"

The server communicates this limit via the `anthropic-ratelimit-unified-7d_oi-utilization` header.

Evidence: New limit type (search for `"seven_day_overage_included"`) mapped to display label `"Fable 5 limit"`


### Simplified Fable 5 Error Messages for Non-Admin Users

Rate limit error messages shown to users without admin access are now shorter and more actionable. The old messages directed non-admins to ask their admin to make changes — which they cannot do — and now those cases simply suggest switching models.

Old messages (removed):
- "You've reached your Fable 5 limit. Ask your admin to turn on usage credits to continue using Fable 5. /model to switch models."
- "You've hit your monthly spend limit. Ask your admin to raise it to keep using Fable 5 or switch models to continue this chat."

New messages for non-admin users:
- `"You've reached your Fable 5 limit. /model to switch models."`
- `"You've hit your monthly spend limit. /model to switch models."`

Users who can purchase credits still get the `/usage-credits` call to action.

Evidence: Updated error message generator (search for `"You've hit your monthly spend limit. /model to switch models."`)


### Model Picker: Fable 5 Label Simplified

The descriptor shown next to Fable 5 in the `/model` picker is now a single consistent label: `"· Requires usage credits"`. The previous version showed three different strings depending on account state: "Draws from usage credits", "Uses your limits ~2× faster than Opus", or "Included with your plan until [date]". The date-based "Included with your plan until..." message and the speed-comparison note are removed.

This applies when you are authenticated, not overaged, and on a plan where Fable 5 requires purchased credits.

Evidence: New description string (search for `"\xB7 Requires usage credits"` — the `\xB7` is the middle dot separator)


### Fable 5 Dialog Title Now Context-Sensitive

The title of the Fable 5 upgrade dialog changes based on when and why it appears:

- During a session, after hitting the weekly allotment: **"You've reached your Fable 5 limit"**
- During a session, for general credits upgrade: "Fable 5 now uses usage credits"
- From the model picker: "Switch to Fable 5?"

Previously the mid-session title was always "Fable 5 now uses usage credits" regardless of whether the user hit a hard limit.

Evidence: Dialog title logic (search for `"You've reached your Fable 5 limit"`)


### Usage API: Per-Model Weekly Windows in `model_scoped` Field

The programmatic usage report (used by integrations reading Claude Code's status) now includes a `model_scoped` array when the server provides per-model limit windows. Each entry contains:

- `display_name` — server-supplied label for the model bucket (e.g. `"Fable"`)
- `utilization` — utilization ratio, or null
- `resets_at` — ISO 8601 reset timestamp, or null

This field is additive: it only appears when the server emits per-model limits data. The field is documented with: "Per-model weekly windows from the server limits[] array, filtered by the overage-included-models allowlist."

Evidence: Schema addition (search for `"Per-model weekly windows from the server limits[] array"`)


### Enterprise Accounts Default to Credits-Only Fable 5

A new server-controlled flag `tengu_saffron_credits_only_tiers` specifies which subscription tiers always require purchased usage credits for Fable 5, bypassing the included-allotment flow. The default value is `["enterprise"]`, meaning enterprise accounts are treated as credits-only by default. This can be adjusted server-side without a client update.

A companion flag `tengu_saffron_picker_dim` controls whether Fable 5 models are shown as dimmed in the model picker for credits-only accounts that do not have credits configured.

Evidence: New feature flags (search for `"tengu_saffron_credits_only_tiers"`)


### Announcement System: Model-Targeted Startup Notices

Server-configured startup announcements now support a `requiresModel` field. When set, an announcement is only shown to users whose current model matches the specified value. Announcements that do not match the active model are filtered out of the display queue.

This allows Anthropic to send targeted announcements — for example, a notice relevant only to Fable 5 users — without surfacing it to everyone.

Evidence: New schema field (search for `"requiresModel"`) and filter function that checks `Pa(e.requiresModel)`


### Credits Purchase: State Refreshes After Buy

After successfully purchasing usage credits, Claude Code now immediately refreshes the overage-included state for the session. Previously, a purchase was confirmed but the in-session model availability state was not updated until the next API call. This affects users who purchase credits mid-session to continue using Fable 5.

Evidence: `g4a()` call added to the `buy_success` handler (search for `"Added "` — the success confirmation message that precedes the refresh)


## Bug Fixes

- Prepaid credit balance fetch no longer crashes when the server returns a response without a numeric `amount` field; it now logs `"not_supported"` and returns null cleanly (search for `"api_prepaid_balance_fetch"`)

- The usage credits eligibility check (`yae()`) now respects an explicit `enabled: false` field from the server config. Previously, an account with `enabled: false` could still be considered eligible due to other flags. (search for `"overageConsentRequired"` in the config schema — the `enabled` boolean is the new guard)

- `credits_required` API errors now surface the `disabled_reason` field from the error body as `overageDisabledReason`, making it available to the error message generator for more accurate messaging (search for `"disabled_reason"`)


Generated with:
- tool: `harness-investigations@0c752ef-dirty`
- provider: `claude`
- model: `claude-sonnet-4-6`
- primary diff: `archive/claude-code/changes/changes-v2.1.190.md` (filtered astdiff)
- string diff: `archive/claude-code/changes/string-diff-v2.1.190.txt`
