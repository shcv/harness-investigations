# Changelog for version 0.146.1

## Summary

This patch makes interactive Codex safer when selecting cataloged cyber-specialty models, with safer permission defaults and clearer terminal warnings. It also extends the app-server model catalog so client authors can identify a model’s specialty.

## Official Release Highlights

### Safer cyber-model approval defaults

What: Selecting a model marked as `cyber` now applies safer thread permission settings when policy allows it: the Workspace profile, `Ask for approval`, and—when available—`Approve for me` automatic review.

Usage:

```text
In interactive Codex, select a model whose catalog entry has modelSpecialty: "cyber".
```

Details:

- The change applies only when the Workspace permission profile and the required approval settings are allowed by the active configuration.
- If automatic review is unavailable or disallowed, Codex falls back to user-reviewed approvals rather than overriding configuration requirements.
- When Codex successfully changes the active thread to automatic review, the terminal shows: `Cyber models default to "Approve for me" for safety reasons.`
- The Full Access confirmation dialog now gives cyber-model-specific guidance, recommending `Approve for me` when available, or manual approval otherwise.

Code references:

- `App::active_thread_model_setting_update_params` and `App::sync_active_thread_model_setting` in `codex-rs/tui/src/app/thread_settings.rs`
- `cyber_model_approval_reviewer` and `auto_review_available` in `codex-rs/tui/src/chatwidget/permissions_menu.rs`
- `AppEvent::CyberModelAutoReviewNotice` in `codex-rs/tui/src/app_event.rs`
- Cyber-model Full Access warning in `codex-rs/tui/src/chatwidget/permission_popups.rs`

## Additional Changes Beyond Official Notes

The app-server’s `model/list` response now exposes an optional model-specialty classification, allowing API clients to recognize cataloged specialties such as `cyber`.

## New Features

### Model specialty metadata in the app-server catalog

What: The `model/list` protocol response now includes optional `modelSpecialty` metadata for each model.

Usage:

```json
{"method":"model/list","params":{"includeHidden":false}}
```

A returned model can now include:

```json
{
  "model": "example-cyber-model",
  "modelSpecialty": "cyber"
}
```

Details:

- `modelSpecialty` is optional and may be `null`; clients should continue to handle models without a specialty.
- Codex passes this metadata from remote model information through its internal `ModelInfo` and `ModelPreset` types into the v2 app-server response.
- The TUI uses the `cyber` value to apply the safer model-selection behavior described above.

Code references:

- `Model::model_specialty` in `codex-rs/app-server-protocol/src/protocol/v2/model.rs`
- `ModelPreset::model_specialty` and `ModelInfo::model_specialty` in `codex-rs/protocol/src/openai_models.rs`
- `model_from_preset` in `codex-rs/app-server/src/models.rs`
- Updated schema `codex-rs/app-server-protocol/schema/json/v2/ModelListResponse.json`
- Updated TypeScript binding `codex-rs/app-server-protocol/schema/typescript/v2/Model.ts`

## Improvements

### Preserve chosen permissions when changing reasoning effort

Changing reasoning effort for the currently selected model now updates only the reasoning setting instead of reapplying model-selection defaults. This preserves an explicitly selected permission profile and approval reviewer, including when advanced reasoning selects a collaboration-mode model.

Code references: `AppEvent::ApplyAdvancedReasoning` handling in `codex-rs/tui/src/app/event_dispatch.rs` and `App::active_thread_reasoning_setting_update_params` use in `codex-rs/tui/src/app/thread_settings.rs`

## Notes

App-server clients that validate `model/list` responses against a fixed schema should update to accept the optional nullable `modelSpecialty` field. No CLI or configuration-file migration is required.


Generated with:
- tool: `harness-investigations@9bfe3ff-dirty`
- provider: `codex`
- model: `gpt-5.6-terra`
- reasoning effort: `medium`
- primary diff: `archive/codex/diff/v0.146.1.diff` (raw diff)
- official release notes: `archive/codex/changes/release-notes-v0.146.1.md`
