# Changelog for version 0.142.3

## Official Release Highlights

Upstream describes this as a maintenance-only patch release with no user-facing changes since 0.142.2. The diff tells a different story: three new GPT-5.6 model variants are added to the Amazon Bedrock catalog, each with a new "max" reasoning effort level. These are genuine user-facing additions verified against the code.

## Additional Changes Beyond Official Notes

### New GPT-5.6 models on Amazon Bedrock (Sol, Terra, Luna)

What: Three new model variants — Sol, Terra, and Luna — are added to the Amazon Bedrock model catalog. Each is a GPT-5.6 variant accessible via Bedrock's Mantle endpoint and introduces a new "max" reasoning effort preset not available on existing Bedrock models.

Details:
- Bedrock model IDs: `openai.gpt-5.6-sol`, `openai.gpt-5.6-terra`, `openai.gpt-5.6-luna`
- Display names in the UI: Sol, Terra, Luna
- Context window: 272,000 tokens (same as the existing GPT-5.5 and GPT-5.4 Bedrock models)
- All three expose a custom reasoning effort level `max` ("Maximum reasoning depth for the hardest problems") that the prior Bedrock models do not advertise
- They inherit the GPT-5.5 base configuration and use the `gpt-5.5` OpenAI slug for API routing, but carry distinct Bedrock-side slugs and display names

Usage: Select any of the three variants by their Bedrock model ID when configuring the Amazon Bedrock provider:

```toml
[model_provider]
name = "amazon-bedrock"
model = "openai.gpt-5.6-sol"   # or openai.gpt-5.6-terra / openai.gpt-5.6-luna
```

Code references:
- `AMAZON_BEDROCK_GPT_5_6_SOL_MODEL_ID`, `AMAZON_BEDROCK_GPT_5_6_TERRA_MODEL_ID`, `AMAZON_BEDROCK_GPT_5_6_LUNA_MODEL_ID` in `codex-rs/model-provider-info/src/lib.rs`
- `gpt_5_6_bedrock_model()` and `static_model_catalog()` in `codex-rs/model-provider/src/amazon_bedrock/catalog.rs`
- `ReasoningEffort::Custom("max")` / `ReasoningEffortPreset` in the same file


Generated with:
- tool: `harness-investigations@0c752ef-dirty`
- provider: `claude`
- model: `claude-sonnet-4-6`
- primary diff: `archive/codex/diff/v0.142.3.diff` (raw diff)
- official release notes: `archive/codex/changes/release-notes-v0.142.3.md`
