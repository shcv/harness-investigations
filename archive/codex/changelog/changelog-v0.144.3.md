# Changelog for version 0.144.3

## Summary

This release overhauls how Max and Ultra reasoning efforts are selected in the TUI, replacing silent keyboard-shortcut access with an explicit two-step "Advanced Reasoning" picker. It also fixes thread-resume behavior so that a saved thread's model and reasoning effort are restored by default rather than overridden by the current config, and ensures that mid-conversation settings changes are properly persisted to thread metadata.

The upstream release was tagged as a version-only bump with no pull-request notes, but the diff contains substantial changes across the TUI, thread-store, and app-server layers.


## New Features


### Advanced Reasoning Picker for Max and Ultra efforts

What: Max and Ultra reasoning efforts are now selected through a dedicated "Advanced Reasoning" popup rather than through the regular effort picker or keyboard shortcuts. This prevents accidental high-usage selections.

Details:
- The standard reasoning-effort popup (opened from `/model → [model]`) now shows "More reasoning…" as a final item whenever the model supports Max or Ultra, with the caption "Max and Ultra consume usage limits faster".
- Selecting "More reasoning…" opens a second-level "Advanced Reasoning" popup listing only Max and Ultra, each with a description ("For difficult problems when quality matters more than speed · higher usage" / "For demanding work using multiple agents · highest usage") and the warning "⚠ Consumes usage limits faster".
- The keyboard shortcut Alt+. (raise effort) stops silently at the boundary just below Max/Ultra and instead prints an info message: "Max and Ultra are available under /model → [model path] → More reasoning…"
- Lowering effort from Max or Ultra with Alt+, still works normally — you can exit advanced efforts without going through the picker.
- Ultra selected via the advanced picker uses the new `ApplyAdvancedReasoning` path, which applies Ultra to the active conversation without writing it as the persistent default for new sessions. The previous non-Ultra effort is kept as the default for new threads.
- Max selected via the advanced picker follows the regular `UpdateReasoningEffort` / `PersistModelSelection` path and becomes the persistent default.

Code references:
- `ChatWidget::open_advanced_reasoning_popup()` in `codex-rs/tui/src/chatwidget/model_popups.rs`
- `ChatWidget::is_advanced_reasoning_effort()` in `codex-rs/tui/src/chatwidget/model_popups.rs`
- `AppEvent::OpenAdvancedReasoningPopup` and `AppEvent::ApplyAdvancedReasoning` in `codex-rs/tui/src/app_event.rs`
- Reasoning-shortcut guard in `codex-rs/tui/src/chatwidget/reasoning_shortcuts.rs`
- `App::on_apply_advanced_reasoning()` in `codex-rs/tui/src/app/config_persistence.rs`


## Improvements


### Thread resume restores saved model settings by default

Previously, resuming a saved thread always forwarded the current config's model, provider, and reasoning effort as overrides, which could silently replace settings that were saved with the thread. Now the TUI detects whether model settings were explicitly supplied via a session flag (`--model`, `--model-provider`) or a named config profile, and only forwards those overrides if so.

When no explicit override is active, the resume request omits model, model_provider, and model_reasoning_effort entirely, letting the app-server restore the values that were saved with the thread.

Code references:
- `ResumeModelSettings` enum (`OverrideFromCurrentConfig` / `RestoreFromThread`) in `codex-rs/tui/src/app_server_session.rs`
- `resume_model_settings_for_overrides()` in `codex-rs/tui/src/app/config_persistence.rs`
- Updated `AppServerSession::resume_thread()` signature and `thread_resume_params_from_config()` in `codex-rs/tui/src/app_server_session.rs`


### Mid-conversation settings changes are persisted to thread metadata

When the app-server emits a `ThreadSettingsApplied` event (fired when model, provider, reasoning effort, cwd, or permission profile change mid-conversation), that event now updates the thread's persisted metadata immediately. This means the thread list and resume logic see the correct last-known settings even after an in-session model switch.

