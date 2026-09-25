# Changelog for version 0.157.1

## Release Status

> **Not yet released:** `rust-v0.157.1` is present in Git, but no published GitHub Release was found at sync time. This may be an intermediate development snapshot or a release prepared ahead of publication.


## Summary

Compared with 0.157.0, this snapshot fixes Windows daemon launches that could keep captured output open or incorrectly fail under nested Job Objects. It also suppresses console windows when launching local MCP servers and the code-mode host.

The source tag `rust-v0.157.1` exists, but no published GitHub Release was found when the sync ran. This changelog describes an intermediate development snapshot; it does not imply that release binaries or assets were published.

## Bug Fixes

- Windows daemon launches no longer keep the launcher’s captured output pipes open. Before spawning the background process, Codex clears inheritance on the launcher’s standard handles. This lets callers finish reading captured output after the launcher exits, even while the daemon continues running. The child’s explicitly configured output destinations remain in use. Code references: `spawn_without_inheriting_stdio` in `codex-rs/app-server-daemon/src/backend/windows.rs`, called by `PidBackend::start_inner` in `codex-rs/app-server-daemon/src/backend/pid_start.rs`.

- Windows daemon launches no longer fail solely because the child remains associated with an outer Job Object. Previously, both the launch probe and the running child were rejected if any job association remained. Codex now accepts a successful breakaway launch without treating residual membership alone as a failure. Hosts must still permit breakaway; the launch preflight remains in place. Code references: `ensure_detached_launch` and removal of `Process::ensure_detached` in `codex-rs/app-server-daemon/src/backend/windows.rs`; `PidBackend::start_inner` in `codex-rs/app-server-daemon/src/backend/pid_start.rs`.

- Local stdio MCP servers launch without creating a Windows console window. The launcher applies `CREATE_NO_WINDOW` to ordinary launches and preserves it alongside `CREATE_SUSPENDED` when assigning the server to a Job Object before execution. Existing MCP configurations need no changes. Code reference: `LocalStdioServerLauncher::launch_server` in `codex-rs/rmcp-client/src/stdio_server_launcher.rs`.

- The code-mode host process also launches without creating a Windows console window. Its existing piped input, output, and error streams remain intact. This changes host process startup, not the availability or enablement of code mode. Code reference: `Connection::spawn` in `codex-rs/code-mode/src/remote_session/connection.rs`.


Generated with:
- tool: `harness-investigations@d1dfc8f-dirty`
- provider: `codex`
- model: `gpt-6-astra`
- reasoning effort: `medium`
- primary diff: `archive/codex/diff/v0.157.1.diff` (raw diff)
- release status: `unreleased Git tag; no published GitHub Release found at sync time`
