# Changelog for version 0.144.1

## Official Release Highlights

This patch release backports three reliability fixes from PR #31913, all
authored by @bolinfest:

- Standalone installs no longer fail when GitHub returns compact or reordered
  release metadata.
- macOS package installs now correctly expose the code-mode host binary
  alongside the main `codex` executable.
- Code mode continues working when the companion host binary is unavailable,
  falling back to the embedded runtime instead of failing outright.

## Additional Changes Beyond Official Notes

The Rust diff captures the implementation of the third fix (embedded runtime
fallback). The first two fixes (installer metadata handling, macOS packaging)
live outside the `codex-rs/` subtree and do not appear in this diff.


## Bug Fixes

### Code mode falls back to embedded runtime when host binary is missing

Previously, if the code-mode host binary could not be found on disk,
`ProcessOwnedCodeModeSessionProvider` propagated a "failed to spawn
code-mode host" error and refused to create a session. This meant any
installation where the companion host binary was absent or not yet on `PATH`
would silently break code mode entirely.

The fix introduces a `ConnectionError` type with a `host_program_not_found()`
predicate. When spawning the host process fails with `io::ErrorKind::NotFound`,
the provider catches that specific error and permanently transitions to
`ProviderState::InProcess`, creating an `InProcessCodeModeSession` instead.
Subsequent session requests in the same provider instance also go directly to
the in-process path without attempting another spawn.

All other spawn errors (permission denied, crash during handshake, timeout) are
still surfaced as hard errors, so real problems are not silently swallowed.

Code references:
- `ConnectionError` (new enum with `host_program_not_found()`) in `codex-rs/code-mode/src/remote_session/connection.rs`
- `ProviderState` (new `OwnedProcess` / `InProcess` enum) in `codex-rs/code-mode/src/remote_session.rs`
- `ProcessOwnedCodeModeSessionProvider` refactored to use `ProviderState` in `codex-rs/code-mode/src/remote_session.rs`


Generated with:
- tool: `harness-investigations@03136fb-dirty`
- provider: `claude`
- model: `claude-sonnet-4-6`
- primary diff: `archive/codex/diff/v0.144.1.diff` (raw diff)
- official release notes: `archive/codex/changes/release-notes-v0.144.1.md`