Code references:
- `apply_event_msg` for `EventMsg::ThreadSettingsApplied` in `codex-rs/state/src/extract.rs`
- `ThreadMetadataSync` handling of `RolloutItem::EventMsg(EventMsg::ThreadSettingsApplied(...))` in `codex-rs/thread-store/src/thread_metadata_sync.rs`
- `rollout_item_affects_thread_metadata` updated to include `ThreadSettingsApplied` in `codex-rs/state/src/extract.rs`


### `reasoning_effort` in thread metadata patches supports explicit clearing

`ThreadMetadataPatch.reasoning_effort` is now typed as `ClearableField<ReasoningEffort>` (i.e. `Option<Option<ReasoningEffort>>`), serialized with a custom `optional_option` serde helper. This distinguishes "no update to effort" (`None`) from "explicitly clear effort to absent" (`Some(None)`). Previously the field could only set an effort, never clear it.

Code references:
- `ThreadMetadataPatch::reasoning_effort` in `codex-rs/thread-store/src/types.rs`
- `apply_metadata_update` in `codex-rs/thread-store/src/local/update_thread_metadata.rs`


### Ultra threads propagate their effort to Plan mode

When resuming or switching to a thread that was running with Ultra reasoning effort, Plan mode now also starts at Ultra rather than falling back to the user's configured `plan_mode_reasoning_effort`. Switching away from that thread restores the configured Plan mode effort.

Code references:
- `ChatWidget::handle_thread_session` guard in `codex-rs/tui/src/chatwidget/session_flow.rs`
- `App::replay_thread_snapshot` plan-mode restoration in `codex-rs/tui/src/app/thread_routing.rs`


### Fork preserves active conversation effort (including Ultra)

Forking a thread now captures the model and reasoning effort currently shown in the chat widget (`current_model()` / `current_reasoning_effort()`) rather than reading from the static config. This means a conversation that was upgraded to Ultra via the advanced picker keeps Ultra in the fork.

Code references:
- `AppEvent::ForkCurrentSession` handler in `codex-rs/tui/src/app/event_dispatch.rs`


### Updating reasoning effort or plan-mode effort clears ephemeral Ultra cross-contamination

- When raising conversation effort to Ultra and then lowering it back, any ephemeral Ultra that was propagated to Plan mode (but not in the user's config) is also cleared.
- Symmetrically, when plan-mode effort is raised to Ultra and then lowered, any ephemeral Ultra propagated to the default mode is cleared.

Code references:
- `App::on_update_reasoning_effort()` and `App::on_update_plan_mode_reasoning_effort()` in `codex-rs/tui/src/app/config_persistence.rs`
- `AppEvent::UpdatePlanModeReasoningEffort` handler in `codex-rs/tui/src/app/event_dispatch.rs`


## Bug Fixes

- Thread resume no longer incorrectly applies the configured `model_reasoning_effort` when the saved thread had no reasoning effort recorded. The fix checks whether the resume request included an explicit effort override before forwarding `config.model_reasoning_effort`, and clears it when restoring from persisted metadata that has no effort set. (`has_model_resume_override()` and updated resume logic in `codex-rs/app-server/src/request_processors/thread_processor.rs`)

- `stored_thread_from_state` in `codex-rs/thread-store/src/in_memory.rs` now calls `.flatten()` when reading `metadata.reasoning_effort`, fixing a double-`Option` wrapping that could surface spurious `Some(None)` values.

- Resuming a thread with `RestoreFromThread` no longer forwards an implicit `service_tier` derived from feature flags like Fast Mode. Only an explicitly configured `service_tier` is forwarded. (`thread_resume_params_from_config` in `codex-rs/tui/src/app_server_session.rs`)


Generated with:
- tool: `harness-investigations@d5cccf8-dirty`
- provider: `claude`
- model: `claude-sonnet-4-6`
- primary diff: `archive/codex/diff/v0.144.3.diff` (raw diff)
- official release notes: `archive/codex/changes/release-notes-v0.144.3.md`
