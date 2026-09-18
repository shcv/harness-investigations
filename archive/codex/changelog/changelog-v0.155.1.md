# Changelog for version 0.155.1

## Official Release Highlights


### Bug fix: reasoning summaries are disabled by default for new local TUI sessions

What: New local interactive sessions no longer request detailed reasoning summaries automatically, preventing request rejection by providers that do not support them. This is the fix described in the [official release notes](https://github.com/openai/codex/releases/tag/rust-v0.155.1).

Usage:

Start a new interactive session normally; no configuration change is required:

```bash
codex
```

To explicitly request detailed summaries from a provider that supports them, set this existing option at the top level of `config.toml`:

```toml
model_reasoning_summary = "detailed"
```

Details:

- In **0.155.0**, new local TUI threads used `"detailed"` when `model_reasoning_summary` was unset. **0.155.1** changes that fallback to `"none"`.
- Explicit reasoning-summary settings remain respected. The configuration option itself is not new.
- Setting `[features].concurrent_reasoning_summaries = true` alone no longer causes an otherwise unconfigured new local session to request summaries. An explicit summary setting is also needed.
- The changed default applies to new threads using the TUI’s embedded app-server path; this patch does not establish a global default change for every Codex client or session type.

Code references:

- `new_thread_reasoning_overrides` in `codex-rs/tui/src/app_server_session.rs` changes the fallback from `ReasoningSummary::Detailed` to `ReasoningSummary::None`, while retaining explicit configuration.
- `thread_start_params_from_config` in the same file applies these overrides for `ThreadParamsMode::Embedded`.
- `ReasoningSummary` in `codex-rs/protocol/src/config_types.rs` defines the existing summary settings.

The complete **0.155.0 → 0.155.1** diff contains no additional substantive user-facing changes beyond this published fix.


Generated with:
- tool: `harness-investigations@a724abb-dirty`
- provider: `codex`
- model: `gpt-6-astra`
- reasoning effort: `medium`
- primary diff: `archive/codex/diff/v0.155.1.diff` (raw diff)
- official release notes: `archive/codex/changes/release-notes-v0.155.1.md`
