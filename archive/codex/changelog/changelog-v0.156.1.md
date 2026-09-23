# Changelog for version 0.156.1

## Release Status

> **Not yet released:** `rust-v0.156.1` is present in Git, but no published GitHub Release was found at sync time. This may be an intermediate development snapshot or a release prepared ahead of publication.


## Summary

Compared with 0.156.0, this snapshot adds bundled catalog support for GPT-6 Sol and GPT-6 Luna, introduces upgrade suggestions for several older models, and redirects the lower-usage model suggestion to GPT-6 Luna. Model-picker descriptions also distinguish the older GPT-5 models more clearly.

## Release Status

The source tag `rust-v0.156.1` exists, but no published GitHub Release was found when the sync ran. This changelog describes an intermediate development snapshot; it does not establish publication of binaries or release assets.

## New Features


### GPT-6 Sol and GPT-6 Luna model entries

What: The bundled model catalog now includes `gpt-6-sol` for coding and everyday work and `gpt-6-luna` for easier tasks.

Usage:

```bash
codex --model gpt-6-sol
codex --model gpt-6-luna
```

You can also select an available model and its reasoning effort through `/model`.

Details:

- Both model identifiers are absent from the 0.156.0 source and present in 0.156.1.
- Both entries default to `medium` reasoning. Sol lists `low`, `medium`, `high`, `xhigh`, `max`, and `ultra`; Luna lists the same levels through `max`.
- Both advertise text and image input, a 272,000-token context window, and an 872,000-token maximum context window. The maximum is catalog metadata, not the default allocation.
- Both are listed as visible and API-supported, with `priority` as their default service tier.
- The bundled picker orders Astra first, followed by Sol and Luna. Adding these entries does not replace Astra as the bundled default.
- These are wired catalog entries, not experimental stubs. Actual availability still depends on the provider and account’s active catalog; an authoritative remote catalog can replace the bundled list.

Code references:

- `gpt-6-sol` and `gpt-6-luna` entries in `codex-rs/models-manager/models.json`.
- `bundled_models_response` in `codex-rs/models-manager/src/lib.rs`.
- `ModelsManager::build_available_models` and `OpenAiModelsManager::apply_remote_models` in `codex-rs/models-manager/src/manager.rs`.

## Improvements


### Upgrade prompts point older selections toward GPT-6

The existing startup migration flow gains these catalog mappings:

| Selected model | Suggested replacement | Change from 0.156.0 |
|---|---|---|
| `gpt-5.6-sol` | `gpt-6-sol` | Added upgrade suggestion |
| `gpt-5.6-terra` | `gpt-6-sol` | Added upgrade suggestion |
| `gpt-5.6-luna` | `gpt-6-luna` | Added upgrade suggestion |
| `gpt-5.5` | `gpt-6-sol` | Added upgrade suggestion |
| `gpt-5.4` | `gpt-6-sol` | Previously targeted GPT-5.6 Terra |
| `gpt-5.4-mini` | `gpt-6-luna` | Previously targeted GPT-5.6 Luna |

Usage: Accept the startup upgrade prompt when offered, or select the replacement through `/model`.

The GPT-5.5 and GPT-5.6 entries remain in the catalog, and their new upgrade metadata specifies no retirement date. GPT-5.4’s existing retirement metadata remains unchanged.

Prompts require the replacement to be visible in the active catalog. Accepting uses the existing persistence flow to save the replacement and its default reasoning effort, which is `medium` for both new models.

Code references: `upgrade.model`, `migration_markdown`, and `retirement_at` in `codex-rs/models-manager/models.json`; `model_upgrade_for_migration`, `should_show_model_migration_prompt`, and `apply_accepted_model_migration` in `codex-rs/tui/src/app/startup_prompts.rs`.


### Lower-usage suggestions now target GPT-6 Luna

The existing “Approaching rate limits” prompt now offers `gpt-6-luna` instead of `gpt-5.6-luna`, provided the model is visible in the active catalog.

Usage: Choose “Switch to gpt-6-luna” when prompted. The existing options to keep the current model or hide future switching reminders remain available.

The Reserve-only `/model` picker also falls back to GPT-6 Luna’s presentation and supported reasoning efforts when it cannot resolve the server-specified normal model. This changes fallback metadata; Reserve routing remains `gpt-reserve`.

Code references: `LUNA_MODEL` in `codex-rs/tui/src/model_catalog.rs`; `NUDGE_MODEL_SLUG`, `lower_cost_preset`, and `open_rate_limit_switch_prompt` in `codex-rs/tui/src/chatwidget/rate_limits.rs`; `open_luna_reserve_model_popup` in `codex-rs/tui/src/chatwidget/luna_reserve_model.rs`.


### Clearer model-picker descriptions

The catalog now describes GPT-5.6 Sol, Terra, and Luna as older models and GPT-5.5 as a legacy coding model. Astra’s description becomes “Frontier intelligence for the most demanding work,” helping distinguish its intended role from the new Sol and Luna entries.

Usage: Open `/model` to compare the descriptions supplied by the active catalog.

Code references: `description` fields for `gpt-6-astra`, `gpt-5.6-sol`, `gpt-5.6-terra`, `gpt-5.6-luna`, and `gpt-5.5` in `codex-rs/models-manager/models.json`.


Generated with:
- tool: `harness-investigations@11dfc40-dirty`
- provider: `codex`
- model: `gpt-6-astra`
- reasoning effort: `medium`
- primary diff: `archive/codex/diff/v0.156.1.diff` (raw diff)
- release status: `unreleased Git tag; no published GitHub Release found at sync time`
