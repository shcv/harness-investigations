# Changelog for version 2.1.220

## Summary

This is a focused maintenance release. It updates Auto Mode’s internal classifier requests for the first-party service and makes safety-triggered model fallback avoid selecting Opus 5 in certain OAuth sessions without cached model-access data.

## Improvements

### Auto Mode classifier beta support

Auto Mode classifier requests can now include the `auto-mode-classifier-2026-07-16` beta header when using the first-party service with experimental betas enabled. This is an internal compatibility improvement to the existing Auto Mode workflow; no new command or setting is required.

Details:

- The header is used only for first-party, standard-base-URL requests.
- It is not sent when experimental betas are disabled, including through `CLAUDE_CODE_DISABLE_EXPERIMENTAL_BETAS`.
- If a classifier beta receives HTTP 400 and the retry succeeds without it, Claude Code drops that beta for the rest of the session.

Evidence: Auto Mode adds `"auto-mode-classifier-2026-07-16"` through the `"auto_mode_classifier"` beta registration and reports `"retry without it succeeded — dropping the beta for the rest of the session"`.


### More conservative model fallback for some OAuth sessions

When a first-party OAuth session has no cached model-access records, Claude Code now avoids choosing `"claude-opus-5"` as an automatic fallback and uses `"claude-opus-4-8"` instead. This affects the existing fallback path used when a request is refused or safety-flagged, reducing the chance of an automatic switch to an unsuitable model.

Details:

- The change applies only to a narrowly defined first-party OAuth state.
- Explicit model selection is unchanged; this adjusts automatic fallback resolution.
- Third-party provider fallback still uses the configured `ANTHROPIC_DEFAULT_OPUS_MODEL` resolution path.

Evidence: the fallback guard checks `"claude-opus-5"` and substitutes `"claude-opus-4-8"` when the model-access cache is empty.

## Notes

No migration steps or new user-facing commands were identified in the CLI diff.


Generated with:
- tool: `harness-investigations@3c353ff`
- provider: `codex`
- model: `gpt-5.6-terra`
- reasoning effort: `medium`
- primary diff: `archive/claude-code/changes/changes-v2.1.220.md` (filtered astdiff)
- string diff: `archive/claude-code/changes/string-diff-v2.1.220.txt`
