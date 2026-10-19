# Changelog for version 2.1.170

## Official Release Highlights

### Claude Fable 5

The upstream release introduces Claude Fable 5, described as a Mythos-class
model with capabilities beyond Anthropic's previously generally available
models.

Usage:

```bash
claude --model fable
```

You can also select Fable from `/model` when it is available for your account
and provider.

Details:

- Adds the `fable` and `fable[1m]` aliases to model-selection surfaces,
  including agent model overrides.
- The existing `best` alias can now resolve to Fable when account-provided model
  options make it available; otherwise it retains its previous fallback.
- Adds provider configuration through `ANTHROPIC_DEFAULT_FABLE_MODEL`, with
  optional name, description, and supported-capabilities variables.
- Bedrock and Vertex setup gain Fable model verification and pinning. Vertex
  also recognizes `VERTEX_REGION_CLAUDE_FABLE_5`.
- Adds Fable-specific effort, context, caching, capacity, and usage-credit
  handling.

Installing this release does not by itself establish access for every account.
The CLI checks server-provided model options and reports when Fable is not
available.

Evidence: the upstream release announcement and the additions anchored by
`"claude-fable-5"`, `"ANTHROPIC_DEFAULT_FABLE_MODEL"`, and
`"VERTEX_REGION_CLAUDE_FABLE_5"`. These are absent from version 2.1.169.


### Transcript and resume persistence in inherited environments

Sessions launched from the VS Code integrated terminal, or another shell that
inherited Claude Code environment variables, now save their transcript and
appear in `--resume`.

The old implementation treated an interactive process with inherited
`CLAUDECODE` and `CLAUDE_CODE_SESSION_ID` values as nested and suppressed prompt
history, transcript persistence, and session registration. Version 2.1.170
removes that shared suppression predicate from all three paths. Explicit history
and persistence controls still apply.

Evidence: the removed predicate was `HkH()` in `pretty-v2.1.169.js`; its callers
in prompt-history saving, persistence selection, and session registration no
longer invoke it in `pretty-v2.1.170.js`. The associated
`CLAUDE_CODE_FORCE_SESSION_PERSISTENCE` override is also removed.

Upstream notes:
https://github.com/anthropics/claude-code/releases/tag/v2.1.170

## Additional Changes Beyond Official Notes

### Explicit Mythos 5 model-ID handling

The CLI now recognizes `claude-mythos-5` and applies model-specific display,
context, reasoning, cost, and prompt-cache behavior. The source does not add a
`mythos` shorthand alias or establish universal availability. Automatic
refusal-fallback target selection explicitly excludes Mythos.

Usage where a provider exposes the model:

```bash
claude --model claude-mythos-5
```

Evidence: compare the additions anchored by `"claude-mythos-5"`,
`"Mythos 5"`, and `"claude-mythos-"` with version 2.1.169.


### Per-family prompt-cache controls

Prompt caching can now be disabled independently for Fable and Mythos requests:

```bash
DISABLE_PROMPT_CACHING_FABLE=1 claude --model fable
DISABLE_PROMPT_CACHING_MYTHOS=1 claude --model claude-mythos-5
```

The Fable check also recognizes a provider model pinned through
`ANTHROPIC_DEFAULT_FABLE_MODEL`.


### Refusal fallback no longer requires its rollout gate

The existing refusal-fallback workflow no longer depends on the default-off
`tengu_loggia_carousel` gate. The `switchModelsOnFlag` setting and
`CLAUDE_CODE_DISABLE_REFUSAL_FALLBACK` environment override still apply, as do
fallback-model availability and dialog-support checks.

Fable and custom Fable model IDs can fall back to an appropriate Opus model.
Third-party providers receive configuration guidance when the required Fable
and Opus pairing is missing.

Evidence: version 2.1.169's eligibility function returns the rollout-gate value;
version 2.1.170's equivalent returns only the inverse of
`CLAUDE_CODE_DISABLE_REFUSAL_FALLBACK`.


### Exported refusal-fallback event schema

The exported system-event union now formally includes
`model_refusal_fallback`, with direction, original and fallback model, request
ID, API refusal category and explanation, and retracted message UUIDs.

This event was already emitted at runtime in version 2.1.169. The change in
2.1.170 is schema exposure and richer metadata, not the introduction of a new
runtime event. Consumers can use `retracted_message_uuids` as an idempotent
transcript-eviction signal.


### Model selection and usage feedback

- The model picker deduplicates equivalent entries, moves disabled choices
  after selectable choices, and shows server-provided explanations.
- Missing Fable availability triggers a server probe before the CLI reports it
  unavailable; `notFound` is now distinguished from other model-validation
  failures.
- The effort selector warns that `max` can use excessive tokens and produce
  long response times or overthinking.
- Rate-limit state records the
  `anthropic-ratelimit-unified-overage-in-use` response header and notifies
  listeners when overage becomes active.
- Logout clears cached model choices, model costs, and client data to avoid
  carrying account-specific state into another login.

## Bug Fixes

- **Retracted tool calls stop consistently during server fallback.** Tool
  dispatch checks for the `server-fallback-tombstone` abort after input
  validation, during permission handling, before execution, and after an
  in-flight call returns. It removes affected tool IDs from the active display
  and returns a controlled cancellation result.

- **Plugins from `--add-dir` participate in early startup loading.** Additional
  directories are registered before the early plugin load, so their plugin and
  marketplace settings are visible to that pass.

- **Credit-required 429s avoid futile retries.** A response containing
  `"usage credits are required"` or `"extra usage is required"` is treated as
  non-retryable unless the overage-disabled reason is `fetch_error` or
  `org_level_disabled_until`, which continue through the ordinary retry logic.

- **Vertex setup reports the correct provider.** Its completion telemetry and
  confirmation text now refer to Vertex AI and the ADC refresh command instead
  of Bedrock and AWS SSO.

- **Native long-context models keep more Stop-hook transcript.** Transcript
  budgeting now recognizes native extended-context models in addition to an
  explicit `[1m]` suffix.

## In Development

### Task-continuity guidance [In Development]

New model instructions describe continuing agreed work without repeatedly
requesting confirmation for ordinary in-scope steps. The text retains approval
boundaries for irreversible or shared-system actions.

The prompt content is present but unreachable in this build: both insertion and
generation depend on a model predicate that returns false. Version 2.1.169
already had the insertion point, but its content function returned `null`.

---

Generated with:
- tool: `harness-investigations@bcd9fc0-dirty`
- provider: `codex`
- model: `gpt-6-astra`
- reasoning effort: `medium`
- primary diff: `archive/claude-code/changes/changes-v2.1.170.md` (filtered astdiff)
- string diff: `archive/claude-code/changes/string-diff-v2.1.170.txt`
- official release notes: `https://github.com/anthropics/claude-code/releases/tag/v2.1.170`
- review: `source-checked correction on 2026-09-13`
