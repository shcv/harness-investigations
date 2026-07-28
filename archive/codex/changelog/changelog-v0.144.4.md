# Changelog for version 0.144.4

## Official Release Highlights

The upstream release notes classify this as a chores-only patch: "No user-facing changes in this patch release." The diff confirms this — all substantive code changes are internal to the auto-review guardian infrastructure.

## Additional Changes Beyond Official Notes

The diff is small (529 lines including test updates) and focused on a single internal subsystem: how the auto-review guardian session obtains its policy instructions.


### Auto-review guardian reads policy from model catalog

What: When Codex runs an auto-review guardian session and no `guardian_policy_config` has been set in user config, the guardian now reads a policy string from the model catalog's new `auto_review.policy` field rather than always falling back to a hardcoded default prompt.

Details:
- `build_guardian_review_session_config` in `codex-rs/core/src/guardian/review_session.rs` gains a new `model_messages: Option<&ModelMessages>` parameter. The caller (`guardian_review_session_config` in `review.rs`) resolves the guardian model's catalog entry before calling it, passing the entry's `model_messages` along.
- The priority order for the guardian's base instructions is: user-configured `guardian_policy_config` → catalog-provided `auto_review.policy` → built-in default prompt. User config always wins.
- The `AutoReviewMessages` struct (`policy: Option<String>`) and the `auto_review: Option<AutoReviewMessages>` field on `ModelMessages` are new in `codex-rs/protocol/src/openai_models.rs`. This extends the existing model catalog protocol to let server-side catalog entries carry auto-review policy text alongside per-model instructions and approval messages.
- The model catalog API drives this: if the catalog entry for `codex-auto-review` includes an `auto_review.policy`, that policy is silently used. Most users will not notice any change in behavior unless the server begins returning this field.

Code references:
- New `AutoReviewMessages` struct in `codex-rs/protocol/src/openai_models.rs`
- New `auto_review: Option<AutoReviewMessages>` field on `ModelMessages` in the same file
- `build_guardian_review_session_config` in `codex-rs/core/src/guardian/review_session.rs`
- `guardian_review_session_config` in `codex-rs/core/src/guardian/review.rs`


### Bug fix: model catalog `auto_review` messages no longer discarded on instruction override

What: A fix in `codex-rs/models-manager/src/model_info.rs` ensures that `model_messages` is preserved when a base-instruction override clears the instructions template and only `auto_review` data (not `approvals`) is present.

Details:
- `clear_instruction_messages()` previously set `model.model_messages = None` whenever `approvals` was `None`, even if `auto_review` was populated. The condition now reads `approvals.is_none() && auto_review.is_none()`, so catalog-provided auto-review policy is retained after an instruction override.
- Without this fix, the new catalog policy fallback above would have been silently dropped whenever a base-instruction override was applied.

Code references:
- `clear_instruction_messages` in `codex-rs/models-manager/src/model_info.rs`


Generated with:
- tool: `harness-investigations@d5cccf8-dirty`
- provider: `claude`
- model: `claude-sonnet-4-6`
- primary diff: `archive/codex/diff/v0.144.4.diff` (raw diff)
- official release notes: `archive/codex/changes/release-notes-v0.144.4.md`
