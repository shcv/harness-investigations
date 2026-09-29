# Changelog for version 0.159.1

## Release Status

> **Not yet released:** `rust-v0.159.1` is present in Git, but no published GitHub Release was found at sync time. This may be an intermediate development snapshot or a release prepared ahead of publication.


## Summary

Compared with 0.159.0, this snapshot adds GPT-6.1-Sol to the bundled model catalog and the existing Amazon Bedrock integrations. It also makes GPT-6.1-Sol the preferred catalog default, replacing GPT-6-Astra in the bundled OpenAI catalog and GPT-6-Sol in the standard Bedrock catalogs.

## Release Status

The source tag `rust-v0.159.1` exists, but no published GitHub Release was found when the sync ran. This changelog describes an intermediate/development snapshot; it does not establish that binaries or release assets were published.

## New Features


### GPT-6.1-Sol Model Selection

What: The bundled catalog now includes `gpt-6.1-sol`, which was absent from the 0.159.0 source tree.

Usage:

```bash
codex --model gpt-6.1-sol
```

To select the model and set reasoning effort in `config.toml`:

```toml
model = "gpt-6.1-sol"
model_reasoning_effort = "high"
```

Details:

- Appears as `GPT-6.1-Sol` in the model picker.
- Defaults to `low` reasoning effort and lists `low`, `medium`, `high`, `xhigh`, `max`, and `ultra` as supported levels.
- Declares text and image input support, including original-detail images.
- Uses a catalog context window of 272,000 tokens, with a separate maximum of 872,000 tokens. The larger maximum is not the default context window.
- Includes a Fast service-tier option in its OpenAI catalog metadata.
- The catalog entry is not behind a new experimental flag. Actual access remains dependent on the provider and account’s available models.

Code references:

- The `gpt-6.1-sol` entry, including `supported_reasoning_levels`, `input_modalities`, and `service_tiers`, in `codex-rs/models-manager/models.json`.
- `SharedCliOptions::model` in `codex-rs/utils/cli/src/shared_options.rs`.
- `model_reasoning_effort` in `codex-rs/core/src/config/mod.rs`.


### GPT-6.1-Sol on Amazon Bedrock

What: The existing Bedrock providers now include GPT-6.1-Sol in their static model catalogs.

Usage:

For the Bedrock Mantle provider, with AWS authentication already configured:

```bash
codex -c 'model_provider="amazon-bedrock"' \
  --model openai.gpt-6.1-sol
```

For Bedrock Runtime with global cross-region routing:

```bash
codex -c 'model_provider="amazon-bedrock-runtime"' \
  --model global.openai.gpt-6.1-sol
```

Details:

- Bedrock Runtime also includes `us.openai.gpt-6.1-sol` for US cross-region routing.
- Existing Bedrock normalization applies to the new model: Ultra reasoning and Fast service tiers are unavailable.
- Mantle uses text-only web search; the Runtime catalog disables web search.
- Bedrock uses the existing V1 multi-agent protocol for this model.
- The separate GovCloud catalog remains limited to its existing models and does not gain GPT-6.1-Sol.

Code references:

- `AMAZON_BEDROCK_GPT_6_1_SOL_MODEL_ID` in `codex-rs/model-provider-info/src/lib.rs`.
- `static_model_catalog`, `bedrock_model`, `normalize_bedrock_catalog`, and `static_gov_model_catalog` in `codex-rs/model-provider/src/amazon_bedrock/catalog.rs`.
- `static_runtime_model_catalog` and `ROUTING_VARIANTS` in `codex-rs/model-provider/src/amazon_bedrock/runtime_catalog.rs`.

## Improvements


### Default Model Selection Prefers GPT-6.1-Sol

When model selection uses the bundled catalog, GPT-6.1-Sol now ranks ahead of GPT-6-Astra. The standard Bedrock catalog likewise prefers `openai.gpt-6.1-sol`, and Bedrock Runtime prefers `global.openai.gpt-6.1-sol`.

This affects sessions without an explicit model selection. It also changes the fallback target for Bedrock requests when provider-model fallback is enabled and the requested model is unavailable. Supported explicit selections remain preserved; remotely supplied OpenAI catalogs can determine a different default.

To retain the previous bundled OpenAI default explicitly:

```toml
model = "gpt-6-astra"
```

Existing GPT-6-Sol and older models remain in the catalogs. Their picker ordering moves down, and GPT-6-Sol’s description now identifies it as the previous-generation workhorse.

Code references:

- Model `priority` and `description` fields in `codex-rs/models-manager/models.json`.
- `ModelsManager::build_available_models`, `ModelsManager::get_default_model`, and `StaticModelsManager::get_default_model` in `codex-rs/models-manager/src/manager.rs`.
- `static_model_catalog` in `codex-rs/model-provider/src/amazon_bedrock/catalog.rs`.
- `static_runtime_model_catalog` in `codex-rs/model-provider/src/amazon_bedrock/runtime_catalog.rs`.


Generated with:
- tool: `harness-investigations@66d60f9-dirty`
- provider: `codex`
- model: `gpt-6-astra`
- reasoning effort: `medium`
- primary diff: `archive/codex/diff/v0.159.1.diff` (raw diff)
- release status: `unreleased Git tag; no published GitHub Release found at sync time`
