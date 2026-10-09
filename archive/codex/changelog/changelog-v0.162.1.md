# Changelog for version 0.162.1

## Release Status

> **Not yet released:** `rust-v0.162.1` is present in Git, but no published GitHub Release was found at sync time. This may be an intermediate development snapshot or a release prepared ahead of publication.


## Summary

Compared with 0.162.0, this snapshot fixes shared background-server compatibility checks so that explicit command-line feature overrides drive mismatch handling, while administrator-managed settings take precedence. It also fixes multiline asynchronous question rendering and hyperlink destinations in the terminal UI.

The source tag `rust-v0.162.1` exists, but no published GitHub Release was found during the supplied sync. Treat this as an intermediate/development snapshot; published binaries or assets are not established.

## Bug Fixes


### Background-server checks honor explicit invocation settings

What: Starting Codex no longer treats differences between the client’s file settings or defaults and the running background server as explicit requests to change shared feature settings.

Usage:
```bash
codex

# Explicitly request a shared-service feature setting:
codex -c features.api_key_model_discovery=false

# Use the existing embedded-mode option if needed:
codex --no-daemon -c features.api_key_model_discovery=false
```

Details:

- In 0.162.0, compatibility checking compared all four tracked shared-service features against the client’s effective configuration. A server launched with different settings could therefore trigger incompatibility handling even when the new invocation supplied no feature override.
- In 0.162.1, checking considers only explicit command-line overrides for `api_key_model_discovery`, `code_mode_host`, `auth_elicitation`, and `mcp_oauth_refresh_coordination`. With none requested, it skips feature comparison after connecting.
- When a mismatch requires recovery, the proposed restart settings contain the explicitly requested, non-managed features rather than all four client-effective values. The same invocation overrides are checked again after a restart.
- The client-side rejection for `code_mode.disable_in_process_fallback` combined with disabled `code_mode_host` is removed from this compatibility check.
- Existing recovery choices remain: run without the daemon, confirm a restart of a Codex-managed daemon, or cancel. Restart settings persist and a restart may interrupt active or queued work.

Code references:

- `compatibility_warning`, `server_features`, and `SERVER_FEATURES` in `codex-rs/tui/src/daemon_startup.rs`
- `check` and `recovery_view` in `codex-rs/tui/src/daemon_recovery.rs`
- `run_main_inner` in `codex-rs/tui/src/startup_orchestration.rs`


### Administrator-managed features no longer cause conflicting restart requests

What: Background-server compatibility checking now excludes explicit feature overrides superseded by administrator-managed configuration.

Usage:
```bash
codex -c features.api_key_model_discovery=false
```

If administrator policy controls this feature, this invocation no longer produces a compatibility mismatch solely because the requested value conflicts with that policy.

Details:

- The client reads the daemon’s effective configuration layers and excludes features present in active legacy managed configuration, including file-based and MDM-based layers.
- It also reads `configRequirements/read` and excludes features listed in `featureRequirements`.
- Remaining explicit overrides still undergo the normal feature comparison.
- Older servers that report `configRequirements/read` as an unsupported method or unknown request variant are tolerated. Other failures reading requirements produce a compatibility error.
- `configRequirements/read` and `featureRequirements` already existed in 0.162.0; this change adds their use to the TUI’s daemon compatibility check.

Code references:

- `compatibility_warning` in `codex-rs/tui/src/daemon_startup.rs`
- `ClientRequest::ConfigRequirementsRead` in `codex-rs/app-server-protocol/src/protocol/common.rs`
- `ConfigRequirements::feature_requirements` in `codex-rs/app-server-protocol/src/protocol/v2/config.rs`


### Multiline asynchronous questions retain line breaks and correct links

What: The inline asynchronous question panel now preserves logical line breaks and keeps hyperlinks aligned with their displayed text.

Usage:

No configuration change is required. Questions containing multiple lines, such as the following, render with their line breaks intact:

````text
Run this command:

```sh
printf '診断'
```
Then review (https://example.com/diagnostics?view=full)?
````

Details:

- Each logical line is wrapped and annotated for hyperlinks separately, preventing removed line endings from misaligning source byte ranges and visible text.
- Both LF and CRLF line endings are handled consistently.
- URLs that wrap across terminal lines retain their complete destination.
- This fixes rendering in the existing asynchronous question panel; it does not introduce a new question API or Markdown renderer.

Code references:

- `AsyncQuestions::wrapped_question_lines` in `codex-rs/tui/src/bottom_pane/async_questions/mod.rs`


Generated with:
- tool: `harness-investigations@08b1bcc-dirty`
- provider: `codex`
- model: `gpt-6.1-sol`
- reasoning effort: `medium`
- primary diff: `archive/codex/diff/v0.162.1.diff` (raw diff)
- release status: `unreleased Git tag; no published GitHub Release found at sync time`
